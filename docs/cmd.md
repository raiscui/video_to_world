# 多视角联合重建命令手册

这份文档对应的是“同一个场景,多个视角视频联合进入一套重建”。
不是把 `0..5` 分别跑成 6 个独立结果。

## 1. 先准备环境

第一次进入仓库时,先装基础环境和第三方依赖:

```bash
pixi install
pixi run setup
```

后面的命令都建议直接用 `pixi run python ...` 执行。

## 2. 输入目录长什么样

当前联合入口面向下面这种目录:

```text
source/flashvsr_reference_xhc_bai/full_scale2x/
  0/rgb/xhc-bai_97e474c6.mp4
  1/rgb/xhc-bai_97e474c6.mp4
  2/rgb/xhc-bai_97e474c6.mp4
  3/rgb/xhc-bai_97e474c6.mp4
  4/rgb/xhc-bai_97e474c6.mp4
  5/rgb/xhc-bai_97e474c6.mp4
```

每个数字目录代表一个视角。
这些视角应当属于同一个 `scene_stem`。

## 3. 先做 dry-run

先确认入口识别到的视角和命令是否正确:

```bash
pixi run python run_multiview_reconstruction.py \
  --views-root source/flashvsr_reference_xhc_bai/full_scale2x \
  --scene-root /tmp/video_to_world_joint_scene \
  --dry-run \
  --config.mode fast
```

这条命令不会真的开始重建。
它会输出两条主命令:

1. 一条联合 `preprocess_multiview.py`
2. 一条共享 `scene_root` 的 `run_reconstruction.py`

同时会写出摘要文件:

```text
/tmp/video_to_world_joint_scene/multiview_reconstruction_summary.json
```

## 4. 真正开始联合重建

确认 dry-run 没问题后,去掉 `--dry-run`:

  pixi run python run_multiview_reconstruction.py \
    --views-root source/my4 \
    --scene-root /data/video_to_world/joint_scene_my4 \
    --config.mode extensive


```bash
pixi run python run_multiview_reconstruction.py \
  --views-root source/flashvsr_reference_xhc_bai/full_scale2x \
  --scene-root /data/video_to_world/joint_scene_xhc_bai \
  --config.mode fast
```

如果你想跑更完整的流程,可以把 `fast` 改成 `extensive`:

```bash
pixi run python run_multiview_reconstruction.py \
  --views-root source/flashvsr_reference_xhc_bai/full_scale2x \
  --scene-root /data/video_to_world/joint_scene_xhc_bai \
  --config.mode extensive
```

## 5. 只跑部分视角

如果你只想先验证部分视角,可以显式指定:

```bash
pixi run python run_multiview_reconstruction.py \
  --views-root source/flashvsr_reference_xhc_bai/full_scale2x \
  --view-ids 0,1,2 \
  --scene-root /tmp/video_to_world_joint_scene_012 \
  --dry-run \
  --config.mode fast
```

## 6. 单独看联合预处理

如果你只想看联合 Stage 0,可以直接运行:

```bash
pixi run python preprocess_multiview.py \
  --views-root source/flashvsr_reference_xhc_bai/full_scale2x \
  --scene-root /tmp/video_to_world_joint_scene_preprocess \
  --dry-run
```

真实执行时去掉 `--dry-run`。

## 7. 结果会写到哪里

联合场景的核心输出会在同一个 `scene_root` 下:

```text
<scene_root>/
  per_view/view_<id>/...                  # 每个视角各自的中间预处理结果
  exports/npz/results.npz                 # 合并后的单一 DA3 输入
  frames_subsampled/                      # 合并后的全局帧序列
  preprocess_frames.json
  preprocess_multiview_summary.json
  multiview_reconstruction_summary.json
```

如果后续 Stage 1/2/3 正常跑完,对应的对齐、优化和 GS 输出也都会继续写在这个 `scene_root` 下面。
