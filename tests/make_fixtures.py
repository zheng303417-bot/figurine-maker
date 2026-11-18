"""Create reproducible cube, open cube and synthetic reference inputs."""

import json
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "examples"


def png_chunk(name, data):
    return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data))


def png(path):
    width = height = 64
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            head = (x - 32) ** 2 + (y - 19) ** 2 <= 11 ** 2
            body = 29 <= y <= 53 and abs(x - 32) <= (y - 23) / 2
            row.extend((36, 130, 144) if head or body else (250, 242, 228))
        rows.append(bytes(row))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(b"".join(rows)))
        + png_chunk(b"IEND", b"")
    )


def triposr_reference(path):
    """Draw an original, shaded robot with a transparent background."""
    size = 320
    shapes = [
        (120, 249, 32, 28, (37, 105, 132)), (200, 249, 32, 28, (38, 121, 145)),
        (98, 178, 25, 44, (61, 149, 164)), (222, 178, 25, 44, (52, 130, 150)),
        (160, 188, 66, 68, (66, 160, 172)), (160, 120, 27, 34, (48, 105, 126)),
        (160, 85, 77, 51, (81, 179, 183)), (175, 94, 56, 29, (28, 47, 62)),
        (151, 92, 8, 10, (240, 211, 107)), (190, 92, 8, 10, (240, 211, 107)),
        (168, 170, 16, 11, (234, 177, 83)),
    ]
    pixels = bytearray()
    for y in range(size):
        pixels.append(0)
        for x in range(size):
            color = (0, 0, 0, 0)
            for cx, cy, rx, ry, rgb in shapes:
                dx, dy = (x - cx) / rx, (y - cy) / ry
                radius = dx * dx + dy * dy
                if radius <= 1:
                    light = 0.63 + 0.45 * (1 - radius) ** 0.5 - 0.18 * (dx + dy)
                    color = (*[min(255, int(channel * light)) for channel in rgb], 255)
            pixels.extend(color)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(pixels))
        + png_chunk(b"IEND", b"")
    )


def obj(path, open_top=False):
    # OBJ is Y-up. Deliberately reverse one face of the closed cube.
    faces = [(1, 4, 3, 2), (5, 6, 7, 8), (1, 2, 6, 5),
             (2, 3, 7, 6), (3, 4, 8, 7), (4, 1, 5, 8)]
    vertices = [(-20, 0, -20), (20, 0, -20), (20, 40, -20), (-20, 40, -20),
                (-20, 0, 20), (20, 0, 20), (20, 40, 20), (-20, 40, 20)]
    if open_top:
        # Remove two adjoining sides to exceed conservative small-hole repair.
        del faces[4:]
    else:
        faces[1] = faces[1][::-1]
    path.write_text(
        "".join(f"v {x} {y} {z}\n" for x, y, z in vertices)
        + "".join("f " + " ".join(map(str, face)) + "\n" for face in faces),
        encoding="utf-8",
    )


def job(name, **overrides):
    target = ROOT / name
    target.mkdir(parents=True, exist_ok=True)
    data = {
        "job_id": name, "target_height_mm": 150, "height_includes_base": True,
        "printer_profile": "fdm_generic", "nozzle_mm": 0.4, "material": "PLA",
        "output_formats": ["stl", "blend"], **overrides,
    }
    (target / "job.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    closed = job("cube", input_mode="mesh", source_mesh="cube.obj", input_unit="mm")
    obj(closed / "cube.obj")
    defect = job("open_cube", input_mode="mesh", source_mesh="open_cube.obj", input_unit="mm")
    obj(defect / "open_cube.obj", open_top=True)
    mock = job("mock_figurine", input_mode="image", source_images=["front.png"], provider="mock", mock_format="stl",
               base={"enabled": True, "shape": "round", "height_mm": 4, "margin_mm": 4})
    png(mock / "front.png")
    triposr_reference(ROOT / "triposr_local" / "front.png")
