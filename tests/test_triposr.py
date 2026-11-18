import json
import os
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from figurine_runtime.config import load_job
from figurine_runtime.providers import generate


class TripoSRTest(unittest.TestCase):
    def test_job_requires_one_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            file = root / "job.json"
            file.write_text(json.dumps({
                "job_id": "one_image", "input_mode": "image", "provider": "triposr",
                "source_images": ["a.png", "b.png"], "target_height_mm": 150,
                "height_includes_base": True,
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly one"):
                load_job(file)

    def test_launch_is_offline_and_checks_glb_header(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "weights").mkdir()
            (root / "weights" / "model.ckpt").touch()
            (root / "source" / "tsr").mkdir(parents=True)
            (root / "source" / "tsr" / "system.py").touch()
            (root / "front.png").touch()
            output = root / "models" / "original.glb"
            job = {"provider": "triposr", "source_images": ["front.png"]}

            def worker(argv, **options):
                self.assertIn("-I", argv)
                self.assertIn(str(root / "front.png"), argv)
                self.assertEqual(options["env"]["HF_HUB_OFFLINE"], "1")
                self.assertNotIn("MESHY_API_KEY", options["env"])
                output.write_bytes(struct.pack("<4sII", b"glTF", 2, 20) + b"testdata")
                return type("FakeProcess", (), {"returncode": 0})()

            with patch.dict(os.environ, {"FIGURINE_TRIPOSR_HOME": str(root), "MESHY_API_KEY": "test-secret"}):
                with patch("figurine_runtime.providers.triposr.subprocess.run", side_effect=worker):
                    result = generate(job, root, output)
            self.assertEqual(result["provider"], "triposr")
            self.assertIs(result["local"], True)
