# 任务计划: 适配 `source/my4` 的 12 视角联合重建入口

## [2026-03-23 23:46:30] [Session ID: codex-20260323-234020] [记录类型]: 新建支线任务并记录现象、假设与执行方向

### 背景
- 用户当前素材位于 `source/my4`。
- 该目录包含 `0..11` 共 12 个数字视角目录。
- 每个视角目录下的视频位于 `generated_videos/generated_video_0.mp4`。
- 当前仓库文档和脚本默认假设旧布局: `<views_root>/<view_id>/rgb/*.mp4`。

### 目标
- 先给出 `source/my4` 现在可直接执行的联合重建命令。
- 再把多视角脚本改到默认兼容新旧两种目录结构。
- 补上测试与文档,避免以后同类目录再次手工传 `--video-glob`。

### 现象
- 已观察到的动态事实:
  - `pixi run python run_multiview_reconstruction.py --views-root source/my4 --dry-run --config.mode fast` 会失败。
  - 首个真实报错是 `No video matched 'rgb/*.mp4' under '.../source/my4/0'`。
  - 当显式传入 `--video-glob 'generated_videos/*.mp4'` 后, dry-run 成功, 且 12 个视角都被正确识别。

### 主假设
- 当前主假设是:
  - 多视角入口并没有依赖旧目录结构本身, 只是把视频发现规则默认写死成了 `rgb/*.mp4`。

### 最强备选解释
- 也可能不只是默认 glob 的问题。
- 还可能存在 `scene_stem`、manifest 读取方式或新目录下附属文件命名,在正式运行阶段触发新的不兼容。

### 最小验证计划
- 先补一个自动发现常见视频路径的实现,只改输入发现层,不动联合重建主流程。
- 再用单元测试覆盖:
  - 旧布局 `rgb/*.mp4`
  - 新布局 `generated_videos/*.mp4`
  - dry-run 命令透传是否仍然正确

### 两个方向
- 方向1: 最佳方案
  - 让脚本默认自动兼容多种常见布局,包括 `rgb/*.mp4` 与 `generated_videos/*.mp4`。
  - 用户继续只传 `--views-root`,最多再传 `--scene-root` 和重建参数。
- 方向2: 先能用方案
  - 代码不改,直接在命令里显式追加 `--video-glob 'generated_videos/*.mp4'`。
  - 成本最低,但以后每次都要记住这个参数。

### 阶段
- [x] 阶段1: 读取历史上下文并核对 `source/my4` 目录结构
- [x] 阶段2: 做最小动态证伪,确认失败点是否仅在视频发现规则
- [x] 阶段3: 修改脚本默认发现逻辑并补测试
- [x] 阶段4: 运行验证并整理最终运行命令

### 状态
**目前已完成** - 脚本已默认兼容 `rgb/*.mp4` 与 `generated_videos/*.mp4`,并完成单元测试、lint 与真实 `source/my4` dry-run 验证。

## [2026-03-23 23:55:20] [Session ID: codex-20260323-234020] [记录类型]: 修复与验证完成

### 已完成改动
- 在 `preprocess_multiview.py` 中新增 `auto` 视频发现模式。
- `auto` 模式按顺序探测:
  - `rgb/*.mp4`
  - `generated_videos/*.mp4`
  - `*.mp4`
- `run_multiview_reconstruction.py` 同步把默认 `--video-glob` 改为 `auto`。
- 新增单元测试覆盖 VerseCrafter 风格 `generated_videos/*.mp4` 目录。
- README 已补充 `source/my4` 示例和 auto 发现说明。

### 动态验证
- `pixi run python -m unittest tests/test_run_multiview_reconstruction.py` 通过。
- `pixi run ruff check preprocess_multiview.py run_multiview_reconstruction.py tests/test_run_multiview_reconstruction.py` 通过。
- `pixi run python run_multiview_reconstruction.py --views-root source/my4 --dry-run --config.mode fast` 通过。

### 最终结论
- 当前 `source/my4` 不再需要额外传 `--video-glob 'generated_videos/*.mp4'` 也能被联合入口识别。
- 如果用户要跑完整 extensive,只需要像旧命令一样换成新的 `views-root` 和目标 `scene-root` 即可。
