"""Check the saved artifacts from the three Windows geometry fixtures."""

import argparse
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(root, inputs):
    for name in ("cube", "open_cube", "mock_figurine"):
        output = root / name
        report = load(output / "reports" / "quality_report.json")
        geometry = load(output / "reports" / "geometry.json")
        manifest = load(output / "manifest.json")
        for artifact in manifest["files"]:
            path = output / artifact["path"]
            assert path.stat().st_size == artifact["bytes"], path
            assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"], path
        for stage in ("before", "after"):
            assert (output / "previews" / f"{stage}.png").read_bytes().startswith(b"\x89PNG")
            assert (output / "stages" / f"{stage}.blend").stat().st_size > 0
        job = load(inputs / name / "job.json")
        if "source_mesh" in job:
            assert (output / report["source_model"]).read_bytes() == (inputs / name / job["source_mesh"]).read_bytes()
        if name == "open_cube":
            assert geometry["evidence"]["before"]["boundary_edges"] > 0
            assert geometry["metrics"]["boundary_edges"] > 0
            assert report["geometry_status"] == "FAIL"
            assert not list((output / "print").glob("figurine.*"))
        else:
            assert report["geometry_status"] == "PASS"
            assert abs(geometry["dimensions_mm"]["z"] - 150) <= 0.5
            assert geometry["metrics"]["inconsistent_winding_edges"] == 0
            assert geometry["metrics"]["part_count"] == 1
            assert all(geometry["evidence"]["reopen_checks"][fmt]["pass"] for fmt in ("stl", "blend"))
            if name == "cube":
                assert geometry["evidence"]["before"]["inconsistent_winding_edges"] > 0
            else:
                assert report["provider_result"]["synthetic"] is True
                assert "Boolean union with round base" in geometry["fixes_applied"]
                assert geometry["dimensions_mm"]["x"] > 65
        outcome = "detected and rejected open mesh" if name == "open_cube" else "verified 150 mm STL and BLEND"
        print(f"PASS {name}: {outcome}")


def check_slice(root, output):
    result = load(output / "result.json")
    plate, = result["sliced_plates"]
    model, = plate["objects"]
    source = root / "mock_figurine" / "print" / "figurine.stl"
    assert result["return_code"] == 0 and abs(result["layer_height"] - 0.2) < 0.001
    assert model["name"] == source.name and abs(model["bbox"]["height"] - 150) <= 0.5
    assert model["triangle_count"] > 0 and plate["sliced_time"] > 0
    with ZipFile(output / "sliced.3mf") as package:
        assert package.testzip() is None
        geometry = ElementTree.fromstring(package.read("3D/Objects/object_1.model"))
        assert len(geometry.findall(".//{*}triangle")) == model["triangle_count"]
        assert package.getinfo("Metadata/plate_1.gcode").file_size > 0
        assert package.read("Metadata/plate_1.gcode.md5").decode().strip().lower() == hashlib.md5(
            package.read("Metadata/plate_1.gcode"), usedforsecurity=False
        ).hexdigest()
    print(f"PASS Bambu slice: 150 mm and {model['triangle_count']} triangles; 3MF geometry and G-code integrity verified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--slice-output", type=Path)
    args = parser.parse_args()
    check(args.output, Path(__file__).resolve().parents[1] / "examples")
    if args.slice_output:
        check_slice(args.output, args.slice_output)
