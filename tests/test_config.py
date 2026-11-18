import json
import tempfile
import unittest
from pathlib import Path

from figurine_runtime.config import load_job


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "job.json"
        self.job = {
            "job_id": "text_example", "input_mode": "text", "prompt": "Explorer",
            "target_height_mm": 150, "height_includes_base": True,
        }

    def load(self, **overrides):
        self.path.write_text(json.dumps({**self.job, **overrides}), encoding="utf-8")
        return load_job(self.path)[0]

    def test_valid_job_preserves_explicit_height(self):
        self.assertEqual(self.load()["target_height_mm"], 150)

    def test_rejects_invalid_modes_options_and_dimensions(self):
        for fields in (
            {"job_id": "CON"}, {"target_height_mm": True}, {"target_height_mm": float("inf")},
            {"height_includes_base": "yes"}, {"input_mode": "other"}, {"output_formats": ["3mf"]},
            {"base": {"enabled": True, "height_mm": -1}}, {"parts": {"mode": "split"}},
        ):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.load(**fields)

    def test_rejects_cross_platform_path_traversal_and_missing_file(self):
        for path in ("../figure.glb", "..\\figure.glb", "C:\\figure.glb", "/figure.glb",
                     "\\\\server\\figure.glb", "figure.glb:stream", "figure.glb"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.load(input_mode="mesh", source_mesh=path)
