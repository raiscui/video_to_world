#!/usr/bin/env python3
"""
同一场景多视角视频的联合重建入口。

流程:
1. 先调用 `preprocess_multiview.py`,把多个视频整理成同一个 scene_root
2. 再调用现有 `run_reconstruction.py --config.root-path <scene_root>`
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from preprocess_multiview import (
    DEFAULT_VIDEO_GLOB,
    PreprocessMultiViewConfig,
    default_scene_root,
    discover_view_inputs,
    parse_view_ids,
)


PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class JointMultiViewConfig:
    """联合多视角重建配置。"""

    views_root: str
    scene_root: str | None = None
    view_ids: tuple[str, ...] = ()
    video_glob: str = DEFAULT_VIDEO_GLOB
    preprocess_overwrite: bool = False
    preprocess_model_name: str = "depth-anything/DA3NESTED-GIANT-LARGE"
    preprocess_image_ext: str = "png"
    preprocess_max_frames: int = 100
    preprocess_max_stride: int = 8
    dry_run: bool = False
    pipeline_args: tuple[str, ...] = ()


def parse_args(argv: Sequence[str] | None = None) -> JointMultiViewConfig:
    parser = argparse.ArgumentParser(
        description=(
            "Jointly reconstruct one scene from multiple view videos.\n"
            "Expected layout example:\n"
            "  <views_root>/0/rgb/foo.mp4\n"
            "  <views_root>/1/rgb/foo.mp4\n"
            "  <views_root>/2/generated_videos/generated_video_0.mp4\n"
            "  ...\n"
            "Extra arguments are forwarded to run_reconstruction.py."
        )
    )
    parser.add_argument("--views-root", required=True)
    parser.add_argument(
        "--scene-root",
        default=None,
        help="Combined scene root. Default: <views_root>_preprocessed beside the input folder.",
    )
    parser.add_argument("--view-ids", default="", help="Optional comma-separated subset, e.g. '0,1,4'.")
    parser.add_argument(
        "--video-glob",
        default=DEFAULT_VIDEO_GLOB,
        help=(
            "Glob pattern relative to each view directory. "
            "Default 'auto' tries rgb/*.mp4, generated_videos/*.mp4, then *.mp4."
        ),
    )
    parser.add_argument("--preprocess-overwrite", action="store_true")
    parser.add_argument("--preprocess-model-name", default="depth-anything/DA3NESTED-GIANT-LARGE")
    parser.add_argument("--preprocess-image-ext", default="png")
    parser.add_argument("--preprocess-max-frames", type=int, default=100)
    parser.add_argument("--preprocess-max-stride", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")

    args, pipeline_args = parser.parse_known_args(argv)
    if pipeline_args and pipeline_args[0] == "--":
        pipeline_args = pipeline_args[1:]

    return JointMultiViewConfig(
        views_root=args.views_root,
        scene_root=args.scene_root,
        view_ids=parse_view_ids(args.view_ids),
        video_glob=args.video_glob,
        preprocess_overwrite=args.preprocess_overwrite,
        preprocess_model_name=args.preprocess_model_name,
        preprocess_image_ext=args.preprocess_image_ext,
        preprocess_max_frames=args.preprocess_max_frames,
        preprocess_max_stride=args.preprocess_max_stride,
        dry_run=args.dry_run,
        pipeline_args=tuple(pipeline_args),
    )


def validate_forwarded_args(pipeline_args: Sequence[str]) -> None:
    """拒绝与联合入口职责冲突的单视频参数。"""

    forbidden_prefixes = (
        "--config.input-video",
        "--config.frames-dir",
        "--config.scene-root",
        "--config.root-path",
    )
    for arg in pipeline_args:
        if any(arg.startswith(prefix) for prefix in forbidden_prefixes):
            raise ValueError(
                "Do not pass single-video input/output flags through the joint multiview entrypoint. "
                f"Conflicting argument: {arg}"
            )


def build_preprocess_command(config: JointMultiViewConfig, scene_root: Path) -> list[str]:
    """生成联合 Stage 0 命令。"""

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "preprocess_multiview.py"),
        "--views-root",
        str(Path(config.views_root).resolve()),
        "--scene-root",
        str(scene_root),
        "--video-glob",
        config.video_glob,
        "--model-name",
        config.preprocess_model_name,
        "--image-ext",
        config.preprocess_image_ext,
        "--max-frames",
        str(config.preprocess_max_frames),
        "--max-stride",
        str(config.preprocess_max_stride),
    ]
    if config.view_ids:
        cmd.extend(["--view-ids", ",".join(config.view_ids)])
    if config.preprocess_overwrite:
        cmd.append("--overwrite")
    if config.dry_run:
        cmd.append("--dry-run")
    return cmd


def build_reconstruction_command(config: JointMultiViewConfig, scene_root: Path) -> list[str]:
    """生成联合 Stage 1/2/3 命令。"""

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "run_reconstruction.py"),
        "--config.root-path",
        str(scene_root),
    ]
    cmd.extend(config.pipeline_args)
    if config.dry_run and "--config.dry-run" not in config.pipeline_args:
        cmd.append("--config.dry-run")
    return cmd


def summary_path_for(scene_root: Path) -> Path:
    """联合重建摘要 JSON 路径。"""

    return scene_root / "multiview_reconstruction_summary.json"


def run_joint_pipeline(config: JointMultiViewConfig) -> bool:
    """执行联合多视角重建。"""

    validate_forwarded_args(config.pipeline_args)

    preprocess_probe_config = PreprocessMultiViewConfig(
        views_root=config.views_root,
        scene_root=config.scene_root,
        view_ids=config.view_ids,
        video_glob=config.video_glob,
    )
    discovered = discover_view_inputs(preprocess_probe_config)

    views_root = Path(config.views_root).resolve()
    scene_root = Path(config.scene_root).resolve() if config.scene_root else default_scene_root(views_root)
    scene_root.mkdir(parents=True, exist_ok=True)

    preprocess_cmd = build_preprocess_command(config, scene_root)
    reconstruct_cmd = build_reconstruction_command(config, scene_root)

    summary = {
        "status": "dry_run" if config.dry_run else "running",
        "scene_root": str(scene_root),
        "scene_stem": discovered[0].scene_stem,
        "config": {
            **asdict(config),
            "view_ids": list(config.view_ids),
            "pipeline_args": list(config.pipeline_args),
        },
        "views": [asdict(item) for item in discovered],
        "commands": {
            "preprocess": preprocess_cmd,
            "reconstruct": reconstruct_cmd,
        },
    }

    if config.dry_run:
        with summary_path_for(scene_root).open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2, ensure_ascii=False)
        print(shlex.join(preprocess_cmd))
        print(shlex.join(reconstruct_cmd))
        return True

    print("=" * 80)
    print("[JOINT-MULTIVIEW] Stage 0: preprocess_multiview.py")
    print(shlex.join(preprocess_cmd))
    print("=" * 80)
    subprocess.run(preprocess_cmd, check=True, cwd=PROJECT_ROOT)

    print("=" * 80)
    print("[JOINT-MULTIVIEW] Stage 1/2/3: run_reconstruction.py")
    print(shlex.join(reconstruct_cmd))
    print("=" * 80)
    subprocess.run(reconstruct_cmd, check=True, cwd=PROJECT_ROOT)

    summary["status"] = "succeeded"
    with summary_path_for(scene_root).open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)
    return True


def main(argv: Sequence[str] | None = None) -> int:
    config = parse_args(argv)
    return 0 if run_joint_pipeline(config) else 1


if __name__ == "__main__":
    raise SystemExit(main())
