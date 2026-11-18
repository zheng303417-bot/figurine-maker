"""Command-line orchestration for local figurine jobs."""

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import confined_path, load_job


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def file_record(path, output):
    with path.open("rb") as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": path.relative_to(output).as_posix(), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def blender_path(explicit):
    configured = explicit or os.environ.get("FIGURINE_BLENDER")
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_file():
            raise ValueError("Configured Blender executable was not found.")
        return str(candidate.resolve())
    candidate = shutil.which("blender")
    if candidate:
        return candidate
    root = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Blender Foundation"
    return next((str(p) for p in sorted(root.glob("*/blender.exe"), reverse=True)), None)


def safe_import_copy(source, output):
    """Check for sidecar references before launching a standalone mesh import."""
    if source.suffix.lower() == ".obj":
        lines = source.read_text(encoding="utf-8-sig", errors="replace").splitlines(keepends=True)
        if any(line.lstrip().split(maxsplit=1)[0:1] in (["call"], ["csh"]) for line in lines):
            raise ValueError("OBJ contains an unsupported external command.")
        clean = [line for line in lines if line.lstrip().split(maxsplit=1)[0:1] != ["mtllib"]]
        if len(clean) != len(lines):
            staged = output / "stages" / "import_geometry.obj"
            staged.parent.mkdir(exist_ok=True)
            staged.write_text("".join(clean), encoding="utf-8")
            return staged
    if source.suffix.lower() == ".glb":
        with source.open("rb") as stream:
            header = stream.read(20)
            if len(header) != 20:
                raise ValueError("Incomplete GLB header.")
            magic, version, size, chunk_size, chunk_type = struct.unpack("<4sIIII", header)
            if (magic, version, chunk_type) != (b"glTF", 2, 0x4E4F534A) or size != source.stat().st_size:
                raise ValueError("Invalid GLB header.")
            if not 0 < chunk_size <= min(32 * 1024 * 1024, size - 20):
                raise ValueError("Invalid GLB JSON chunk size.")
            document = json.loads(stream.read(chunk_size))
        if not isinstance(document, dict):
            raise ValueError("Invalid GLB document.")
        for collection in ("images", "buffers"):
            for item in document.get(collection, []):
                if not isinstance(item, dict):
                    raise ValueError("Invalid GLB resource.")
                uri = item.get("uri")
                if uri is not None and (not isinstance(uri, str) or not uri.startswith("data:")):
                    raise ValueError("External GLB resources are unsupported. Embed assets in the GLB.")
    return source


def design_job(job, output):
    write_json(output / "concept" / "character-spec.json", {
        "job_id": job["job_id"],
        "brief": job.get("prompt", ""),
        "style": job.get("style"),
        "target_height_mm": job["target_height_mm"],
        "height_includes_base": job["height_includes_base"],
        "base": job["base"],
        "status": "DRAFT",
        "review_fields": ["silhouette", "face", "hair", "clothing", "palette", "pose", "accessories", "rear_details"],
        "next_step": "Review the character specification, then supply a consistent reference image or a mesh.",
    })


def run_job(args, job, job_dir, output):
    from .providers import generate
    from .providers.meshy import ProviderError

    executable = blender_path(args.blender)
    if not executable:
        raise ValueError("Blender was not found. Set FIGURINE_BLENDER or pass --blender.")
    output.mkdir(parents=True, exist_ok=False)
    state_path = output / "job_state.json"
    write_json(state_path, {"state": "RUNNING"})
    write_json(output / "job.json", job)
    source = None
    geometry = {}
    provider = None
    problem = None
    try:
        model_dir = output / "models"
        model_dir.mkdir()
        if job["input_mode"] == "mesh":
            original = confined_path(job_dir, job["source_mesh"])
            source = model_dir / ("original" + original.suffix.lower())
            shutil.copyfile(original, source)
        else:
            extension = job["mock_format"] if job["provider"] == "mock" else "glb"
            source = model_dir / f"original.{extension}"
            provider = generate(job, job_dir, source, approve_upload=args.approve_upload, approve_paid=args.approve_paid)
        worker_mesh = safe_import_copy(source, output)
        worker = Path(__file__).resolve().parents[1] / "blender_scripts" / "process_mesh.py"
        log = output / "reports" / "blender.log"
        log.parent.mkdir(exist_ok=True)
        env = os.environ.copy()
        env.pop("MESHY_API_KEY", None)
        with log.open("wb") as stream:
            process = subprocess.run(
                [executable, "--background", "--factory-startup", "--disable-autoexec", "--python-exit-code", "1",
                 "--python", str(worker), "--", "--job", str(output / "job.json"), "--mesh", str(worker_mesh),
                 "--output", str(output)],
                stdout=stream, stderr=subprocess.STDOUT, env=env, timeout=900, check=False,
            )
        report_path = log.parent / "geometry.json"
        if report_path.is_file():
            geometry = json.loads(report_path.read_text(encoding="utf-8"))
        if process.returncode or geometry.get("status") != "PASS":
            problem = "Geometry processing failed. Review reports/geometry.json and reports/blender.log."
    except Exception as exc:
        problem = str(exc) or type(exc).__name__
        token = os.environ.get("MESHY_API_KEY")
        if token:
            problem = problem.replace(token, "[redacted]")
        if isinstance(exc, ProviderError):
            task_id = exc.task_id
            if token and task_id and token in task_id:
                task_id = None
            allowed_states = ("PENDING", "IN_PROGRESS", "FAILED", "SUCCEEDED", "CANCELED", "EXPIRED")
            provider = {
                "provider": "meshy", "task_id": task_id, "status": "FAILED",
                "remote_status": exc.status if exc.status in allowed_states else None,
            }
    status = "FAIL" if problem else "PASS"
    report = {
        **geometry,
        "geometry_status": status,
        "status": "FAIL" if problem else "UNVERIFIED",
        "job_id": job["job_id"],
        "target_height_mm": job["target_height_mm"],
        "height_includes_base": job["height_includes_base"],
        "printer_profile": job["printer_profile"],
        "source_model": source.relative_to(output).as_posix() if source and source.is_file() else None,
        "processed_model": next(
            (p.relative_to(output).as_posix() for p in sorted((output / "print").glob("figurine.*")) if p.is_file()),
            None,
        ),
        "provider_result": provider,
        "external_tasks": [provider] if provider and provider.get("provider") == "meshy" else [],
        "thin_wall_status": "UNVERIFIED",
        "slicer_status": "UNVERIFIED",
        "error": problem,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output / "reports" / "quality_report.json", report)
    write_json(state_path, {"state": "FAILED" if problem else "SUCCEEDED"})
    records = [file_record(p, output) for p in sorted(output.rglob("*")) if p.is_file()]
    write_json(output / "manifest.json", {"job_id": job["job_id"], "geometry_status": status, "files": records})
    if problem:
        print(problem, file=sys.stderr)
        return 1
    print(f"Geometry PASS. Thin-wall and slicing checks UNVERIFIED. Output: {output}")
    return 0


def verify_job(job, output):
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    if manifest["job_id"] != job["job_id"] or manifest["geometry_status"] != "PASS" or not manifest["files"]:
        raise ValueError("Manifest does not describe a successful geometry run for this job.")
    for record in manifest["files"]:
        path = confined_path(output, record["path"])
        if file_record(path, output) != record:
            raise ValueError(f"Artifact integrity check failed: {record['path']}")
    print(f"PASS: verified {len(manifest['files'])} artifact checksums.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="figurine")
    commands = parser.add_subparsers(dest="command", required=True)
    probe = commands.add_parser("probe")
    probe.add_argument("--blender")
    for name in ("validate", "design", "run", "verify"):
        command = commands.add_parser(name)
        command.add_argument("--job", required=True, type=Path)
        command.add_argument("--output", type=Path)
        if name == "run":
            command.add_argument("--blender")
            command.add_argument("--approve-upload", action="store_true")
            command.add_argument("--approve-paid", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "probe":
            print(json.dumps({
                "python": sys.version.split()[0],
                "blender": blender_path(args.blender),
                "meshy_api_key_set": bool(os.environ.get("MESHY_API_KEY")),
            }, indent=2))
            return 0
        job, job_dir = load_job(args.job)
        output = (args.output or Path("projects") / job["job_id"]).resolve()
        if args.command == "validate":
            print(f"PASS: {job['job_id']}")
        elif args.command == "verify":
            return verify_job(job, output)
        elif args.command == "design" or job["input_mode"] == "text":
            output.mkdir(parents=True, exist_ok=False)
            design_job(job, output)
            print(f"Design draft: {output / 'concept' / 'character-spec.json'}")
        else:
            return run_job(args, job, job_dir, output)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0
