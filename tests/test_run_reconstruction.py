from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import run_reconstruction
from configs.stage3_gs import GSConfig
from run_reconstruction import PipelineConfig


class RunReconstructionTests(unittest.TestCase):
    def test_fast_mode_preserves_explicit_gs_num_iters_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "scene"
            root.mkdir()

            commands: list[list[str]] = []
            config = PipelineConfig(
                root_path=str(root),
                mode="fast",
                dry_run=True,
                skip_alignment=True,
                alignment_run="frame_to_model_icp_demo",
                skip_inverse_deform=True,
                inverse_deform_dir=str(root / "frame_to_model_icp_demo" / "inverse_deformation"),
                gs=replace(GSConfig(), num_iters=150),
            )

            with patch.object(run_reconstruction, "_run", side_effect=lambda cmd, dry_run=False: commands.append(cmd)):
                run_reconstruction.main(config)

            self.assertEqual(len(commands), 1)
            self.assertIn("--config.num-iters", commands[0])
            self.assertEqual(commands[0][commands[0].index("--config.num-iters") + 1], "150")

    def test_fast_mode_uses_renderer_default_when_gs_num_iters_not_overridden(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir) / "scene"
            root.mkdir()

            commands: list[list[str]] = []
            config = PipelineConfig(
                root_path=str(root),
                mode="fast",
                dry_run=True,
                skip_alignment=True,
                alignment_run="frame_to_model_icp_demo",
                skip_inverse_deform=True,
                inverse_deform_dir=str(root / "frame_to_model_icp_demo" / "inverse_deformation"),
            )

            with patch.object(run_reconstruction, "_run", side_effect=lambda cmd, dry_run=False: commands.append(cmd)):
                run_reconstruction.main(config)

            self.assertEqual(len(commands), 1)
            self.assertIn("--config.num-iters", commands[0])
            self.assertEqual(commands[0][commands[0].index("--config.num-iters") + 1], "10000")


if __name__ == "__main__":
    unittest.main()
