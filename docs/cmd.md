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

## 6.1. 设置视频预处理的 stride

这里说的是 Stage 0 视频预处理阶段的采样 stride。
它控制的是 `frames/ -> frames_subsampled/` 这一层。

先说参数名区别:

- `run_multiview_reconstruction.py` 用的是 `--preprocess-max-stride`
- `preprocess_multiview.py` 用的是 `--max-stride`
- `preprocess_video.py` 用的是 `--max_stride`

### 通过联合入口设置

如果你想直接从多视角总入口设置预处理 stride,用这个参数:

```bash
pixi run python run_multiview_reconstruction.py \
  --views-root source/flashvsr_reference_xhc_bai/full_scale2x \
  --scene-root /data/video_to_world/joint_scene_xhc_bai \
  --preprocess-max-frames 100 \
  --preprocess-max-stride 4 \
  --config.mode fast
```

### 通过联合入口设置 只设置 ICP 抽帧 ,跑完整 extensive


```bash
pixi run python run_multiview_reconstruction.py \
  --views-root source/flashvsr_reference_xhc_bai/full_scale2x \
  --scene-root output/video_to_world/joint_scene_xhc_bai \
  --preprocess-max-frames 60 \
  --preprocess-max-stride 2 \
  --config.alignment.num-frames 50 \
  --config.alignment.stride 8 \
  --config.alignment.offset 0
  --config.mode extensive
```

### 只跑联合预处理时设置

如果你只想调 Stage 0,直接运行联合预处理脚本:

```bash
pixi run python preprocess_multiview.py \
  --views-root source/flashvsr_reference_xhc_bai/full_scale2x \
  --scene-root /tmp/video_to_world_joint_scene_preprocess \
  --max-frames 100 \
  --max-stride 4
```

### 单视频预处理时设置

如果你不是多视角入口,而是直接处理一个视频,用单视频参数名:

```bash
pixi run python preprocess_video.py \
  --input_video /path/to/video.mp4 \
  --scene_root /tmp/video_to_world_single_scene \
  --max_frames 100 \
  --max_stride 4
```

### 一个容易误解的点

`max_stride` 不是“强制每隔 N 帧固定取一张”。
它更像“允许的最大 stride 上限”。
实际取帧还会同时受 `max_frames` 影响。

比如视频总帧数不大时,脚本可能会选择 `actual_stride = 1`,然后再因为 `max_frames` 不够而只保留前 `max_frames` 帧。

所以如果你想确认这次运行到底实际用了多少 stride,不要只看你传进去的参数,还要看输出里的:

```text
<scene_root>/preprocess_frames.json
```

重点看这两个字段:

- `actual_stride`
- `num_frames_used`

### 如果你说的是 Stage 1 的 stride

上面这一节是视频预处理的 stride。
如果你想设置的是 Stage 1 配准时从 `results.npz` 里隔帧取样,那是另一套参数:

```bash
pixi run python -m frame_to_model_icp \
  --config.root-path <scene_root> \
  --config.alignment.num-frames 50 \
  --config.alignment.stride 4 \
  --config.alignment.offset 0
```

这和 Stage 0 的 `max_stride` 不是同一个东西。

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
