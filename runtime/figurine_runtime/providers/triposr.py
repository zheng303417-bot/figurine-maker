"""Run the local TripoSR worker in an isolated Python process."""

import os
import struct
import subprocess
import sys
from pathlib import Path

from ..config import confined_path


def generate(job, job_dir, destination):
    images = job.get("source_images", [])
    if len(images) != 1:
        raise ValueError("TripoSR requires exactly one reference image.")
    image = confined_path(job_dir, images[0])
    tools = Path(os.environ.get("FIGURINE_TRIPOSR_HOME", ".tools/triposr")).resolve()
    if not (tools / "weights" / "model.ckpt").is_file() or not (tools / "source" / "tsr" / "system.py").is_file():
        raise ValueError("TripoSR files are missing. See docs/INSTALL_TRIPOSR.md or set FIGURINE_TRIPOSR_HOME.")
    python = os.environ.get("FIGURINE_TRIPOSR_PYTHON", sys.executable)
    default_device = "cuda"
    if (tools / "deps-cpu" / "torch" / "__init__.py").is_file():
        default_device = "cpu"
    device = os.environ.get("FIGURINE_TRIPOSR_DEVICE", default_device)
    if device not in ("cpu", "cuda"):
        raise ValueError("FIGURINE_TRIPOSR_DEVICE must be cpu or cuda.")
    worker = Path(__file__).with_name("triposr_worker.py").resolve()
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    log = destination.with_name("triposr.log")
    env = os.environ.copy()
    for name in ("MESHY_API_KEY", "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        env.pop(name, None)
    env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", PYTHONUTF8="1")
    with log.open("wb") as stream:
        result = subprocess.run(
            [python, "-I", str(worker), "--tools", str(tools), "--image", str(image),
             "--output", str(destination), "--device", device],
            env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=900, check=False,
        )
    if result.returncode or not destination.is_file():
        raise RuntimeError(f"Local TripoSR failed (exit {result.returncode}). See models/triposr.log.")
    with destination.open("rb") as stream:
        header = stream.read(12)
    if header != struct.pack("<4sII", b"glTF", 2, destination.stat().st_size):
        raise RuntimeError("TripoSR did not produce a valid GLB header.")
    return {
        "provider": "triposr", "task_id": None, "status": "SUCCEEDED", "local": True,
        "device": device, "generation_log": "models/triposr.log",
    }
