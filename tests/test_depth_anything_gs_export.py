from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from depth_anything_3.specs import Gaussians, Prediction
from depth_anything_3.utils.export.gs import export_to_gs_video


class DepthAnythingGsExportTests(unittest.TestCase):
    def test_export_to_gs_video_writes_mp4_with_current_moviepy(self) -> None:
        """回归测试: 当前 MoviePy 环境下,gs_video 导出不应再因为 fps=None 崩溃。"""

        prediction = Prediction(
            depth=np.zeros((2, 16, 16), dtype=np.float32),
            is_metric=0,
            conf=np.ones((2, 16, 16), dtype=np.float32),
            extrinsics=np.stack([np.eye(4, dtype=np.float32) for _ in range(2)], axis=0),
            intrinsics=np.stack([np.eye(3, dtype=np.float32) for _ in range(2)], axis=0),
            gaussians=Gaussians(
                # 这里的 3DGS 内容对本测试并不重要。
                # 只要张量真实存在,导出函数就能完成设备和 dtype 推导。
                means=torch.zeros((1, 1, 3), dtype=torch.float32),
                scales=torch.zeros((1, 1, 3), dtype=torch.float32),
                rotations=torch.zeros((1, 1, 4), dtype=torch.float32),
                harmonics=torch.zeros((1, 1, 3, 1), dtype=torch.float32),
                opacities=torch.zeros((1, 1), dtype=torch.float32),
            ),
        )

        fake_color = torch.rand((1, 3, 3, 16, 16), dtype=torch.float32)
        fake_depth = torch.zeros((1, 3, 16, 16), dtype=torch.float32)
        fake_extr = torch.stack([torch.eye(4, dtype=torch.float32) for _ in range(3)], dim=0).unsqueeze(0)
        fake_intr = torch.stack([torch.eye(3, dtype=torch.float32) for _ in range(3)], dim=0).unsqueeze(0)

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch(
                "depth_anything_3.utils.export.gs.run_renderer_in_chunk_w_trj_mode",
                return_value=(fake_color, fake_depth, fake_extr, fake_intr),
            ):
                export_to_gs_video(
                    prediction=prediction,
                    export_dir=tmp_dir,
                    vis_depth=None,
                    enable_tqdm=False,
                    output_name="probe",
                )

            video_path = Path(tmp_dir) / "gs_video" / "probe.mp4"
            transforms_path = Path(tmp_dir) / "gs_video" / "probe_transforms.json"

            self.assertTrue(video_path.is_file())
            self.assertGreater(video_path.stat().st_size, 0)
            self.assertTrue(transforms_path.is_file())


if __name__ == "__main__":
    unittest.main()
