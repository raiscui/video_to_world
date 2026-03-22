"""
Isolated RoMa worker.

Run one frame's RoMa matching in a short-lived subprocess so CUDA state from
RoMaV2 cannot accumulate across the parent Stage-1 process.
"""

from __future__ import annotations

import argparse
import os

import torch

from data.data_loading import load_da3_camera_images
from models.roma_matcher import (
    RoMaMatcherWrapper,
    compute_roma_matches_for_frame,
    frame_has_uncached_roma_pairs,
    load_cached_matches,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute RoMa matches for one frame in an isolated subprocess.")
    parser.add_argument("--root-path", required=True)
    parser.add_argument("--num-frames", type=int, required=True)
    parser.add_argument("--stride", type=int, required=True)
    parser.add_argument("--current-frame-idx", type=int, required=True)
    parser.add_argument("--max-references", type=int, required=True)
    parser.add_argument("--num-samples-per-pair", type=int, required=True)
    parser.add_argument("--certainty-threshold", type=float, required=True)
    parser.add_argument("--roma-version", required=True)
    parser.add_argument("--roma-model", required=True)
    parser.add_argument("--reference-selection-mode", default="strided")
    parser.add_argument("--cache-path")
    parser.add_argument("--output-path", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # 只加载当前 Stage 1 需要的 DA3 图像,避免把整套 ICP 状态也带进来。
    images, _, _ = load_da3_camera_images(
        root_path=args.root_path,
        num_frames=args.num_frames,
        stride=args.stride,
        device=device,
    )

    cached_matches = None
    if args.cache_path and os.path.exists(args.cache_path):
        cached_matches = load_cached_matches(args.cache_path, device="cpu")

    needs_compute = frame_has_uncached_roma_pairs(
        current_frame_idx=args.current_frame_idx,
        max_references=args.max_references,
        cached_matches=cached_matches,
        reference_selection_mode=args.reference_selection_mode,
    )

    roma_matcher = None
    if needs_compute:
        roma_matcher = RoMaMatcherWrapper(
            device=device,
            model_type=args.roma_model,
            version=args.roma_version,
        )

    matches, _ = compute_roma_matches_for_frame(
        roma_matcher=roma_matcher,
        images=images,
        current_frame_idx=args.current_frame_idx,
        max_references=args.max_references,
        num_samples_per_pair=args.num_samples_per_pair,
        certainty_threshold=args.certainty_threshold,
        cache_path=args.cache_path,
        cached_matches=cached_matches,
        reference_selection_mode=args.reference_selection_mode,
    )

    # 匹配结果在主进程只以 CPU 形式消费,这里落盘前保持 CPU tensor 即可。
    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    torch.save({"matches": matches}, args.output_path)


if __name__ == "__main__":
    main()
