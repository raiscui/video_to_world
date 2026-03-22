"""
RoMa / RoMaV2 matcher wrapper.

Extracted from the frame-to-model ICP pipeline to keep heavyweight
model construction out of large algorithm scripts.
"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import torch

logger = logging.getLogger(__name__)


@dataclass
class RoMaMatchData:
    """Container for RoMa matches between frame pairs."""

    src_frame_idx: int
    ref_frame_idx: int
    kpts_src: torch.Tensor  # (N, 2) pixel coords in source frame
    kpts_ref: torch.Tensor  # (N, 2) pixel coords in reference frame
    certainty: torch.Tensor  # (N,) RoMa certainty scores

    def to(self, device: str | torch.device) -> "RoMaMatchData":
        """返回一个迁移到目标 device 的新对象."""
        return RoMaMatchData(
            src_frame_idx=self.src_frame_idx,
            ref_frame_idx=self.ref_frame_idx,
            kpts_src=self.kpts_src.to(device),
            kpts_ref=self.kpts_ref.to(device),
            certainty=self.certainty.to(device),
        )


class RoMaMatcherWrapper:
    """
    Wrapper for RoMa/RoMaV2 dense feature matching.

    RoMa produces pixel-dense warps and certainties for any image pair.
    Supports both RoMa v1 and RoMaV2.
    """

    def __init__(
        self,
        device: str = "cuda",
        model_type: str = "indoor",  # v1: "outdoor", "indoor", "tiny"; v2: ignored
        version: str = "v2",  # "v1" or "v2"
    ):
        self.device = device
        self.model_type = model_type
        self.version = version

        if version == "v2":
            self._init_romav2(device)
        elif version == "v1":
            self._init_romav1(device, model_type)
        else:
            raise ValueError(f"Unknown version: {version}. Use 'v1' or 'v2'.")

    def _init_romav2(self, device: str):
        """Initialize RoMaV2 model."""
        logger.info("Loading RoMaV2 model...")

        try:
            from romav2 import RoMaV2
        except ImportError:
            raise ImportError(
                "RoMaV2 is not installed. Run `pixi run setup-romav2` from the repository root.\n"
                "Fallback: python -m pip install git+https://github.com/Parskatt/RoMaV2.git"
            )

        cfg = RoMaV2.Cfg(compile=False)
        self.model = RoMaV2(cfg).to(device)
        self.model.eval()
        logger.info("RoMaV2 model loaded successfully")

    def _init_romav1(self, device: str, model_type: str):
        """Initialize RoMa v1 model."""
        logger.info(f"Loading RoMa v1 model ({model_type})...")

        try:
            import romatch
        except ImportError:
            raise ImportError(
                "RoMa is not installed. Run `pixi install` from the repository root.\n"
                "Fallback: python -m pip install romatch"
            )

        # Load the appropriate model
        if model_type == "outdoor":
            self.model = romatch.roma_outdoor(device=device)
        elif model_type == "indoor":
            self.model = romatch.roma_indoor(device=device)
        elif model_type == "tiny":
            self.model = romatch.tiny_roma_v1_outdoor(device=device)
        else:
            raise ValueError(f"Unknown model_type for v1: {model_type}")

        logger.info("RoMa v1 model loaded successfully")

    @torch.no_grad()
    def match_images(
        self,
        image_a: torch.Tensor,  # (3, H, W) in [0, 1]
        image_b: torch.Tensor,  # (3, H, W) in [0, 1]
        num_samples: int = 5000,
        certainty_threshold: float = 0.0,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Match two images using RoMa/RoMaV2.

        Args:
            image_a: First image (3, H, W) in [0, 1]
            image_b: Second image (3, H, W) in [0, 1]
            num_samples: Number of matches to sample
            certainty_threshold: Minimum certainty for matches

        Returns:
            kpts_a: (N, 2) keypoints in image A (x, y) in pixel coordinates
            kpts_b: (N, 2) keypoints in image B (x, y) in pixel coordinates
            certainty: (N,) certainty/overlap scores for each match
        """
        if self.version == "v2":
            return self._match_images_v2(image_a, image_b, num_samples, certainty_threshold)
        else:
            return self._match_images_v1(image_a, image_b, num_samples, certainty_threshold)

    def _match_images_v2(
        self,
        image_a: torch.Tensor,
        image_b: torch.Tensor,
        num_samples: int,
        certainty_threshold: float,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Match using RoMaV2."""
        import numpy as np
        from PIL import Image

        _, H_A, W_A = image_a.shape
        _, H_B, W_B = image_b.shape

        # Convert to PIL images
        img_a_np = (image_a.permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
        img_b_np = (image_b.permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)

        img_a_pil = Image.fromarray(img_a_np)
        img_b_pil = Image.fromarray(img_b_np)

        if self.device.startswith("cuda") and torch.cuda.is_available():
            # 先清理上一轮 ICP / RoMa 留下的可释放缓存,减少显存碎片。
            torch.cuda.empty_cache()

        # Get dense predictions from RoMaV2
        preds = self.model.match(img_a_pil, img_b_pil)

        # Sample matches
        # RoMaV2 sample() returns: matches, overlaps, precision_AB, precision_BA
        matches, overlaps, precision_AB, precision_BA = self.model.sample(preds, num_samples)
        del preds, precision_AB, precision_BA

        # Convert to pixel coordinates
        kpts_a, kpts_b = self.model.to_pixel_coordinates(matches, H_A, W_A, H_B, W_B)
        del matches

        # Use overlaps as certainty score
        certainty_sampled = overlaps
        del overlaps

        # Filter by certainty threshold
        if certainty_threshold > 0:
            mask = certainty_sampled >= certainty_threshold
            kpts_a = kpts_a[mask]
            kpts_b = kpts_b[mask]
            certainty_sampled = certainty_sampled[mask]

        # 后续匹配历史与缓存不需要常驻 GPU,这里直接下沉到 CPU.
        kpts_a = kpts_a.detach().cpu()
        kpts_b = kpts_b.detach().cpu()
        certainty_sampled = certainty_sampled.detach().cpu()

        if self.device.startswith("cuda") and torch.cuda.is_available():
            torch.cuda.empty_cache()

        return kpts_a, kpts_b, certainty_sampled

    def _match_images_v1(
        self,
        image_a: torch.Tensor,
        image_b: torch.Tensor,
        num_samples: int,
        certainty_threshold: float,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Match using RoMa v1."""
        import numpy as np
        from PIL import Image

        _, H_A, W_A = image_a.shape
        _, H_B, W_B = image_b.shape

        # Convert to PIL images (RoMa expects file paths or PIL images)
        img_a_np = (image_a.permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
        img_b_np = (image_b.permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)

        img_a_pil = Image.fromarray(img_a_np)
        img_b_pil = Image.fromarray(img_b_np)

        if self.device.startswith("cuda") and torch.cuda.is_available():
            torch.cuda.empty_cache()

        # Get dense warp and certainty
        warp, certainty = self.model.match(img_a_pil, img_b_pil, device=self.device)

        # Sample matches
        matches, certainty_sampled = self.model.sample(warp, certainty, num=num_samples)
        del warp, certainty

        # Convert to pixel coordinates
        # RoMa returns matches in [-1, 1] x [-1, 1] normalized coordinates
        kpts_a, kpts_b = self.model.to_pixel_coordinates(matches, H_A, W_A, H_B, W_B)
        del matches

        # Filter by certainty threshold
        if certainty_threshold > 0:
            mask = certainty_sampled >= certainty_threshold
            kpts_a = kpts_a[mask]
            kpts_b = kpts_b[mask]
            certainty_sampled = certainty_sampled[mask]

        kpts_a = kpts_a.detach().cpu()
        kpts_b = kpts_b.detach().cpu()
        certainty_sampled = certainty_sampled.detach().cpu()

        if self.device.startswith("cuda") and torch.cuda.is_available():
            torch.cuda.empty_cache()

        return kpts_a, kpts_b, certainty_sampled


def get_local_indices_for_pixels_batch(
    *,
    pixels_x: torch.Tensor,  # (K,)
    pixels_y: torch.Tensor,  # (K,)
    valid_pixel_indices: torch.Tensor,  # (M,) flat pixel indices that have valid 3D points
    H: int,
    W: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Map pixel coordinates to local point indices.

    `valid_pixel_indices` is a per-frame list of the flat pixel indices kept when building the
    point cloud for that frame (e.g. after depth/conf filtering). This function maps arbitrary
    (x,y) pixel coordinates to indices into that filtered list.

    Returns:
        local_indices: (K,) long tensor with point indices for valid pixels (undefined for invalid)
        valid_mask: (K,) bool mask indicating which input pixels had valid 3D points
    """
    device = valid_pixel_indices.device
    K = int(pixels_x.numel())

    pixels_x = pixels_x.round().long().clamp(0, W - 1)
    pixels_y = pixels_y.round().long().clamp(0, H - 1)
    query_flat_indices = (pixels_y * W + pixels_x).to(device)

    valid_sorted, sort_order = torch.sort(valid_pixel_indices)
    search_pos = torch.searchsorted(valid_sorted, query_flat_indices)

    in_bounds = search_pos < int(valid_sorted.numel())
    valid_mask = torch.zeros(K, dtype=torch.bool, device=device)
    valid_mask[in_bounds] = valid_sorted[search_pos[in_bounds]] == query_flat_indices[in_bounds]

    local_indices = torch.zeros(K, dtype=torch.long, device=device)
    local_indices[valid_mask] = sort_order[search_pos[valid_mask]]
    return local_indices, valid_mask


# ================================================================
#                    RoMa Matching Loss Utilities
# ================================================================


def select_reference_frames(
    current_frame_idx: int,
    num_previous_frames: int,
    max_references: int = 20,
    mode: str = "strided",
) -> list[int]:
    """
    Select reference frames for matching with good temporal coverage.

    When there are more previous frames than max_references, select frames
    with an optimal stride to maintain good coverage across the sequence.

    Args:
        current_frame_idx: Index of the current (source) frame
        num_previous_frames: Total number of previous frames available (0 to current_frame_idx-1)
        max_references: Maximum number of reference frames to return

    Returns:
        List of frame indices to use as references
    """
    if num_previous_frames == 0:
        return []

    # All available previous frame indices
    all_previous = list(range(current_frame_idx))

    if len(all_previous) <= max_references:
        return all_previous

    if mode == "recent_and_strided":
        # Allocate half of the references to the most recent frames,
        # and the other half to evenly spaced older frames.
        num_recent = max_references // 2
        num_strided = max_references - num_recent

        # Most recent frames (immediately preceding the current frame)
        recent = all_previous[-num_recent:] if num_recent > 0 else []

        # Remaining older frames for strided sampling
        remaining = all_previous[: len(all_previous) - len(recent)]

        strided = []
        if remaining and num_strided > 0:
            stride = len(remaining) / num_strided
            for i in range(num_strided):
                idx = int(i * stride)
                if idx < len(remaining):
                    strided.append(remaining[idx])

        selected = sorted(set(recent + strided))
        # In rare edge cases we might end up with fewer than max_references
        # (e.g. heavy overlap between recent and strided); this is acceptable.
        return selected

    # Default behaviour: evenly spaced strided sampling.
    stride = len(all_previous) / max_references

    selected = []
    for i in range(max_references):
        idx = int(i * stride)
        if idx < len(all_previous):
            selected.append(all_previous[idx])

    # Always include the most recent frame if not already included
    if all_previous[-1] not in selected:
        selected[-1] = all_previous[-1]

    return sorted(selected)


# ================================================================
#                    Match Caching Utilities
# ================================================================


def _get_cache_key(
    roma_version: str,
    roma_model: str,
    num_samples_per_pair: int,
    certainty_threshold: float,
    num_frames: int,
    stride: int,
    reference_selection_mode: Optional[str] = None,
) -> str:
    """Generate a cache key based on matching parameters."""
    key_str = f"{roma_version}_{roma_model}_{num_samples_per_pair}_{certainty_threshold}_{num_frames}_{stride}"
    # Only differentiate cache keys when the mode changes the sampled references.
    if reference_selection_mode == "recent_and_strided":
        key_str = f"{key_str}_{reference_selection_mode}"
    return hashlib.md5(key_str.encode()).hexdigest()[:16]


def _get_cache_path(root_path: str, cache_key: str) -> str:
    """Get the cache file path for a given root path and cache key."""
    cache_dir = os.path.join(root_path, "roma_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"matches_{cache_key}.pt")


def load_cached_matches(
    cache_path: str,
    device: str = "cuda",
) -> dict[tuple[int, int], RoMaMatchData]:
    """
    Load cached matches from disk.

    Returns:
        Dictionary mapping (src_frame_idx, ref_frame_idx) -> RoMaMatchData
    """
    if not os.path.exists(cache_path):
        return {}

    try:
        data = torch.load(cache_path, weights_only=False, map_location=device)
        cached = {}
        for pair, match_dict in data.items():
            cached[pair] = RoMaMatchData(
                src_frame_idx=match_dict["src_frame_idx"],
                ref_frame_idx=match_dict["ref_frame_idx"],
                kpts_src=match_dict["kpts_src"].to(device),
                kpts_ref=match_dict["kpts_ref"].to(device),
                certainty=match_dict["certainty"].to(device),
            )
        logger.info(f"Loaded {len(cached)} cached match pairs from {cache_path}")
        return cached
    except Exception as e:
        logger.warning(f"Failed to load cache from {cache_path}: {e}")
        return {}


def save_matches_to_cache(
    cache_path: str,
    matches: list[RoMaMatchData],
    existing_cache: Optional[dict[tuple[int, int], RoMaMatchData]] = None,
):
    """
    Save matches to cache, merging with existing cache if provided.

    Args:
        cache_path: Path to cache file
        matches: List of new matches to save
        existing_cache: Optional existing cache to merge with
    """
    # Start with existing cache or empty dict
    cache_dict = {}
    if existing_cache is not None:
        for pair, match_data in existing_cache.items():
            cache_dict[pair] = {
                "src_frame_idx": match_data.src_frame_idx,
                "ref_frame_idx": match_data.ref_frame_idx,
                "kpts_src": match_data.kpts_src.cpu(),
                "kpts_ref": match_data.kpts_ref.cpu(),
                "certainty": match_data.certainty.cpu(),
            }

    # Add new matches (overwrite if pair already exists)
    for match in matches:
        pair = (match.src_frame_idx, match.ref_frame_idx)
        cache_dict[pair] = {
            "src_frame_idx": match.src_frame_idx,
            "ref_frame_idx": match.ref_frame_idx,
            "kpts_src": match.kpts_src.cpu(),
            "kpts_ref": match.kpts_ref.cpu(),
            "certainty": match.certainty.cpu(),
        }

    # Save to disk
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    torch.save(cache_dict, cache_path)
    logger.info(f"Saved {len(cache_dict)} match pairs to cache: {cache_path}")


def compute_roma_matches_for_frame(
    roma_matcher: Optional[RoMaMatcherWrapper],
    images: torch.Tensor,  # (N, 3, H, W) in [0, 1]
    current_frame_idx: int,
    max_references: int = 20,
    num_samples_per_pair: int = 5000,
    certainty_threshold: float = 0.0,
    cache_path: Optional[str] = None,
    cached_matches: Optional[dict[tuple[int, int], RoMaMatchData]] = None,
    reference_selection_mode: str = "strided",
) -> tuple[list[RoMaMatchData], Optional[RoMaMatcherWrapper]]:
    """
    Compute RoMa matches between the current frame and all selected previous frames.
    Optionally uses cached matches to avoid recomputation.

    Args:
        roma_matcher:
            已初始化的 RoMa matcher。
            当当前帧所有 pair 都能直接命中 cache 时,允许传入 None。
        images: All images tensor (N, 3, H, W) in [0, 1]
        current_frame_idx: Index of current frame
        max_references: Maximum number of reference frames
        num_samples_per_pair: Number of matches to sample per frame pair
        certainty_threshold: Minimum RoMa certainty for matches
        cache_path: Optional path to cache file for saving matches
        cached_matches: Optional dictionary of cached matches: (src_idx, ref_idx) -> RoMaMatchData

    Returns:
        matches_list:
            当前帧和参考帧之间的 RoMa 匹配结果。
        roma_matcher:
            当前函数结束后仍应继续使用的 matcher 实例。
            说明:
            - 该返回值很重要,因为函数内部可能为了限制单帧内的 GPU 累积
              而重建 matcher。
            - 如果调用方继续持有旧实例,那内部刷新就只会停留在函数局部,
              无法真正缩短外层生命周期。
    """
    ref_frames = select_reference_frames(
        current_frame_idx,
        current_frame_idx,  # num_previous_frames
        max_references,
        mode=reference_selection_mode,
    )

    if not ref_frames:
        return [], roma_matcher

    matches_list: list[RoMaMatchData] = []
    current_image = images[current_frame_idx]

    # Track which pairs we computed vs loaded from cache
    computed_pairs = []
    cached_pairs = []

    for ref_idx in ref_frames:
        pair = (current_frame_idx, ref_idx)

        # Check cache first
        if cached_matches is not None and pair in cached_matches:
            matches_list.append(cached_matches[pair])
            cached_pairs.append(pair)
            continue

        # Compute match if not in cache
        if roma_matcher is None:
            raise ValueError(
                "RoMa matcher is required when uncached pairs need to be computed. "
                "Pass a matcher instance or route this frame through an isolated worker."
            )

        ref_image = images[ref_idx]

        kpts_src, kpts_ref, certainty = roma_matcher.match_images(
            current_image,
            ref_image,
            num_samples=num_samples_per_pair,
            certainty_threshold=certainty_threshold,
        )

        if len(kpts_src) > 0:
            match_data = RoMaMatchData(
                src_frame_idx=current_frame_idx,
                ref_frame_idx=ref_idx,
                kpts_src=kpts_src,
                kpts_ref=kpts_ref,
                certainty=certainty,
            )
            matches_list.append(match_data)
            computed_pairs.append(pair)

    # Log cache usage
    if cached_matches is not None:
        if cached_pairs:
            logger.info(
                f"Frame {current_frame_idx}: Loaded {len(cached_pairs)} pairs from cache, "
                f"computed {len(computed_pairs)} new pairs"
            )
        elif computed_pairs:
            logger.info(f"Frame {current_frame_idx}: Computed {len(computed_pairs)} pairs (no cache hits)")

    return matches_list, roma_matcher


def frame_has_uncached_roma_pairs(
    *,
    current_frame_idx: int,
    max_references: int,
    cached_matches: Optional[dict[tuple[int, int], RoMaMatchData]],
    reference_selection_mode: str = "strided",
) -> bool:
    """判断当前帧是否仍有未命中缓存的 RoMa pair."""
    ref_frames = select_reference_frames(
        current_frame_idx,
        current_frame_idx,
        max_references,
        mode=reference_selection_mode,
    )
    if not ref_frames:
        return False
    if cached_matches is None:
        return True
    return any((current_frame_idx, ref_idx) not in cached_matches for ref_idx in ref_frames)


def compute_roma_matches_for_frame_isolated(
    *,
    root_path: str,
    num_frames: int,
    stride: int,
    current_frame_idx: int,
    max_references: int,
    num_samples_per_pair: int,
    certainty_threshold: float,
    roma_version: str,
    roma_model: str,
    reference_selection_mode: str = "strided",
    cache_path: Optional[str] = None,
) -> list[RoMaMatchData]:
    """在子进程里计算当前帧的 RoMa 匹配.

    RoMaV2 的 GPU 状态会随着 pair 数在当前进程里累计。
    即使 Python 张量和 matcher 对象已经删除,`memory_allocated()` 也不会
    及时回落。这里用子进程边界做强释放,保证每个 uncached frame 的
    匹配结束后整段 GPU 状态随进程退出一起回收。
    """
    repo_root = Path(__file__).resolve().parents[1]

    with tempfile.TemporaryDirectory(prefix="roma_worker_") as tmpdir:
        output_path = os.path.join(tmpdir, f"frame_{current_frame_idx:05d}_matches.pt")
        cmd = [
            sys.executable,
            "-m",
            "models.roma_matcher_worker",
            "--root-path",
            root_path,
            "--num-frames",
            str(num_frames),
            "--stride",
            str(stride),
            "--current-frame-idx",
            str(current_frame_idx),
            "--max-references",
            str(max_references),
            "--num-samples-per-pair",
            str(num_samples_per_pair),
            "--certainty-threshold",
            str(certainty_threshold),
            "--roma-version",
            roma_version,
            "--roma-model",
            roma_model,
            "--reference-selection-mode",
            reference_selection_mode,
            "--output-path",
            output_path,
        ]
        if cache_path is not None:
            cmd.extend(["--cache-path", cache_path])

        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            f"{repo_root}:{existing_pythonpath}" if existing_pythonpath else str(repo_root)
        )

        result = subprocess.run(
            cmd,
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "RoMa isolated worker failed.\n"
                f"command: {' '.join(cmd)}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )

        payload = torch.load(output_path, map_location="cpu", weights_only=False)
        matches = payload.get("matches", [])
        if not isinstance(matches, list):
            raise RuntimeError(f"Unexpected isolated worker payload at {output_path}: {type(matches)}")
        return matches


# ================================================================
#                    Match History Management
# ================================================================


@dataclass
class MatchHistory:
    """
    Maintains history of all RoMa matches for use in bundle adjustment.
    """

    all_matches: list[RoMaMatchData]

    def __init__(self):
        self.all_matches = []

    def add_matches(self, matches: list[RoMaMatchData]):
        """Add new matches to the history."""
        self.all_matches.extend(matches)

    def get_matches_for_frames(self, src_frame_idx: int, ref_frame_indices: list[int]) -> list[RoMaMatchData]:
        """Get matches where source is src_frame_idx and ref is in ref_frame_indices."""
        return [
            m for m in self.all_matches if m.src_frame_idx == src_frame_idx and m.ref_frame_idx in ref_frame_indices
        ]

    def get_all_matches_involving_frame(self, frame_idx: int) -> list[RoMaMatchData]:
        """Get all matches where frame_idx is either source or reference."""
        return [m for m in self.all_matches if m.src_frame_idx == frame_idx or m.ref_frame_idx == frame_idx]

    def get_unique_frame_pairs(self) -> list[tuple[int, int]]:
        """Get list of unique (src, ref) frame pairs."""
        pairs = set()
        for m in self.all_matches:
            pairs.add((m.src_frame_idx, m.ref_frame_idx))
        return sorted(list(pairs))

    def __len__(self):
        return len(self.all_matches)
