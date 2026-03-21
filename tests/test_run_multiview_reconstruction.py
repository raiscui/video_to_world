from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from preprocess_multiview import (
    PreprocessMultiViewConfig,
    default_scene_root,
    discover_view_inputs,
)
from run_multiview_reconstruction import (
    JointMultiViewConfig,
    build_preprocess_command,
    build_reconstruction_command,
    run_joint_pipeline,
)


class RunMultiViewReconstructionTests(unittest.TestCase):
    def test_discover_view_inputs_sorts_views_and_reads_scene_stem(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "full_scale2x"
            self._write_view(root, "10", "demo_scene")
            self._write_view(root, "2", "demo_scene")

            inputs = discover_view_inputs(
                PreprocessMultiViewConfig(
                    views_root=str(root),
                )
            )

            self.assertEqual([item.view_id for item in inputs], ["2", "10"])
            self.assertEqual(inputs[0].scene_stem, "demo_scene")

    def test_build_preprocess_command_targets_joint_scene_root(self) -> None:
        config = JointMultiViewConfig(
            views_root="/tmp/views",
            scene_root="/tmp/scene_root",
            view_ids=("0", "1"),
            preprocess_max_frames=64,
            preprocess_max_stride=4,
        )

        cmd = build_preprocess_command(config, Path("/tmp/scene_root"))

        self.assertIn("preprocess_multiview.py", cmd[1])
        self.assertIn("--scene-root", cmd)
        self.assertIn("/tmp/scene_root", cmd)
        self.assertIn("--view-ids", cmd)
        self.assertIn("0,1", cmd)
        self.assertIn("--max-frames", cmd)
        self.assertIn("64", cmd)

    def test_build_reconstruction_command_uses_single_root_path(self) -> None:
        config = JointMultiViewConfig(
            views_root="/tmp/views",
            pipeline_args=("--config.mode", "fast"),
        )

        cmd = build_reconstruction_command(config, Path("/tmp/scene_root"))

        self.assertIn("run_reconstruction.py", cmd[1])
        self.assertIn("--config.root-path", cmd)
        self.assertIn("/tmp/scene_root", cmd)
        self.assertIn("--config.mode", cmd)
        self.assertNotIn("--config.input-video", cmd)

    def test_run_joint_pipeline_writes_dry_run_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "full_scale2x"
            self._write_view(root, "0", "demo_scene")
            self._write_view(root, "1", "demo_scene")

            config = JointMultiViewConfig(
                views_root=str(root),
                dry_run=True,
                pipeline_args=("--config.mode", "fast"),
            )

            ok = run_joint_pipeline(config)
            self.assertTrue(ok)

            scene_root = default_scene_root(root)
            summary_path = scene_root / "multiview_reconstruction_summary.json"
            self.assertTrue(summary_path.is_file())

            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "dry_run")
            self.assertEqual(len(payload["views"]), 2)
            self.assertIn("--config.root-path", payload["commands"]["reconstruct"])

    def _write_view(self, root: Path, view_id: str, scene_stem: str) -> None:
        view_dir = root / view_id
        rgb_dir = view_dir / "rgb"
        manifest_dir = view_dir / "manifests"
        rgb_dir.mkdir(parents=True, exist_ok=True)
        manifest_dir.mkdir(parents=True, exist_ok=True)

        video_path = rgb_dir / f"{scene_stem}.mp4"
        video_path.write_bytes(b"")
        (manifest_dir / f"{scene_stem}.json").write_text(
            json.dumps({"scene_stem": scene_stem}, ensure_ascii=False),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
