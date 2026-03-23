## [2026-03-23 23:56:25] [Session ID: codex-20260323-234020] 任务名称: 适配 `source/my4` 的 12 视角联合重建入口

### 任务内容
- 核对 `source/my4` 的真实目录结构与旧多视角入口的差异。
- 修改多视角脚本,让其默认兼容 VerseCrafter 风格的 `generated_videos/*.mp4` 布局。
- 给出 `source/my4` 现在可直接执行的运行命令。

### 完成过程
- 先静态阅读 `run_multiview_reconstruction.py` 与 `preprocess_multiview.py`,确认真正写死的是 `video_glob='rgb/*.mp4'`,而不是视角数量或数字目录扫描逻辑。
- 再用真实目录做 dry-run,拿到首个失败证据 `No video matched 'rgb/*.mp4' under '.../source/my4/0'`。
- 然后用 `--video-glob 'generated_videos/*.mp4'` 做最小证伪,确认 12 个视角都能被现有联合入口识别。
- 最后把修复收敛到输入发现层,新增 `auto` 模式,同步补测试与 README,并用真实 `source/my4` dry-run、单元测试、ruff 三重验证收尾。

### 总结感悟
- 这次问题不在“12 个镜头太多”,而在“旧脚本把输入布局写死了”。
- 对长流水线入口,先做 dry-run 找首个失败点,比直接起正式重建更省时间也更不容易误判。
