"""CPU mesh generation with a local, pinned Hunyuan3D-2mini checkpoint."""

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path
from types import ModuleType


def prepare_image(path, background_weights):
    import numpy as np
    from PIL import Image, ImageOps

    with Image.open(path) as source:
        source = ImageOps.exif_transpose(source)
        source.thumbnail((1600, 1600))
        image = source.convert("RGBA")
    if image.getchannel("A").getextrema()[0] < 255:
        return image

    pixels = np.array(image)
    red, green, blue = np.moveaxis(pixels[:, :, :3].astype(np.int16), -1, 0)
    magenta = np.minimum(red, blue) - green
    border = np.concatenate((magenta[0, :], magenta[-1, :], magenta[:, 0], magenta[:, -1]))
    if np.mean(border > 145) > 0.95:
        pixels[:, :, 3] = (255 - np.clip((magenta - 55) * 3.4, 0, 255)).astype(np.uint8)
        return Image.fromarray(pixels)

    import rembg

    checksum = hashlib.md5(background_weights.read_bytes(), usedforsecurity=False).hexdigest()
    if checksum != "8e83ca70e441ab06c318d82300c84806":
        raise ValueError("Local U2NetP model checksum mismatch.")
    os.environ["U2NET_HOME"] = str(background_weights.parent)
    return rembg.remove(image.convert("RGB"), session=rembg.new_session("u2netp"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("model", "deps", "image", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    sys.path[:0] = [str(path) for path in (
        args.model / "deps", args.deps / "extra", args.deps / "deps-cpu", args.model / "source",
    )]
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HY3DGEN_DEBUG="0")
    import numpy as np
    import torch

    # Import shape modules directly. The upstream package initializer also
    # loads the optional MeshLab native plugin, which fails on this Windows path.
    package = ModuleType("hy3dgen.shapegen")
    package.__path__ = [str(args.model / "source" / "hy3dgen" / "shapegen")]
    sys.modules[package.__name__] = package
    from hy3dgen.shapegen.models.autoencoders import HierarchicalVolumeDecoding
    from hy3dgen.shapegen.pipelines import Hunyuan3DDiTFlowMatchingPipeline

    torch.set_num_threads(min(12, os.cpu_count() or 1))
    image = prepare_image(args.image, args.deps / "weights" / "u2netp.onnx")
    if image.getchannel("A").getbbox() is None:
        raise ValueError("Foreground extraction returned an empty image.")
    image.save(args.output.with_name("hunyuan-input.png"))
    weights = args.model / "weights"
    print(f"Loading Hunyuan3D-2mini Turbo with Torch {torch.__version__} on CPU.", flush=True)
    pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_single_file(
        str(weights / "model.fp16.safetensors"), str(weights / "config.yaml"),
        device="cpu", dtype=torch.float32, use_safetensors=True,
    )
    pipeline.vae.volume_decoder = HierarchicalVolumeDecoding()
    mesh = pipeline(
        image=image, num_inference_steps=8, octree_resolution=256,
        generator=torch.Generator(device="cpu").manual_seed(2026),
        num_chunks=8000, enable_pbar=False,
    )[0]
    if mesh is None or not len(mesh.faces) or not np.isfinite(mesh.vertices).all():
        raise RuntimeError("Hunyuan3D produced empty or invalid geometry.")
    temporary = args.output.with_suffix(".tmp")
    temporary.write_bytes(mesh.export(file_type="glb"))
    temporary.replace(args.output)
    print(f"Generated {len(mesh.faces)} faces in {time.monotonic() - started:.1f}s.", flush=True)


if __name__ == "__main__":
    main()
