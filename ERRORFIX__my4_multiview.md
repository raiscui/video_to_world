## [2026-03-23 23:56:55] [Session ID: codex-20260323-234020] 问题: `source/my4` 的 VerseCrafter 多视角目录无法被联合入口默认识别

### 现象
- 运行:
  - `pixi run python run_multiview_reconstruction.py --views-root source/my4 --dry-run --config.mode fast`
- 首个报错:
  - `FileNotFoundError: No video matched 'rgb/*.mp4' under '.../source/my4/0'`

### 原因
- `preprocess_multiview.py` 之前把每个视角的视频路径默认固定为 `rgb/*.mp4`。
- 新素材 `source/my4` 的真实视频位于 `generated_videos/generated_video_0.mp4`。
- 联合入口本身支持数字视角目录和 12 个镜头,真正不兼容的是输入发现规则。

### 修复
- 新增 `DEFAULT_VIDEO_GLOB = "auto"`。
- `auto` 依次尝试:
  - `rgb/*.mp4`
  - `generated_videos/*.mp4`
  - `*.mp4`
- `run_multiview_reconstruction.py` 与 `preprocess_multiview.py` 的 CLI 默认值同步改为 `auto`。
- 新增针对 `generated_videos/*.mp4` 目录的单元测试。

### 验证
- `pixi run python -m unittest tests/test_run_multiview_reconstruction.py`
- `pixi run ruff check preprocess_multiview.py run_multiview_reconstruction.py tests/test_run_multiview_reconstruction.py`
- `pixi run python run_multiview_reconstruction.py --views-root source/my4 --dry-run --config.mode fast`

### 结果
- 默认命令已能识别 `source/my4` 的 12 个视角。
- 如需完整跑 extensive,无需再额外记 `--video-glob 'generated_videos/*.mp4'`。
