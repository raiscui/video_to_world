from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from configs.eval_gs import EvalGSConfig
from eval_gs import _resolve_transforms_path


class EvalGSTests(unittest.TestCase):
    def test_missing_default_gs_video_transforms_disables_gs_video_render(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "scene"
            root.mkdir()

            config = EvalGSConfig(root_path=str(root))
            _resolve_transforms_path(config)

            self.assertEqual(
                config.transforms_path,
                str(root / "gs_video" / "0000_extend_transforms.json"),
            )
            self.assertFalse(config.render_gs_video_path)

    def test_existing_default_gs_video_transforms_keeps_gs_video_render_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "scene"
            transforms_path = root / "gs_video" / "0000_extend_transforms.json"
            transforms_path.parent.mkdir(parents=True)
            transforms_path.write_text("{}", encoding="utf-8")

            config = EvalGSConfig(root_path=str(root))
            _resolve_transforms_path(config)

            self.assertEqual(config.transforms_path, str(transforms_path))
            self.assertTrue(config.render_gs_video_path)


if __name__ == "__main__":
    unittest.main()
