"""Invoke the optional, local Hunyuan3D shape generator."""

import os
import struct
import subprocess
import sys
from pathlib import Path

from ..config import confined_path


def generate(job, job_dir, destination):
    images = job.get("source_images", [])
    if len(images) != 1:
        raise ValueError("Hunyuan3D requires exactly one reference image.")
    image = confined_path(job_dir, images[0])
    model = Path(os.environ.get("FIGURINE_HUNYUAN_HOME", ".tools/hunyuan")).resolve()
    deps = Path(os.environ.get("FIGURINE_TRIPOSR_HOME", ".tools/triposr")).resolve()
    worker = Path(__file__).with_name("hunyuan_worker.py").resolve()
    if not (model / "weights" / "model.fp16.safetensors").is_file():
        raise ValueError("Hunyuan3D files are missing. See docs/INSTALL_HUNYUAN.md.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    log = destination.with_name("hunyuan.log")
    env = os.environ.copy()
    for key in ("MESHY_API_KEY", "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        env.pop(key, None)
    with log.open("wb") as stream:
        result = subprocess.run(
            [sys.executable, "-I", "-X", "utf8", str(worker), "--model", str(model),
             "--deps", str(deps), "--image", str(image), "--output", str(destination)],
            env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=900, check=False,
        )
    if result.returncode or not destination.is_file():
        raise RuntimeError(f"Local Hunyuan3D failed (exit {result.returncode}). See models/hunyuan.log.")
    with destination.open("rb") as stream:
        header = stream.read(12)
    if header != struct.pack("<4sII", b"glTF", 2, destination.stat().st_size):
        raise RuntimeError("Hunyuan3D produced an invalid GLB header.")
    return {"provider": "hunyuan", "status": "SUCCEEDED", "local": True, "device": "cpu",
            "generation_log": "models/hunyuan.log"}
