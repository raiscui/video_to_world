import unittest

import torch

from losses.correspondence import compute_correspondence_loss_with_model_segments
from models.roma_matcher import RoMaMatchData, compute_roma_matches_for_frame


class _FakeMatcher:
    def match_images(self, image_a, image_b, num_samples=5000, certainty_threshold=0.0):
        del image_a, image_b, num_samples, certainty_threshold
        return (
            torch.tensor([[0.0, 0.0], [1.0, 0.0]], dtype=torch.float32),
            torch.tensor([[0.0, 0.0], [1.0, 0.0]], dtype=torch.float32),
            torch.tensor([0.9, 0.8], dtype=torch.float32),
        )


class RomaMemoryOffloadTests(unittest.TestCase):
    def test_compute_roma_matches_for_frame_keeps_matches_on_cpu(self):
        matcher = _FakeMatcher()
        images = torch.zeros((3, 3, 2, 2), dtype=torch.float32)

        matches = compute_roma_matches_for_frame(
            roma_matcher=matcher,
            images=images,
            current_frame_idx=2,
            max_references=2,
            num_samples_per_pair=2,
            certainty_threshold=0.0,
        )

        self.assertEqual(len(matches), 2)
        for match in matches:
            self.assertEqual(match.kpts_src.device.type, "cpu")
            self.assertEqual(match.kpts_ref.device.type, "cpu")
            self.assertEqual(match.certainty.device.type, "cpu")

    def test_correspondence_loss_accepts_cpu_offloaded_matches(self):
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        matches = [
            RoMaMatchData(
                src_frame_idx=1,
                ref_frame_idx=0,
                kpts_src=torch.tensor([[0.0, 0.0], [1.0, 0.0]], dtype=torch.float32),
                kpts_ref=torch.tensor([[0.0, 0.0], [1.0, 0.0]], dtype=torch.float32),
                certainty=torch.tensor([1.0, 0.5], dtype=torch.float32),
            )
        ]

        src_points_transformed = torch.tensor(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
            dtype=torch.float32,
            device=device,
        )
        model_points = torch.tensor(
            [[0.0, 0.0, 0.0], [1.2, 0.0, 0.0]],
            dtype=torch.float32,
            device=device,
        )
        model_colors = torch.tensor(
            [[0.2, 0.2, 0.2], [0.7, 0.7, 0.7]],
            dtype=torch.float32,
            device=device,
        )
        src_colors = torch.tensor(
            [[0.2, 0.2, 0.2], [0.8, 0.8, 0.8]],
            dtype=torch.float32,
            device=device,
        )

        geometry_loss, color_loss, num_matches = compute_correspondence_loss_with_model_segments(
            matches_data=matches,
            src_points_transformed=src_points_transformed,
            model_points=model_points,
            model_colors=model_colors,
            model_frame_segments=[(0, 2)],
            ref_frame_indices=[0],
            src_valid_pixel_indices=torch.tensor([0, 1], dtype=torch.long),
            model_valid_pixel_indices_list=[torch.tensor([0, 1], dtype=torch.long)],
            H=1,
            W=2,
            src_colors=src_colors,
            color_loss_weight=0.5,
            max_corr_dist=None,
        )

        self.assertEqual(num_matches, 2)
        self.assertEqual(geometry_loss.device.type, device.type)
        self.assertEqual(color_loss.device.type, device.type)
        self.assertGreater(float(geometry_loss.item()), 0.0)


if __name__ == "__main__":
    unittest.main()
