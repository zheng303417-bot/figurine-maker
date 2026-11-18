"""Load the official model and extract a mesh with a wheel-based Windows backend."""

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--resolution", type=int, choices=(160, 256), default=160)
    args = parser.parse_args()
    started = time.monotonic()
    print("Starting local TripoSR worker; importing numerical libraries.", flush=True)
    root = args.tools
    weights = root / "weights"
    backend_dir = "deps-cpu" if args.device == "cpu" and (root / "deps-cpu" / "torch").is_dir() else "deps"
    for path in (root / "source", root / "extra", root / backend_dir):
        if not path.is_dir():
            raise ValueError(f"Missing TripoSR directory: {path.name}")
    sys.path[:0] = [str(root / part) for part in ("extra", backend_dir, "source")]
    os.environ["U2NET_HOME"] = str(weights)
    os.environ.setdefault("NUMBA_CACHE_DIR", str(root / "tmp" / "numba"))

    import numpy as np
    import torch
    from PIL import Image, ImageOps
    from omegaconf import OmegaConf
    from skimage.measure import marching_cubes

    # TripoSR's extractor expects torchmcubes' reverse-axis coordinates.
    # The isosurface operation uses a prebuilt scikit-image CPU wheel.
    def extract_surface(field, threshold):
        vertices, faces, _, _ = marching_cubes(
            field.to(device="cpu", dtype=torch.float32).numpy(), threshold,
            gradient_direction="descent", allow_degenerate=False,
        )
        return torch.from_numpy(vertices[:, ::-1].copy()), torch.from_numpy(faces.astype(np.int64))

    backend = ModuleType("torchmcubes")
    backend.marching_cubes = extract_surface
    sys.modules["torchmcubes"] = backend

    from tsr.models.tokenizers import image as tokenizer
    from tsr.system import TSR
    from tsr.utils import resize_foreground, to_gradio_3d_orientation

    device = args.device
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable. Verify the CUDA PyTorch wheel or select CPU.")
    if device == "cpu":
        torch.set_num_threads(min(8, os.cpu_count() or 1))

    with Image.open(args.image) as original:
        original = ImageOps.exif_transpose(original)
        original.thumbnail((1600, 1600))
        foreground = original.convert("RGBA")
    if foreground.getchannel("A").getextrema()[0] == 255:
        import rembg
        background_weights = weights / "u2netp.onnx"
        if not background_weights.is_file():
            raise ValueError("Opaque images require the local u2netp.onnx file.")
        checksum = hashlib.md5(background_weights.read_bytes(), usedforsecurity=False).hexdigest()
        if checksum != "8e83ca70e441ab06c318d82300c84806":
            raise ValueError("U2NetP checksum mismatch. Reinstall the local weights.")
        foreground = rembg.remove(foreground.convert("RGB"), session=rembg.new_session("u2netp"))
    if foreground.getchannel("A").getbbox() is None:
        raise ValueError("Foreground extraction returned an empty image.")
    foreground = resize_foreground(foreground, 0.85)
    background = Image.new("RGBA", foreground.size, (128, 128, 128, 255))
    prepared = Image.alpha_composite(background, foreground).convert("RGB")
    prepared.save(args.output.with_name("triposr-input.png"))

    cfg = OmegaConf.load(weights / "config.yaml")
    OmegaConf.resolve(cfg)
    dino_config = weights / "dino-config.json"
    if not dino_config.is_file():
        raise ValueError("Missing the local DINO configuration.")
    print(f"PyTorch {torch.__version__}, TripoSR device: {device}; loading local checkpoint.", flush=True)
    with patch.object(tokenizer, "hf_hub_download", return_value=str(dino_config)):
        model = TSR(cfg)
    model.load_state_dict(torch.load(weights / "model.ckpt", map_location="cpu", weights_only=True))
    model.eval().to(device)
    model.renderer.set_chunk_size(8192)
    print(f"Reconstructing image and extracting surface at resolution {args.resolution}.", flush=True)
    with torch.inference_mode():
        scene_codes = model([prepared], device=device)
        mesh = model.extract_mesh(scene_codes, has_vertex_color=True, resolution=args.resolution)[0]
    if not len(mesh.faces) or not np.isfinite(mesh.vertices).all():
        raise ValueError("TripoSR produced empty or invalid geometry.")
    mesh.fix_normals(multibody=True)
    mesh = to_gradio_3d_orientation(mesh)
    temporary = args.output.with_suffix(".tmp")
    temporary.write_bytes(mesh.export(file_type="glb"))
    temporary.replace(args.output)
    print(f"EXPORT OK: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces; watertight={mesh.is_watertight}.", flush=True)
    print(f"Worker elapsed seconds: {time.monotonic() - started:.2f}", flush=True)


if __name__ == "__main__":
    main()
