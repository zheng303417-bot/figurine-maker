"""Check a saved, fully executed TripoSR job and optional Bambu slice."""

import argparse
import hashlib
import json
import struct
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(output, sliced):
    report = read(output / "reports" / "quality_report.json")
    assert report["provider_result"]["provider"] == "triposr"
    assert report["provider_result"]["local"] is True
    assert report["provider_result"]["status"] == "SUCCEEDED"
    assert report["geometry_status"] == "PASS"
    assert report["metrics"]["watertight_each_part"] is True
    assert report["metrics"]["part_count"] == 1
    assert abs(report["dimensions_mm"]["z"] - 150) <= 0.5
    for extension in ("stl", "glb", "blend"):
        assert report["evidence"]["reopen_checks"][extension]["pass"]
    manifest = read(output / "manifest.json")
    for record in manifest["files"]:
        file = output / record["path"]
        assert file.stat().st_size == record["bytes"]
        assert hashlib.sha256(file.read_bytes()).hexdigest() == record["sha256"]
    model = output / "models" / "original.glb"
    with model.open("rb") as stream:
        assert stream.read(12) == struct.pack("<4sII", b"glTF", 2, model.stat().st_size)
    print("PASS local TripoSR generation, closed single-part geometry, 150 mm and three export roundtrips.")
    if sliced:
        result = read(sliced / "result.json")
        assert result["return_code"] == 0
        plate, = result["sliced_plates"]
        obj, = plate["objects"]
        assert abs(obj["bbox"]["height"] - 150) <= 0.5
        with ZipFile(sliced / "sliced.3mf") as archive:
            assert archive.testzip() is None
            geometry = ElementTree.fromstring(archive.read("3D/Objects/object_1.model"))
            assert len(geometry.findall(".//{*}triangle")) == obj["triangle_count"]
            assert archive.getinfo("Metadata/plate_1.gcode").file_size > 0
        print(f"PASS Bambu slice, {obj['triangle_count']} triangles, 3MF geometry and G-code present.")
        if plate.get("warning_message"):
            print(f"Slicer warning: {plate['warning_message']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--slice-output", type=Path)
    args = parser.parse_args()
    check(args.output, args.slice_output)
