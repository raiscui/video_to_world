import unittest
from unittest import mock

import torch

import models.roma_matcher as roma_matcher_module
from losses.correspondence import compute_correspondence_loss_with_model_segments
from models.roma_matcher import RoMaMatchData, compute_roma_matches_for_frame, frame_has_uncached_roma_pairs
from third_party.RoMaV2.src.romav2.romav2 import kde


class _FakeMatcher:
    version = "v1"
    device = "cpu"
    model_type = "fake"

    def match_images(self, image_a, image_b, num_samples=5000, certainty_threshold=0.0):
        del image_a, image_b, num_samples, certainty_threshold
        return (
            torch.tensor([[0.0, 0.0], [1.0, 0.0]], dtype=torch.float32),
            torch.tensor([[0.0, 0.0], [1.0, 0.0]], dtype=torch.float32),
            torch.tensor([0.9, 0.8], dtype=torch.float32),
        )


class RomaMemoryOffloadTests(unittest.TestCase):
    def test_kde_chunked_matches_dense_result(self):
        samples = torch.randn((64, 4), dtype=torch.float32)

        dense_density = kde(samples, half=False, max_pairwise_elements=None)
        chunked_density = kde(samples, half=False, max_pairwise_elements=512)

        self.assertEqual(dense_density.shape, chunked_density.shape)
        self.assertTrue(torch.allclose(chunked_density, dense_density, atol=1e-5, rtol=1e-4))

    def test_compute_roma_matches_for_frame_keeps_matches_on_cpu(self):
        matcher = _FakeMatcher()
        images = torch.zeros((3, 3, 2, 2), dtype=torch.float32)

        matches, returned_matcher = compute_roma_matches_for_frame(
            roma_matcher=matcher,
            images=images,
            current_frame_idx=2,
            max_references=2,
            num_samples_per_pair=2,
            certainty_threshold=0.0,
        )

        self.assertEqual(len(matches), 2)
        self.assertIs(returned_matcher, matcher)
        for match in matches:
            self.assertEqual(match.kpts_src.device.type, "cpu")
            self.assertEqual(match.kpts_ref.device.type, "cpu")
            self.assertEqual(match.certainty.device.type, "cpu")

    def test_compute_roma_matches_for_frame_all_cached_allows_none_matcher(self):
        images = torch.zeros((3, 3, 2, 2), dtype=torch.float32)
        cached_matches = {
            (2, 0): RoMaMatchData(
                src_frame_idx=2,
                ref_frame_idx=0,
                kpts_src=torch.tensor([[0.0, 0.0]], dtype=torch.float32),
                kpts_ref=torch.tensor([[1.0, 1.0]], dtype=torch.float32),
                certainty=torch.tensor([0.9], dtype=torch.float32),
            ),
            (2, 1): RoMaMatchData(
                src_frame_idx=2,
                ref_frame_idx=1,
                kpts_src=torch.tensor([[0.5, 0.5]], dtype=torch.float32),
                kpts_ref=torch.tensor([[1.5, 1.5]], dtype=torch.float32),
                certainty=torch.tensor([0.8], dtype=torch.float32),
            ),
        }

        matches, returned_matcher = compute_roma_matches_for_frame(
            roma_matcher=None,
            images=images,
            current_frame_idx=2,
            max_references=2,
            num_samples_per_pair=2,
            certainty_threshold=0.0,
            cached_matches=cached_matches,
        )

        self.assertIsNone(returned_matcher)
        self.assertEqual(len(matches), 2)
        self.assertEqual({(m.src_frame_idx, m.ref_frame_idx) for m in matches}, {(2, 0), (2, 1)})

    def test_compute_roma_matches_for_frame_does_not_rebuild_matcher_within_single_frame(self):
        class _FakeV2Matcher:
            def __init__(self, device="cuda", model_type="indoor", version="v2"):
                self.device = device
                self.model_type = model_type
                self.version = version

            def match_images(self, image_a, image_b, num_samples=5000, certainty_threshold=0.0):
                del image_a, image_b, num_samples, certainty_threshold
                return (
                    torch.tensor([[0.0, 0.0]], dtype=torch.float32),
                    torch.tensor([[0.0, 0.0]], dtype=torch.float32),
                    torch.tensor([0.9], dtype=torch.float32),
                )

        initial_matcher = _FakeV2Matcher()
        images = torch.zeros((6, 3, 2, 2), dtype=torch.float32)

        with mock.patch.object(
            roma_matcher_module,
            "RoMaMatcherWrapper",
            side_effect=AssertionError("single-frame matching should not rebuild RoMa matcher"),
        ), mock.patch(
            "torch.cuda.is_available",
            return_value=True,
        ):
            matches, returned_matcher = compute_roma_matches_for_frame(
                roma_matcher=initial_matcher,
                images=images,
                current_frame_idx=5,
                max_references=5,
                num_samples_per_pair=1,
                certainty_threshold=0.0,
            )

        self.assertEqual(len(matches), 5)
        self.assertIs(returned_matcher, initial_matcher)

    def test_frame_has_uncached_roma_pairs_distinguishes_cached_and_uncached(self):
        cached_matches = {
            (2, 0): RoMaMatchData(2, 0, torch.zeros((1, 2)), torch.zeros((1, 2)), torch.ones(1)),
            (2, 1): RoMaMatchData(2, 1, torch.zeros((1, 2)), torch.zeros((1, 2)), torch.ones(1)),
        }

        self.assertFalse(
            frame_has_uncached_roma_pairs(
                current_frame_idx=2,
                max_references=2,
                cached_matches=cached_matches,
            )
        )
        self.assertTrue(
            frame_has_uncached_roma_pairs(
                current_frame_idx=3,
                max_references=3,
                cached_matches=cached_matches,
            )
        )

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
