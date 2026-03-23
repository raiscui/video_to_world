#!/usr/bin/env python3
"""
把同一场景的多个视角视频预处理成单一 scene_root。

核心思路:
1. 每个视角先独立跑一次现有 `preprocess_video.py`
2. 再把每个视角产出的 `results.npz` 和 `frames_subsampled` 按统一顺序合并
3. 最终得到一个共享的 `<scene_root>/exports/npz/results.npz`
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence


PROJECT_ROOT = Path(__file__).resolve().parent
SUPPORTED_IMAGE_EXTS = ("png", "jpg", "jpeg", "webp")
DEFAULT_VIDEO_GLOB = "auto"
AUTO_VIDEO_GLOBS = (
    "rgb/*.mp4",
    "generated_videos/*.mp4",
    "*.mp4",
)


@dataclass(frozen=True)
class MultiViewInput:
    """单个视角的视频输入。"""

    view_id: str
    view_dir: str
    input_video: str
    scene_stem: str


@dataclass(frozen=True)
class PreprocessMultiViewConfig:
    """多视角联合预处理配置。"""

    views_root: str
    scene_root: str | None = None
    view_ids: tuple[str, ...] = ()
    video_glob: str = DEFAULT_VIDEO_GLOB
    model_name: str = "depth-anything/DA3NESTED-GIANT-LARGE"
    image_ext: str = "png"
    max_frames: int = 100
    max_stride: int = 8
    overwrite: bool = False
    dry_run: bool = False


def parse_args(argv: Sequence[str] | None = None) -> PreprocessMultiViewConfig:
    parser = argparse.ArgumentParser(
        description=(
            "Preprocess multiple view videos of the same scene into a single scene root.\n"
            "Expected layout example:\n"
            "  <views_root>/0/rgb/foo.mp4\n"
            "  <views_root>/1/rgb/foo.mp4\n"
            "  <views_root>/2/generated_videos/generated_video_0.mp4\n"
            "  ...\n"
            "Each view is preprocessed independently first, then merged into one results.npz."
        )
    )
    parser.add_argument("--views-root", required=True, help="Root folder containing numeric view directories.")
    parser.add_argument(
        "--scene-root",
        default=None,
        help="Output scene root. Default: <views_root>_preprocessed beside the input folder.",
    )
    parser.add_argument(
        "--view-ids",
        default="",
        help="Optional comma-separated subset of numeric view ids, e.g. '0,1,5'. Empty means all.",
    )
    parser.add_argument(
        "--video-glob",
        default=DEFAULT_VIDEO_GLOB,
        help=(
            "Glob pattern, relative to each view directory, used to locate the source video. "
            "Default 'auto' tries: rgb/*.mp4, generated_videos/*.mp4, then *.mp4."
        ),
    )
    parser.add_argument("--model-name", default="depth-anything/DA3NESTED-GIANT-LARGE")
    parser.add_argument("--image-ext", default="png")
    parser.add_argument("--max-frames", type=int, default=100)
    parser.add_argument("--max-stride", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    return PreprocessMultiViewConfig(
        views_root=args.views_root,
        scene_root=args.scene_root,
        view_ids=parse_view_ids(args.view_ids),
        video_glob=args.video_glob,
        model_name=args.model_name,
        image_ext=args.image_ext,
        max_frames=args.max_frames,
        max_stride=args.max_stride,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )


def parse_view_ids(raw: str) -> tuple[str, ...]:
    """解析用户指定的视角列表。"""

    if not raw.strip():
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def default_scene_root(views_root: Path) -> Path:
    """生成默认联合 scene_root。"""

    return views_root.parent / f"{views_root.name}_preprocessed"


def build_per_view_scene_root(scene_root: Path, view_id: str) -> Path:
    """每个视角的中间预处理目录。"""

    return scene_root / "per_view" / f"view_{view_id}"


def iter_view_dirs(views_root: Path, selected_view_ids: Sequence[str]) -> list[Path]:
    """按数值顺序枚举视角目录。"""

    all_view_dirs = sorted(
        (path for path in views_root.iterdir() if path.is_dir() and path.name.isdigit()),
        key=lambda path: (int(path.name), path.name),
    )
    if not selected_view_ids:
        return all_view_dirs

    selected = set(selected_view_ids)
    filtered = [path for path in all_view_dirs if path.name in selected]
    missing = sorted(selected.difference(path.name for path in filtered), key=int)
    if missing:
        raise FileNotFoundError(f"Requested view ids not found under '{views_root}': {', '.join(missing)}")
    return filtered


def find_single_video(view_dir: Path, video_glob: str) -> Path:
    """在单个视角目录里定位唯一视频。"""

    normalized_glob = video_glob.strip() or DEFAULT_VIDEO_GLOB

    # `auto` 模式下按常见目录结构依次探测。
    # 一旦某个模式命中唯一文件,就直接采用,避免要求用户记住内部布局差异。
    candidate_globs = AUTO_VIDEO_GLOBS if normalized_glob == DEFAULT_VIDEO_GLOB else (normalized_glob,)
    attempted_globs: list[str] = []

    for candidate_glob in candidate_globs:
        attempted_globs.append(candidate_glob)
        candidates = sorted(path for path in view_dir.glob(candidate_glob) if path.is_file())
        if not candidates:
            continue
        if len(candidates) > 1:
            candidate_text = ", ".join(str(path) for path in candidates)
            raise ValueError(
                f"Expected exactly one video matching '{candidate_glob}' under '{view_dir}', found: {candidate_text}"
            )
        return candidates[0]

    if normalized_glob == DEFAULT_VIDEO_GLOB:
        attempted_text = ", ".join(attempted_globs)
        raise FileNotFoundError(f"No video matched auto patterns [{attempted_text}] under '{view_dir}'.")

    raise FileNotFoundError(f"No video matched '{normalized_glob}' under '{view_dir}'.")


def read_scene_stem(view_dir: Path, video_path: Path) -> str:
    """优先从 manifest 读取 scene_stem。"""

    manifest_path = view_dir / "manifests" / f"{video_path.stem}.json"
    if manifest_path.is_file():
        with manifest_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        scene_stem = payload.get("scene_stem", None)
        if isinstance(scene_stem, str) and scene_stem.strip():
            return scene_stem
    return video_path.stem


def discover_view_inputs(config: PreprocessMultiViewConfig) -> list[MultiViewInput]:
    """发现多视角输入视频。"""

    views_root = Path(config.views_root).resolve()
    if not views_root.is_dir():
        raise NotADirectoryError(f"views_root is not a directory: {views_root}")

    inputs: list[MultiViewInput] = []
    for view_dir in iter_view_dirs(views_root, config.view_ids):
        video_path = find_single_video(view_dir, config.video_glob)
        scene_stem = read_scene_stem(view_dir, video_path)
        inputs.append(
            MultiViewInput(
                view_id=view_dir.name,
                view_dir=str(view_dir.resolve()),
                input_video=str(video_path.resolve()),
                scene_stem=scene_stem,
            )
        )

    if not inputs:
        raise FileNotFoundError(f"No numeric view directories found under '{views_root}'.")

    scene_stems = sorted({item.scene_stem for item in inputs})
    if len(scene_stems) != 1:
        raise ValueError(
            "Joint multiview preprocessing expects all selected views to belong to the same scene, "
            f"but found scene_stem values: {scene_stems}"
        )

    return inputs


def build_preprocess_video_command(
    item: MultiViewInput,
    config: PreprocessMultiViewConfig,
    per_view_scene_root: Path,
) -> list[str]:
    """生成单视角预处理命令。"""

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "preprocess_video.py"),
        "--input_video",
        item.input_video,
        "--scene_root",
        str(per_view_scene_root),
        "--model_name",
        config.model_name,
        "--image_ext",
        config.image_ext,
        "--max_frames",
        str(config.max_frames),
        "--max_stride",
        str(config.max_stride),
    ]
    if config.overwrite:
        cmd.append("--overwrite")
    return cmd


def load_npz_payload(npz_path: Path) -> dict[str, Any]:
    """读取单个 npz 的全部键值。"""

    import numpy as np

    with np.load(npz_path, allow_pickle=False) as payload:
        return {key: payload[key] for key in payload.files}


def merge_npz_payloads(payloads: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """合并多个视角的 DA3 npz。"""

    import numpy as np

    if not payloads:
        raise ValueError("No payloads provided for merging.")

    reference_keys = set(payloads[0].keys())
    for payload in payloads[1:]:
        if set(payload.keys()) != reference_keys:
            raise ValueError("All per-view results.npz files must contain the same keys.")

    frame_counts = [int(payload["conf"].shape[0]) for payload in payloads]
    merged: dict[str, Any] = {}

    for key in sorted(reference_keys):
        arrays = [payload[key] for payload in payloads]
        first = arrays[0]

        # 这类数组的第 0 维是帧维度,需要跨视角拼接。
        if getattr(first, "ndim", 0) >= 1 and all(array.shape[0] == frame_counts[i] for i, array in enumerate(arrays)):
            base_shape = first.shape[1:]
            if not all(array.shape[1:] == base_shape for array in arrays):
                raise ValueError(
                    f"Cannot merge key '{key}' because per-view shapes differ after frame dimension: "
                    f"{[array.shape for array in arrays]}"
                )
            merged[key] = np.concatenate(arrays, axis=0)
            continue

        # 非帧维配置项必须完全一致,否则无法定义单一联合 scene。
        if not all(np.array_equal(array, first) for array in arrays[1:]):
            raise ValueError(f"Key '{key}' differs across views and cannot be merged safely.")
        merged[key] = first

    return merged


def load_frames_dir(scene_root: Path) -> Path:
    """读取单视角预处理产出的 frames_subsampled 路径。"""

    meta_path = scene_root / "preprocess_frames.json"
    if meta_path.is_file():
        with meta_path.open("r", encoding="utf-8") as handle:
            meta = json.load(handle)
        frames_dir = meta.get("frames_dir", None)
        if isinstance(frames_dir, str) and Path(frames_dir).is_dir():
            return Path(frames_dir)

    fallback = scene_root / "frames_subsampled"
    if fallback.is_dir():
        return fallback
    raise FileNotFoundError(f"Could not locate frames_subsampled for per-view scene root: {scene_root}")


def list_frame_images(frames_dir: Path) -> list[Path]:
    """列出单个 frames_dir 中的排序图片。"""

    image_paths: list[Path] = []
    for ext in SUPPORTED_IMAGE_EXTS:
        image_paths.extend(path for path in frames_dir.glob(f"*.{ext}") if path.is_file())
        image_paths.extend(path for path in frames_dir.glob(f"*.{ext.upper()}") if path.is_file())
    image_paths = sorted(set(image_paths))
    if not image_paths:
        raise FileNotFoundError(f"No frame images found under '{frames_dir}'.")
    return image_paths


def merge_multiview_scene(
    scene_root: Path,
    config: PreprocessMultiViewConfig,
    inputs: Sequence[MultiViewInput],
) -> dict[str, Any]:
    """把 per-view 中间结果合并成单一 scene_root。"""

    import numpy as np

    combined_frames_dir = scene_root / "frames_subsampled"
    combined_npz_dir = scene_root / "exports" / "npz"
    combined_npz_dir.mkdir(parents=True, exist_ok=True)
    combined_frames_dir.mkdir(parents=True, exist_ok=True)

    # 无论是不是 overwrite,每次重建联合 frames 目录时都先清空旧文件,
    # 否则视角数量或帧数变化时会残留脏图像,破坏全局索引对齐。
    for old_image in combined_frames_dir.iterdir():
        if old_image.is_file():
            old_image.unlink()

    payloads: list[dict[str, Any]] = []
    view_records: list[dict[str, Any]] = []
    global_frame_cursor = 0

    for item in inputs:
        per_view_scene_root = build_per_view_scene_root(scene_root, item.view_id)
        npz_path = per_view_scene_root / "exports" / "npz" / "results.npz"
        if not npz_path.is_file():
            raise FileNotFoundError(f"Per-view preprocessing did not produce {npz_path}")

        payload = load_npz_payload(npz_path)
        frame_count = int(payload["conf"].shape[0])

        frames_dir = load_frames_dir(per_view_scene_root)
        frame_images = list_frame_images(frames_dir)
        if len(frame_images) != frame_count:
            raise ValueError(
                f"Frame count mismatch for view {item.view_id}: results.npz has {frame_count} frames, "
                f"but {frames_dir} contains {len(frame_images)} images."
            )

        frame_start = global_frame_cursor
        for local_idx, src_image in enumerate(frame_images):
            dst_name = f"{global_frame_cursor:06d}{src_image.suffix.lower()}"
            shutil.copy2(src_image, combined_frames_dir / dst_name)
            global_frame_cursor += 1

        frame_end = global_frame_cursor
        payloads.append(payload)
        view_records.append(
            {
                "view_id": item.view_id,
                "scene_stem": item.scene_stem,
                "input_video": item.input_video,
                "view_dir": item.view_dir,
                "per_view_scene_root": str(per_view_scene_root),
                "frame_count": frame_count,
                "global_frame_start": frame_start,
                "global_frame_end_exclusive": frame_end,
            }
        )

    merged_payload = merge_npz_payloads(payloads)
    np.savez_compressed(combined_npz_dir / "results.npz", **merged_payload)

    preprocess_frames_meta = {
        "frames_dir": str(combined_frames_dir),
        "source": "multiview",
        "views_root": str(Path(config.views_root).resolve()),
        "scene_root": str(scene_root),
        "image_ext": config.image_ext,
        "max_frames": config.max_frames,
        "max_stride": config.max_stride,
        "num_frames_used": int(global_frame_cursor),
        "view_ids": [item.view_id for item in inputs],
        "per_view": view_records,
    }
    with (scene_root / "preprocess_frames.json").open("w", encoding="utf-8") as handle:
        json.dump(preprocess_frames_meta, handle, indent=2, ensure_ascii=False)

    summary = {
        "status": "succeeded",
        "scene_root": str(scene_root),
        "scene_stem": inputs[0].scene_stem,
        "total_frames": int(global_frame_cursor),
        "views": view_records,
        "merged_npz_path": str(combined_npz_dir / "results.npz"),
    }
    with (scene_root / "preprocess_multiview_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)

    return summary


def run_preprocess(config: PreprocessMultiViewConfig) -> dict[str, Any]:
    """执行联合预处理。"""

    inputs = discover_view_inputs(config)
    views_root = Path(config.views_root).resolve()
    scene_root = Path(config.scene_root).resolve() if config.scene_root else default_scene_root(views_root)
    scene_root.mkdir(parents=True, exist_ok=True)

    if config.dry_run:
        records = []
        for item in inputs:
            per_view_scene_root = build_per_view_scene_root(scene_root, item.view_id)
            records.append(
                {
                    "view_id": item.view_id,
                    "scene_stem": item.scene_stem,
                    "input_video": item.input_video,
                    "per_view_scene_root": str(per_view_scene_root),
                    "command": build_preprocess_video_command(item, config, per_view_scene_root),
                }
            )
        summary = {
            "status": "dry_run",
            "scene_root": str(scene_root),
            "scene_stem": inputs[0].scene_stem,
            "config": asdict(config),
            "views": records,
        }
        with (scene_root / "preprocess_multiview_summary.json").open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2, ensure_ascii=False)
        return summary

    for item in inputs:
        per_view_scene_root = build_per_view_scene_root(scene_root, item.view_id)
        per_view_scene_root.parent.mkdir(parents=True, exist_ok=True)
        cmd = build_preprocess_video_command(item, config, per_view_scene_root)
        print(f"[MULTIVIEW-PREPROCESS] view={item.view_id} scene={item.scene_stem}")
        print(" ".join(cmd))
        subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)

    return merge_multiview_scene(scene_root, config, inputs)


def main(argv: Sequence[str] | None = None) -> int:
    config = parse_args(argv)
    summary = run_preprocess(config)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
