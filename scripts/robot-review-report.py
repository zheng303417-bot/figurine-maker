"""Verify robot refinement outputs and compose a labeled comparison sheet."""

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "projects" / "robot-review"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    validated = OUTPUT / "validated"
    geometry = read(validated / "reports" / "geometry.json")
    manifest = read(validated / "manifest.json")
    assert geometry["status"] == "PASS"
    assert geometry["metrics"]["part_count"] == 1
    assert all(item["pass"] for item in geometry["evidence"]["reopen_checks"].values())
    assert abs(geometry["dimensions_mm"]["z"] - 150) < 0.5
    assert geometry["dimensions_mm"]["x"] < 140
    for record in manifest["files"]:
        file = validated / record["path"]
        assert file.stat().st_size == record["bytes"]
        assert hashlib.sha256(file.read_bytes()).hexdigest() == record["sha256"]
    sliced = OUTPUT / "slice-supported"
    result = read(sliced / "result.json")
    assert result["return_code"] == 0
    plate, = result["sliced_plates"]
    assert not plate["warning_message"]
    with ZipFile(sliced / "sliced.3mf") as archive:
        assert archive.testzip() is None
        assert archive.getinfo("Metadata/plate_1.gcode").file_size > 0
    report = {
        "geometry_status": "PASS", "slicer_status": "PASS",
        "physical_print_status": "UNVERIFIED",
        "dimensions_mm": geometry["dimensions_mm"],
        "visual_status": "IMPROVED_WITH_REMAINING_GAPS",
        "improvements": ["Front-facing camera established", "Reduced surface stair steps",
                         "Defined face-panel relief and paired eye relief",
                         "Pedestal width reduced from 170 mm to about 132 mm"],
        "remaining_gaps": ["Inferred back protrusion remains", "Fine facial shape differs from reference",
                           "Color reproduction and thin-wall assessment unverified"],
        "slicer_warning": plate["warning_message"],
    }
    (OUTPUT / "review.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    sheet = Image.new("RGB", (1440, 560), "#eeeeea")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 24)
    panels = [
        ("Reference", ROOT / "examples" / "triposr_local" / "front.png"),
        ("Before / matched front view", OUTPUT / "baseline" / "positive_y.png"),
        ("After / matched front view", OUTPUT / "final" / "positive_y.png"),
    ]
    for index, (title, file) in enumerate(panels):
        draw.text((index * 480 + 16, 18), title, fill="#222222", font=font)
        with Image.open(file) as image:
            image = image.convert("RGBA")
            image.thumbnail((480, 480), Image.Resampling.LANCZOS)
            background = Image.new("RGBA", image.size, "#eeeeea")
            background.alpha_composite(image)
            sheet.paste(background.convert("RGB"), (index * 480 + (480 - image.width) // 2, 64))
    sheet.save(OUTPUT / "comparison.png")
    print("PASS robot refinement geometry, three export roundtrips and supported Bambu slice.")


if __name__ == "__main__":
    main()
