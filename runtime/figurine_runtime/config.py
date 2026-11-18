"""Validate a job before touching the filesystem or calling a provider."""

import json
import math
import re
from pathlib import Path, PureWindowsPath


def confined_path(root, supplied):
    if not isinstance(supplied, str) or not supplied.strip() or any(
        c in supplied for c in (":", "\x00")
    ):
        raise ValueError("Expected a relative job path.")
    portable = supplied.replace("\\", "/")
    if PureWindowsPath(supplied).anchor or portable.startswith("/") or ".." in portable.split("/"):
        raise ValueError("Path escapes the job directory.")
    path = (root / portable).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Path escapes the job directory.")
    return path


def positive(value, label):
    if type(value) not in (int, float) or value <= 0 or value > 1e9 or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite positive number.")


def one_of(value, choices, label):
    if value not in choices:
        raise ValueError(f"Unsupported {label}.")


def load_job(path):
    path = Path(path).resolve(strict=True)
    with path.open(encoding="utf-8-sig") as stream:
        job = json.load(stream)
    if not isinstance(job, dict):
        raise ValueError("The job must be a JSON object.")
    job_id = job.get("job_id")
    if not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", job_id):
        raise ValueError("Invalid job_id.")
    if PureWindowsPath(job_id).is_reserved():
        raise ValueError("Reserved job_id.")
    mode = job.get("input_mode")
    one_of(mode, ("text", "image", "mesh"), "input_mode")
    positive(job.get("target_height_mm"), "target_height_mm")
    if type(job.get("height_includes_base")) is not bool:
        raise ValueError("Set height_includes_base explicitly.")
    job.setdefault("printer_profile", "fdm_generic")
    one_of(job["printer_profile"], ("fdm_generic", "sla_generic"), "printer_profile")
    if job.get("nozzle_mm") is not None:
        positive(job["nozzle_mm"], "nozzle_mm")
    job.setdefault("provider", "mock")
    one_of(job["provider"], ("mock", "meshy", "triposr", "hunyuan"), "provider")
    one_of(job.setdefault("mock_format", "glb"), ("glb", "stl"), "mock format")
    for flag, default in (("allow_external_image_upload", False), ("require_approval_for_paid_calls", True)):
        if type(job.setdefault(flag, default)) is not bool:
            raise ValueError(f"{flag} must be boolean.")
    if job.get("max_paid_credits") is not None:
        positive(job["max_paid_credits"], "max_paid_credits")
    formats = job.setdefault("output_formats", ["stl", "glb"])
    if not isinstance(formats, list) or not formats or any(
        item not in ("stl", "glb", "blend") for item in formats
    ):
        raise ValueError("output_formats must contain stl, glb or blend.")
    if job.get("input_unit") is not None:
        one_of(job["input_unit"], ("mm", "cm", "m", "in"), "input_unit")
    base = job.setdefault("base", {"enabled": False, "shape": "round"})
    if not isinstance(base, dict) or type(base.get("enabled")) is not bool:
        raise ValueError("base.enabled must be boolean.")
    if base["enabled"]:
        one_of(base.get("shape", "round"), ("round",), "base shape")
        for field in ("height_mm", "margin_mm"):
            if field in base:
                positive(base[field], f"base.{field}")
    parts = job.setdefault("parts", {"mode": "single", "allow_connectors": False})
    if not isinstance(parts, dict) or parts.get("mode", "single") != "single" or parts.get("allow_connectors", False) is not False:
        raise ValueError("Only single-part jobs are supported.")
    if type(job.get("remove_small_components", False)) is not bool:
        raise ValueError("remove_small_components must be boolean.")
    images = job.setdefault("source_images", [])
    if not isinstance(images, list) or len(images) > 4 or (mode == "image") != bool(images):
        raise ValueError("Image mode requires one to four images.")
    if mode == "image" and job["provider"] in ("triposr", "hunyuan") and len(images) != 1:
        name = "TripoSR" if job["provider"] == "triposr" else "Hunyuan3D"
        raise ValueError(f"{name} requires exactly one reference image.")
    for image in images:
        validate_file(path.parent, image, (".png", ".jpg", ".jpeg", ".webp"))
    mesh = job.get("source_mesh")
    if mode == "mesh":
        validate_file(path.parent, mesh, (".stl", ".obj", ".glb"))
    elif mesh is not None:
        raise ValueError("source_mesh is only supported in mesh mode.")
    prompt = job.get("prompt", "")
    if not isinstance(prompt, str) or (mode == "text" and not prompt.strip()):
        raise ValueError("Text mode requires a prompt.")
    return job, path.parent


def validate_file(root, supplied, extensions):
    path = confined_path(root, supplied)
    if path.suffix.lower() not in extensions or not path.is_file() or not path.stat().st_size:
        raise ValueError(f"Expected a nonempty file with extension {'/'.join(extensions)}.")
    return path
