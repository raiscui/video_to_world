# 任务计划: 启动 `source/flashvsr_reference_xhc_bai` 的 extensive 多视角正式运行

## [2026-03-22 04:39:30] [Session ID: e7d33bb8-22af-4207-a9b3-224a0f3a3b4e] [记录类型]: 新任务续档初始化

### 背景承接
- 旧的 `task_plan.md` 与 `notes.md` 已超过 1000 行,本轮按项目规则续档。
- 已完成最小持续学习检索,并回读了默认六文件与相关历史文件。
- 已确认 `source/flashvsr_reference_xhc_bai/full_scale2x` 是多视角输入,应走 `run_multiview_reconstruction.py`。
- 用户要求使用 `extensive` 模式,输出目录固定到当前项目下的 `output/flashvsr_reference_xhc_bai`。

### 目标
- 正式启动 `source/flashvsr_reference_xhc_bai` 的 `extensive` 多视角重建。
- 将日志、首批输出、进程状态和首个真实阻塞记录清楚。
- 如果运行成功进入主流程,继续保留可追踪的日志与会话信息。

### 现象
- 当前 `output/` 目录为空,目标输出目录尚未存在可复用产物。
- 当前 GPU 空闲,仅有约 `396 MiB` 基础占用,没有重建相关 compute app。
- 之前已验证多视角入口会把额外参数透传给 `run_reconstruction.py`,因此 `--config.mode extensive` 应可生效。

### 主假设
- 主假设: 直接执行下列命令即可进入正式 extensive 流程:
  - `pixi run python run_multiview_reconstruction.py --views-root source/flashvsr_reference_xhc_bai/full_scale2x --scene-root output/flashvsr_reference_xhc_bai --config.mode extensive`

### 最强备选解释
- 备选解释: 运行可能会卡在外部模型下载、Stage 1 显存峰值、或某个 extensive 特有阶段,需要根据首批日志继续收敛。

### 阶段
- [x] 阶段1: 回读上下文并完成续档
- [ ] 阶段2: 记录启动参数与运行环境
- [ ] 阶段3: 正式启动 extensive 运行
- [ ] 阶段4: 验证首批日志、落盘和阻塞点
- [ ] 阶段5: 更新工作记录并向用户汇报当前进度

### 状态
**目前在阶段2** - 正在写入正式启动记录,马上启动 extensive 会话并挂日志。

## [2026-03-22 04:40:04] [Session ID: e7d33bb8-22af-4207-a9b3-224a0f3a3b4e] [记录类型]: 记录正式启动参数与日志路径

### 本轮启动配置
- 入口命令:
  - `pixi run python run_multiview_reconstruction.py --views-root source/flashvsr_reference_xhc_bai/full_scale2x --scene-root output/flashvsr_reference_xhc_bai --config.mode extensive`
- 日志文件:
  - `/tmp/video_to_world_flashvsr_reference_xhc_bai_extensive_20260322_044004.log`
- GPU 采样日志:
  - `GPU_/tmp/video_to_world_flashvsr_reference_xhc_bai_extensive_20260322_044004.log`
- 网络环境:
  - 启用 `http_proxy` / `https_proxy` 到 `127.0.0.1:7890`
  - 启用 `all_proxy=socks5://127.0.0.1:7890`
  - 启用 `HF_ENDPOINT=https://hf-mirror.com`

### 运行前判断
- 目标输出目录当前无旧内容,可以直接开始。
- 当前没有重建相关残留进程占用 GPU。
- extensive 是长任务,因此本轮会保留前台会话并持续观察首批日志。

### 状态
**目前在阶段3** - 已写入启动参数,下一步正式启动 extensive 会话。

## [2026-03-22 04:42:36] [Session ID: e7d33bb8-22af-4207-a9b3-224a0f3a3b4e] [记录类型]: extensive 会话已成功启动并稳定推进到多视角预处理中段

### 已观察到的现象
- 正式会话已启动,主 PTY 会话 ID 为 `90694`。
- 日志文件已落盘:
  - `/tmp/video_to_world_flashvsr_reference_xhc_bai_extensive_20260322_044004.log`
- GPU 采样日志已落盘:
  - `/tmp/video_to_world_flashvsr_reference_xhc_bai_extensive_gpu_20260322_044004.log`
- 主日志已明确显示:
  - `Stage 0: preprocess_multiview.py`
  - `view=0` 到 `view=4` 已依次推进
- 至少以下 per-view 结果已明确完成:
  - `view_0/exports/npz/results.npz`
  - `view_1/exports/npz/results.npz`
  - `view_2/exports/npz/results.npz`
  - `view_3/exports/npz/results.npz`
- 当前尚未观察到 `Traceback`、`[ERROR]` 或下载层卡死。

### 结论更新
- 上一条主假设目前被动态证据支持:
  - 命令、代理和 HF mirror 组合可以把 extensive 会话稳定拉起。
- 当前最强备选解释仍保留:
  - 后续仍可能在 Stage 0 合并、Stage 1、ICP、global optimization 或 GS 阶段出现新的真实阻塞。

### 阶段
- [x] 阶段1: 回读上下文并完成续档
- [x] 阶段2: 记录启动参数与运行环境
- [x] 阶段3: 正式启动 extensive 运行
- [ ] 阶段4: 验证首批日志、落盘和阻塞点
- [ ] 阶段5: 更新工作记录并向用户汇报当前进度

### 状态
**目前在阶段4** - extensive 会话已稳定运行,正在继续观察是否完成 Stage 0 并进入后续主流程。

## [2026-03-22 04:44:54] [Session ID: e7d33bb8-22af-4207-a9b3-224a0f3a3b4e] [记录类型]: Stage 0 已完成,Stage 1 已进入 GPU 实算

### 动态证据
- `preprocess_multiview.py` 已对 `view_0..view_5` 全部完成 DA3 preprocessing。
- 联合预处理总结 JSON 已打印:
  - `total_frames: 600`
  - `merged_npz_path: /workspace/video_to_world/output/flashvsr_reference_xhc_bai/exports/npz/results.npz`
- 入口已继续进入:
  - `run_reconstruction.py --config.root-path /workspace/video_to_world/output/flashvsr_reference_xhc_bai --config.mode extensive`
  - `Stage 1: Iterative Alignment`
  - `python -m frame_to_model_icp --config.root-path ... --config.icp-early-stopping-min-delta 5e-06`
- Stage 1 已完成 `Back-projecting frames: 600/600`。
- GPU 采样日志显示 Stage 1 期间出现真实 compute app,显存峰值已观测到约 `22026 MiB`,GPU 利用率达到 `100%`,目前未见 OOM。

### 结论
- 阶段4 已完成:
  - extensive 不仅成功启动,还已跨过联合预处理,并进入后续主流程的真实 GPU 计算。
- 当前仍未完成整条 extensive 管线,但已经排除了“启动即失败”“Stage 0 卡死”“刚进 Stage 1 就 OOM”这几类早期风险。

### 阶段
- [x] 阶段1: 回读上下文并完成续档
- [x] 阶段2: 记录启动参数与运行环境
- [x] 阶段3: 正式启动 extensive 运行
- [x] 阶段4: 验证首批日志、落盘和阻塞点
- [ ] 阶段5: 更新工作记录并向用户汇报当前进度

### 状态
**目前在阶段5** - extensive 长跑仍在继续,我已完成首批稳定性验收,正在整理阶段性汇报。

## [2026-03-22 10:29:44] [Session ID: e7d33bb8-22af-4207-a9b3-224a0f3a3b4e] [记录类型]: 检查 extensive 长跑是否已经完成

### 检查动机
- 用户刚刚询问“完成了吗”。
- 该问题属于实时状态判断,不能依赖上一轮的中途观察结果,必须重新核对当前进程、日志和落盘情况。

### 最小验证计划
- 检查主 PTY 会话 `90694` 是否仍在输出。
- 检查相关进程是否还存活。
- 检查主日志尾部是否出现成功收尾或错误收尾标记。
- 检查输出目录是否出现后续阶段产物。

### 状态
**目前在阶段5** - 正在重新核对 extensive 长跑的当前完成状态。

## [2026-03-22 10:30:30] [Session ID: e7d33bb8-22af-4207-a9b3-224a0f3a3b4e] [记录类型]: extensive 长跑当前未完成,已在 Stage 1 因 RoMa CUDA OOM 退出

### 新动态证据
- 主 PTY 会话 `90694` 已结束,退出码为 `1`。
- 当前已无 `run_multiview_reconstruction.py` / `run_reconstruction.py` / `frame_to_model_icp.py` 相关存活进程。
- 主日志尾部出现明确错误栈:
  - `torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 200.00 MiB`
  - 失败位置在 `third_party/RoMaV2/src/romav2/refiner.py`,调用链由 `models/roma_matcher.py -> frame_to_model_icp.py` 触发。
- 失败时日志进度大约在:
  - `Frames: 16%|█▋| 8/49`
  - 已完成 Stage 0 和 Stage 1 前半段,但未完成整个 extensive 流程。

### 结论更新
- 上一条“extensive 已稳定进入主流程”的判断只对当时的早期阶段成立。
- 新证据已经推翻“本次 extensive 长跑目前仍在继续”的状态判断。
- 当前真实结论是:
  - 这次 `output/flashvsr_reference_xhc_bai` 的 extensive 正式运行 **没有完成**。
  - 它在 Stage 1 的 RoMa matching / refiner 阶段因 CUDA OOM 失败退出。

### 下一步
- [ ] 提炼这次 OOM 的静态与动态证据。
- [ ] 判断是 RoMa 生命周期问题、匹配缓存增长问题,还是 extensive 特定参数导致的峰值过高。
- [ ] 给出可执行的下一轮处置方案。

### 状态
**目前仍在阶段5** - 已完成状态核对,当前转入失败原因归档与下一步方案收敛。

## [2026-03-22 10:30:59] [Session ID: e7d33bb8-22af-4207-a9b3-224a0f3a3b4e] [记录类型]: 转入 Stage 1 RoMa OOM 的最小证伪排查

### 排查目标
- 先区分这次 OOM 更像单次前向峰值,还是跨帧显存累积。
- 优先从 `frame_to_model_icp.py`、`models/roma_matcher.py` 与日志中的初始化痕迹入手。

### 最小验证计划
- 检查 RoMa matcher 的初始化位置与生命周期。
- 检查每帧匹配后是否存在明显的大对象保留。
- 检查日志里是否有重复初始化或重复缓存增长的迹象。

### 状态
**目前仍在阶段5** - 正在做 Stage 1 RoMa OOM 的静态证据收集。

## [2026-03-22 10:31:41] [Session ID: e7d33bb8-22af-4207-a9b3-224a0f3a3b4e] [记录类型]: 最小静态排查已初步缩小 OOM 怀疑范围

### 已观察到的静态证据
- `frame_to_model_icp.py` 在每帧 RoMa 匹配后都有:
  - `del roma_matcher`
  - `torch.cuda.empty_cache()`
  - `roma_matcher = _create_roma_matcher()`
- `models/roma_matcher.py::compute_roma_matches_for_frame()` 内部还会在单帧内每 4 个新 pair 后重建一次 matcher。
- 主日志里也确实出现了每帧重复的:
  - `Initializing RoMa matcher`
  - `RoMa matcher initialized successfully`

### 当前判断更新
- “同一个 matcher 跨帧一直复用导致简单泄漏” 这个解释,目前被新证据削弱了。
- 当前更值得优先怀疑的是:
  - 随着 `model_pts` 增长,Stage 1 本体占用逐步抬高,再叠加单次 RoMaV2 refiner 前向峰值,最终在第 8 帧附近触顶 OOM。
- 这还是候选假设,还不是最终根因结论。

### 状态
**目前仍在阶段5** - 已缩小一层怀疑范围,下一步更适合围绕 Stage 1 中增长性状态做证伪。

## [2026-03-22 10:35:45] [Session ID: e7d33bb8-22af-4207-a9b3-224a0f3a3b4e] [记录类型]: 启动 Stage 1 单阶段动态验证

### 验证目的
- 不重跑整条 multiview extensive。
- 直接基于已完成的 Stage 0 产物重跑 `frame_to_model_icp`,确认修复后是否还能在 `frame 8` 左右再次 OOM。

### 验证命令
- `pixi run python -m frame_to_model_icp --config.root-path output/flashvsr_reference_xhc_bai --config.icp-early-stopping-min-delta 5e-06 --config.out-suffix _oomfix_probe_20260322_103545`
- 日志:
  - `/tmp/video_to_world_flashvsr_reference_xhc_bai_stage1_probe_oomfix_probe_20260322_103545.log`

### 状态
**目前仍在阶段5** - 正在做修复后的最小动态复现验证。
## [${ts}] [Session ID: 2e546d88-242b-47b8-a6a3-eff09359ded0] [记录类型]: 当前会话接手并继续完整 extensive 正式验证

### 承接判断
- 已回读当前六文件和上一轮关键结论。
- 上一轮已经完成代码修复,并用 Stage 1 单阶段 probe 动态证明: 修复后已越过原来 `frame 8` 左右的 OOM 点。
- 但完整命令 `run_multiview_reconstruction.py --config.mode extensive` 还没有在修复后重新正式跑完。

### 当前会话的最小可证伪计划
- 先核对当前是否存在残留的 pipeline 进程、旧 PTY 或 GPU 占用。
- 若没有,就重新启动 `source/flashvsr_reference_xhc_bai` 的完整 extensive 正式运行。
- 继续观察 Stage 1 是否完整通过,以及后续是否进入 global optimization、inverse deformation、train_gs、eval_gs。

### 当前主假设
- 主假设: 现在的 RoMa matcher 生命周期修复,足以让本次 extensive 至少穿过上一轮的 Stage 1 OOM 阻塞点。

### 最强备选解释
- 备选解释: 即使旧 OOM 点已被解除,也可能在 Stage 1 更后段或后续 extensive 特有阶段出现新的显存峰值或其他真实错误。

### 状态
**目前仍在阶段5** - 当前会话已完成接手登记,下一步先核对现场状态并立即启动完整 extensive 正式长跑。

## [2026-03-22 10:40:00] [Session ID: 2e546d88-242b-47b8-a6a3-eff09359ded0] [记录类型]: 更正上一条接手记录的时间戳写入错误

### 现象
- 上一条追加记录的标题被误写成了 `## [${ts}] ...`。
- 原因是为了满足“正文含反引号时使用单引号 heredoc”这条规则,导致 shell 变量没有展开。

### 纠正方式
- 保留错误记录原样不删,避免破坏 append-only 上下文。
- 从本条开始以正确时间戳继续推进当前会话记录。

### 状态
**目前仍在阶段5** - 接手记录已纠正,下一步开始核对现场进程、GPU 占用和当前输出状态。

## [2026-03-22 10:40:38] [Session ID: 2e546d88-242b-47b8-a6a3-eff09359ded0] [记录类型]: 现场核对完成,当前可以安全发起新一轮正式运行

### 已验证事实
- 当前没有存活的 `run_multiview_reconstruction.py` / `run_reconstruction.py` / `frame_to_model_icp.py` / `train_gs.py` / `eval_gs.py` 进程。
- 当前 GPU 只有桌面进程基础占用,显存约 `396 MiB / 49140 MiB`,不存在上轮残留计算负载。
- 目标目录 `output/flashvsr_reference_xhc_bai` 已保留 Stage 0 产物,并保留了上轮失败的 `frame_to_model_icp_50_2_offset0` 与本轮 probe 的 `frame_to_model_icp_50_2_offset0_oomfix_probe_20260322_103545`。
- probe 日志尾部已清楚显示: 修复后至少稳定推进到 `frame 11`,明显越过了原来 `frame 8` 左右的 OOM 点。

### 当前判断
- 现场状态允许重新发起正式长跑。
- 但正式发起前还需要确认主入口对已有输出目录的处理策略,避免旧失败产物污染本轮验证。

### 状态
**目前仍在阶段5** - 现场核对完成,下一步检查主入口对已有输出目录的行为,然后立即启动新的 extensive 正式运行。

## [2026-03-22 10:41:55] [Session ID: 2e546d88-242b-47b8-a6a3-eff09359ded0] [记录类型]: 确认正式续跑必须规避旧 probe 目录干扰

### 新静态证据
- `frame_to_model_icp.py` 默认输出目录是固定命名,不会自动清空旧目录。
- `run_reconstruction.py` 在 Stage 1 完成后,只是按前缀 `frame_to_model_icp_` 搜索并选择字典序最后一个目录。
- 当前输出根目录里已经存在 probe 目录 `frame_to_model_icp_50_2_offset0_oomfix_probe_20260322_103545`。

### 已验证结论
- 如果直接用默认 Stage 1 目录名重跑,Stage 2/3 可能接错到 probe 目录,这会污染本轮正式验证。
- 本轮正式续跑应改为直接调用 `run_reconstruction.py --config.root-path output/flashvsr_reference_xhc_bai --config.mode extensive`,并显式加一个新的 `--config.stage1.out-suffix`。
- 为了确保 `_find_subdir()` 选中的一定是这次新目录,后缀应以 `z` 开头,让它按字典序排在 probe 目录之后。

### 状态
**目前仍在阶段5** - 已明确正式续跑命令策略,下一步启动带唯一 `out_suffix` 的完整 extensive 续跑。

## [2026-03-22 10:42:27] [Session ID: 2e546d88-242b-47b8-a6a3-eff09359ded0] [记录类型]: 已启动修复后的 extensive 正式续跑会话

### 启动信息
- 主 PTY 会话 ID: `35731`
- 主日志:
  - `/tmp/video_to_world_flashvsr_reference_xhc_bai_extensive_resume_20260322_104213.log`
- GPU 日志:
  - `/tmp/video_to_world_flashvsr_reference_xhc_bai_extensive_resume_gpu_20260322_104213.log`
- 实际执行命令:
  - `pixi run python run_reconstruction.py --config.root-path output/flashvsr_reference_xhc_bai --config.mode extensive --config.stage1.out-suffix _zzextensive_rerun_20260322_104213`

### 选择理由
- 直接复用已完成的 Stage 0 产物,避免重复预处理。
- 通过新的 `out_suffix` 规避旧 probe 目录对 `_find_subdir()` 的干扰。

### 状态
**目前仍在阶段5** - 会话已启动,正在观察早期日志,重点确认新的 Stage 1 目录被正确创建并进入真实 GPU 计算。

## [2026-03-22 10:44:18] [Session ID: 2e546d88-242b-47b8-a6a3-eff09359ded0] [记录类型]: 正式 extensive 长跑已穿过旧 OOM 断点并继续推进

### 新动态证据
- 当前正式会话 `35731` 已稳定推进到 `frame 12`。
- 日志已明确显示:
  - `Frames: 22%|██▏| 11/49 ... model_pts=811221`
  - 随后继续进入 `Rigid ICP f00012` 和 `Non-rigid ICP f00012`。
- 上一轮失败发生在大约 `frame 8/49`,而这次已经明显越过该位置,并且没有再次出现 `torch.OutOfMemoryError`。

### 已验证结论
- RoMa matcher 生命周期修复不只是对单阶段 probe 有效。
- 它已经在正式 `run_reconstruction.py --config.mode extensive` 长跑里成功消除了原来的早期 Stage 1 OOM 断点。

### 状态
**目前仍在阶段5** - 已完成对旧 OOM 点的正式证伪,接下来继续等待 Stage 1 是否完整结束并进入 Stage 2。

## [2026-03-22 10:45:08] [Session ID: 2e546d88-242b-47b8-a6a3-eff09359ded0] [记录类型]: 正式长跑在更后段再次出现新的 RoMa OOM,分析阶段切换

### 新现象
- 正式会话 `35731` 已经越过旧的 `frame 8` OOM 点,但最终仍在 `frame 13` 左右退出。
- 新报错不再落在上一轮的 refiner 分支,而是落在 `third_party/RoMaV2/src/romav2/romav2.py::kde()` 内部的 `torch.cdist(x, x)`。
- 本次报错为:
  - `torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 764.00 MiB`
- 失败前日志位置大约是:
  - `Frames: 27%|██▋| 13/49`
  - 随后进入 `Rigid ICP f00014` 后再次开始 `RoMa matching...`

### 口径回滚
- 上一条“正式 extensive 长跑已消除原来的早期 Stage 1 OOM 断点”仍然成立。
- 但它不能被扩大解释成“Stage 1 已整体稳定”。
- 新证据已经明确推翻“当前 Stage 1 足以完整跑完”的更强说法。

### 下一步
- [ ] 收敛这次新的 OOM 具体发生在 RoMa 采样链路的哪一步。
- [ ] 判断最稳妥的修法是: 限制 sample 峰值 / 改 chunked KDE / CPU fallback / 动态降采样。
- [ ] 做最小验证后再决定是否重新发起正式长跑。

### 状态
**目前仍在阶段5** - 当前从“正式长跑观察”切换到“新 OOM 的根因收敛与修复”。

## [2026-03-22 10:47:21] [Session ID: 2e546d88-242b-47b8-a6a3-eff09359ded0] [记录类型]: 记录用户对 extensive 质量边界的新约束

### 用户新约束
- extensive 模式下不要随便降低样本数。
- 只有在可以证明不影响质量时,才允许动样本规模。
- 如果最终确认这台机器显存就是不够正式跑,不要勉强硬跑。

### 当前执行策略
- 优先尝试“不改样本数、不改采样语义”的显存削峰方案。
- 当前最优先候选是把 `RoMaV2.sample -> kde()` 内部的整块 `torch.cdist(x, x)` 改成等价分块计算。
- 若等价削峰后仍然无法完成,则如实给出“当前 GPU 不适合该 formal extensive 配置”的结论,不通过偷偷降样本糊弄跑通。

### 状态
**目前仍在阶段5** - 已记录用户质量边界,接下来只评估等价显存优化方案。

## [2026-03-22 10:49:43] [Session ID: 1774147758-2955119] [记录类型]: 核对 run_multiview_reconstruction 的视频采样语义

### 目标
- 确认多视角入口在视频源输入下,是否逐帧抽取全部帧,还是先按某种规则做稀疏采样。
- 找到实际控制采样行为的代码位置和配置项。

### 执行计划
- [ ] 阅读 `run_multiview_reconstruction.py` 与 `preprocess_multiview.py` 的入口调用链。
- [ ] 阅读 `preprocess_video.py` 与相关配置,确认视频帧抽取与 subsample 逻辑。
- [ ] 整理成“现象 -> 代码证据 -> 结论”的答复。

### 状态
**目前在阶段2** - 正在读取入口与预处理实现,确认视频帧是全量抽帧还是抽帧后再二次下采样。

## [2026-03-22 10:49:43] [Session ID: 2e546d88-242b-47b8-a6a3-eff09359ded0] [记录类型]: 启动 `kde` 分块修复后的 Stage 1 最小动态验证

### 验证目的
- 不立刻重跑完整 extensive。
- 先只重跑 `frame_to_model_icp`,确认新的 `kde()` 分块实现是否能越过正式长跑里 `frame 13` 左右的 OOM。

### 验证标准
- 若再次在 `sample() -> kde() -> torch.cdist()` 报 OOM,则当前等价削峰方案不足。
- 若稳定越过 `frame 13` 并继续推进,则说明这次修法对真实场景有效,下一步再考虑重新发起完整 extensive。

### 状态
**目前仍在阶段5** - 即将启动仅 Stage 1 的动态验证。

## [2026-03-22 10:50:09] [Session ID: 2e546d88-242b-47b8-a6a3-eff09359ded0] [记录类型]: `kde` 分块修复后的 Stage 1 probe 已启动

### 启动信息
- 主 PTY 会话 ID: `32510`
- 主日志:
  - `/tmp/video_to_world_flashvsr_reference_xhc_bai_stage1_probe_kdefix_20260322_104955.log`
- GPU 日志:
  - `/tmp/video_to_world_flashvsr_reference_xhc_bai_stage1_probe_kdefix_gpu_20260322_104955.log`
- 实际命令:
  - `pixi run python -m frame_to_model_icp --config.root-path output/flashvsr_reference_xhc_bai --config.icp-early-stopping-min-delta 5e-06 --config.out-suffix _zzkdefix_probe_20260322_104955`

### 状态
**目前仍在阶段5** - probe 已启动,接下来重点观察它能否越过 `frame 13` 并继续推进。

## [2026-03-22 10:50:28] [Session ID: 1774147758-2955119] [记录类型]: 已确认多视角视频输入的采样语义

### 已完成
- [x] 阅读 `run_multiview_reconstruction.py` 与 `preprocess_multiview.py` 的入口调用链。
- [x] 阅读 `preprocess_video.py` 与相关配置,确认视频帧抽取与 subsample 逻辑。
- [x] 整理成“现象 -> 代码证据 -> 结论”的答复。

### 已验证结论
- `run_multiview_reconstruction.py` 不会直接逐帧处理视频,而是先把每个视角交给 `preprocess_multiview.py`。
- `preprocess_multiview.py` 又会把每个视角交给 `preprocess_video.py`。
- `preprocess_video.py` 对视频输入的真实行为是: 先全量解帧到 `frames/`,再按 `max_frames` / `max_stride` 做子采样,最后只对 `frames_subsampled/` 里的帧跑 DA3。
- 因此默认情况下不是“全视频逐帧进入后续重建”,而是“全量解码 + 稀疏抽帧 + 对抽样帧做重建”。
- 只有当视频总帧数不超过 `max_frames` 时,才会表现为逐帧全量使用。

### 状态
**目前在阶段4** - 证据已收集完成,下一步直接向用户汇报结论并给出可调参数说明。

## [2026-03-22 10:52:34] [Session ID: 1774147758-2955119] [记录类型]: 用户要求落到真实多视角数据,核对默认采样实际取帧

### 目标
- 对当前多视角数据给出每个视角实际用了哪些帧。
- 给出总帧数、实际 stride、选中帧索引范围,以及是否只覆盖前半段。

### 执行计划
- [ ] 找到这份多视角数据对应的 `scene_root` 与 `preprocess_frames.json`。
- [ ] 读取每个视角的预处理元数据,确认 `num_frames_used` 与 `actual_stride`。
- [ ] 如有必要,补查源视频总帧数,把“选中了哪些原始帧”算出来。
- [ ] 整理成面向这份真实数据的结论。

### 状态
**目前在阶段2** - 正在定位当前多视角数据的真实预处理产物和元数据。

## [2026-03-22 10:53:58] [Session ID: 1774147758-2955119] [记录类型]: 已核对真实多视角数据的默认采样结果

### 已完成
- [x] 找到这份多视角数据对应的 `scene_root` 与 `preprocess_frames.json`。
- [x] 读取每个视角的预处理元数据,确认 `num_frames_used` 与 `actual_stride`。
- [x] 补查真实解帧目录与内容匹配,确认到底选中了哪些原始帧。
- [x] 整理成面向这份真实数据的结论。

### 已验证结论
- 当前核对的数据是: `source/flashvsr_reference_xhc_bai/full_scale2x` -> `output/flashvsr_reference_xhc_bai`。
- 6 个视角每个都先解出了 121 帧原始图片。
- 但后续每个视角只用了 100 帧,并且 `actual_stride=1`。
- 通过对 `frames_subsampled` 与 `frames` 做文件内容匹配,已确认每个视角实际选中的是原始 `000001.png` 到 `000100.png`。
- 原始 `000101.png` 到 `000121.png` 没有进入后续 DA3 和重建。
- 联合场景总共用了 600 帧,按视角顺序拼接成全局索引。

### 状态
**目前在阶段4** - 真实数据的采样结果已经核对完成,下一步直接向用户汇报并解释为什么会出现“stride=1 但仍只用 100 帧”。

## [2026-03-22 10:55:57] [Session ID: 2e546d88-242b-47b8-a6a3-eff09359ded0] [记录类型]: 启动第二轮 Stage 1 动态验证,检查显式清理是否能压低 late-frame 常驻显存

### 验证目标
- 复测 `frame 15` / `frame 16` 附近的 `[CUDA][after_empty_cache]` 与 `[before_roma]`。
- 判断显式 `del + gc.collect() + empty_cache()` 是否真的把跨帧常驻显存压下去。

### 判定口径
- 若常驻显存明显下降且继续越过 `frame 16`,说明存在可修复的生命周期问题。
- 若常驻显存几乎不降,而且仍在 refiner 处 OOM,就更接近“当前 GPU 对正式 extensive 不足”的结论。

### 状态
**目前仍在阶段5** - 即将启动第二轮 Stage 1 probe。

## [2026-03-22 11:00:22] [Session ID: 2e546d88-242b-47b8-a6a3-eff09359ded0] [记录类型]: 启动第三轮 Stage 1 probe,验证 matcher 懒创建是否消除双份常驻

### 验证目标
- 观察 `frame 17` 左右的 `before_roma` / `after_roma`。
- 重点看 `after_roma - before_roma` 是否还会出现接近一整份 matcher 的额外常驻跃迁。

### 状态
**目前仍在阶段5** - 即将启动第三轮 Stage 1 probe。

## [2026-03-22 11:07:37] [Session ID: 1774147758-2955119] [记录类型]: 用户要求在 cmd.md 中补充 max_stride 的设置方法

### 目标
- 找到仓库里的 `cmd.md`。
- 根据真实 CLI 参数,补上 `max_stride` 的设置方法和示例命令。
- 如有必要,顺手说明多视角入口与单视角入口参数名的差异。

### 执行计划
- [ ] 阅读 `cmd.md` 当前内容与相关命令示例。
- [ ] 核对 `preprocess_video.py`、`preprocess_multiview.py`、`run_multiview_reconstruction.py` 的真实参数名。
- [ ] 更新 `cmd.md` 并做最小校验。

### 状态
**目前在阶段2** - 正在定位 `cmd.md` 并核对参数名。

## [2026-03-22 11:08:11] [Session ID: 1774147758-2955119] [记录类型]: 用户要求在 cmd.md 中补充设置 stride 的方法

### 目标
- 在仓库文档中明确写出如何通过命令行设置视频采样 stride。
- 同时区分多视角入口和单视频预处理入口的参数名。

### 执行计划
- [ ] 检查仓库中是否已有 `cmd.md`。
- [ ] 核对 `run_multiview_reconstruction.py` 与 `preprocess_video.py` 的实际参数名。
- [ ] 更新 `cmd.md`,补充可直接复制的命令示例。

### 状态
**目前在阶段3** - 正在定位现有命令文档并准备写入 stride 设置说明。

## [2026-03-22 11:09:20] [Session ID: 1774147758-2955119] [记录类型]: 已在 docs/cmd.md 补充 stride 设置方法

### 已完成
- [x] 检查仓库中是否已有 `cmd.md`。
- [x] 核对 `run_multiview_reconstruction.py` 与 `preprocess_video.py` 的实际参数名。
- [x] 更新 `docs/cmd.md`,补充可直接复制的命令示例。

### 已验证结果
- 已在 `docs/cmd.md` 新增“设置视频预处理的 stride”小节。
- 已区分多视角总入口 `--preprocess-max-stride`、联合预处理 `--max-stride`、单视频预处理 `--max_stride`。
- 已补充 Stage 1 的 `--config.alignment.stride` 说明,避免和 Stage 0 混淆。
- 已写明 `max_stride` 只是上限,实际结果还要看 `preprocess_frames.json` 里的 `actual_stride` 与 `num_frames_used`。

### 状态
**目前在阶段4** - 文档更新完成,下一步向用户汇报修改位置和可直接使用的命令。

## [2026-03-22 11:12:30] [Session ID: 3515473] [记录类型]: 继续 extensive Stage 1 OOM 排查,准备收口已停止的 probe 并追查 inner refresh 生命周期

### 背景
- 用户确认上一轮 probe "已经停了"。
- 当前目标不变: 在不随意降低样本数的前提下,继续推进 `source/flashvsr_reference_xhc_bai` 的 `extensive` 模式。
- 根据上一轮动态证据,外层 matcher 常驻问题已明显缓解,当前最强候选问题缩到 `compute_roma_matches_for_frame()` 的 inner refresh 生命周期。

### 当前主假设
- 主假设:
  - 帧内每 4 个新 pair 的 refresh 路径仍然存在“旧 matcher 未完全回收就重建新 matcher”的问题,导致 late-frame 常驻显存台阶式抬升。
- 备选解释:
  - 即使 refresh 生命周期进一步修好,late-frame 的 refiner 峰值本身也可能最终超过这张卡的可用显存。

### 本轮计划
- [ ] 确认当前没有残留 pipeline 进程和 GPU 占用。
- [ ] 阅读 Stage 1 / RoMa 相关代码与最新 probe 日志,补齐静态和动态证据。
- [ ] 对 inner refresh 做最小修复,优先尝试“删除后不立刻重建,改为下次需要时懒创建”。
- [ ] 运行最小验证: 语法检查 + RoMa 内存相关单测 + Stage 1 probe。
- [ ] 根据结果判断是否可以继续正式 extensive,还是需要明确结论为当前 GPU 仍不足。

### 状态
**目前在阶段2** - 正在确认现场已停并准备进入 inner refresh 证据复盘。

## [2026-03-22 11:18:20] [Session ID: 3515473] [记录类型]: 准备启动去掉 inner refresh 后的 Stage 1 probe

### 启动目的
- 只验证 `compute_roma_matches_for_frame()` 去掉帧内重复重建之后,Stage 1 能否越过 `frame 20`。
- 暂不直接重跑完整 extensive,避免把 Stage 2/3 噪音混进本轮证据。

### 预期判定
- 若 `frame 18~20` 的 `after_roma` 不再出现 `18.84 GiB -> 37.76 GiB` 这类台阶跃迁,说明本轮修复命中了主要问题。
- 若仍然在相近位置 OOM,则需要转向评估“单个 matcher 连跑 late-frame pair 本身就超这张卡”的可能性。

### 状态
**目前在阶段4** - 即将启动新的 Stage 1 probe。

## [2026-03-22 11:14:01] [Session ID: 1774147758-2955119] [记录类型]: 澄清 run_multiview_reconstruction 中 Stage 1 stride 与 preprocess stride 的区别

### 目标
- 确认 `run_multiview_reconstruction.py` 是否能透传 `--config.alignment.stride` 给 ICP。
- 明确 `--config.alignment.stride` 和 `--preprocess-max-stride` 是否等价。

### 状态
**目前在阶段4** - 基于已经核对过的入口代码,正在整理分层结论和可直接复制的命令示例。

## [2026-03-22 11:17:40] [Session ID: 1774147758-2955119] [记录类型]: 正在确认 Stage 1 中 num_frames 与 stride 的先后关系

### 现象
- 用户问的是: Stage 0 先把 100 帧缩成 50 帧后,Stage 1 的 stride=2 会不会再从这 50 帧里缩成 25 帧。

### 当前假设
- 主假设: Stage 1 是从 Stage 0 产出的底层序列按 `offset::stride` 先取索引,再用 `[:num_frames]` 截断。
- 备选解释: Stage 1 也可能先限定 `num_frames`,再在这批帧里继续按 stride 二次减半。

### 验证计划
- 读取 `data/data_loading.py` 中 `load_data` 的索引生成逻辑。
- 用代码证据回答用户,避免按 README 文案猜测。

### 状态
**目前在阶段4** - 正在核对 Stage 1 真实索引公式。

## [2026-03-22 11:18:19] [Session ID: 1774147758-2955119] [记录类型]: 已确认两层 stride 的真实取帧公式

### 已验证结论
- Stage 0 的 `subsample_frames()` 逻辑是先根据总帧数算 `stride`,生成 `range(0, total_frames, stride)`,再用 `max_frames` 截断。
- 因此 `--preprocess-max-frames 100 --preprocess-max-stride 2` 不等于“100 里取 50”。
- Stage 1 的 `load_data()` 逻辑是 `all_indices[offset::stride][:num_frames]`。
- 因此 Stage 1 不是“先取 `num_frames`,再在这批帧里继续按 stride 减半”,而是“先按 stride 选底层序列,再最多保留 `num_frames` 张”。
- 如果 Stage 0 最终产出 100 帧,并且 Stage 1 用默认 `num_frames=50, stride=2`,那么 Stage 1 最终会取到 50 帧,不是 25 帧。

### 状态
**目前在阶段4** - 公式已核实完成,下一步直接向用户给出反例和正确心智模型。

## [2026-03-22 11:32:10] [Session ID: 3515473] [记录类型]: 新 probe 已完成,旧 repeated-init 问题已修掉,当前阻塞转为单帧 20+ 新 pair 的累计常驻显存

### 已完成
- [x] 确认当前没有残留 pipeline 进程和 GPU 占用。
- [x] 阅读 Stage 1 / RoMa 相关代码与最新 probe 日志,补齐静态和动态证据。
- [x] 对 inner refresh 做最小修复,优先尝试“删除后不立刻重建,改为下次需要时懒创建”。
- [x] 运行最小验证: 语法检查 + RoMa 内存相关单测 + Stage 1 probe。

### 新结论
- 这轮 probe 已稳定越过旧的 `frame 18/19` repeated-init 死亡点。
- 但 `frame 20` 作为第一个 uncached 的 `20` 新 pair 帧,会把 `after_roma` 抬到 `20.81 GiB`,并把这层常驻显存带进 `frame 21`。
- 因此当前待办已经切换为: 查清楚单帧内 repeated `match_images()` 的累计状态,再决定要不要做 pair 粒度 unload/offload。

### 剩余待办
- [ ] 给 `compute_roma_matches_for_frame()` / `_match_images_v2()` 加 pair 粒度显存日志,定位是哪一步开始累计。
- [ ] 设计并验证更强的释放策略,优先评估 `model.cpu()` / hard unload 是否能打断单帧累计。
- [ ] 若 pair 级释放仍无法控制峰值,再明确向用户下结论: 当前 GPU 对 formal extensive 的 Stage 1 仍不足。

### 状态
**目前在阶段5** - 已完成一轮有效修复,当前进入新的单帧累计显存诊断阶段。

## [2026-03-22 11:29:41] [Session ID: 1774147758-2955119] [记录类型]: 核对之前 Stage 1 ICP 运行实际使用的 stride

### 目标
- 确认当前多视角场景目录下,之前实际跑过的 Stage 1 ICP 使用了什么 `alignment.stride`。
- 如果可以,同时给出它相对原始视频的等效取帧步长。

### 执行计划
- [ ] 列出 `output/flashvsr_reference_xhc_bai` 下已有的 `frame_to_model_icp_*` 目录。
- [ ] 读取对应 `after_non_rigid_icp/config.json` 里的 `alignment` 配置。
- [ ] 结合 Stage 0 的真实 `actual_stride`,整理成用户能直接理解的结论。

### 状态
**目前在阶段4** - 正在核对已有 Stage 1 运行目录与落盘配置。

## [2026-03-22 11:44:20] [Session ID: 3515473] [记录类型]: 准备启动 isolated-worker 版 Stage 1 probe

### 启动目的
- 验证 RoMaV2 子进程隔离后,主 Stage 1 进程能否越过 `frame 21`。
- 重点观察 `before_roma/after_roma` 是否重新回到低位,而不是继续继承 `20.81 GiB` 平台。

### 状态
**目前在阶段5** - 即将启动 isolated-worker 版 probe。

## [2026-03-22 11:37:30] [Session ID: 3515473] [记录类型]: 复核用户“已经停了”后的 probe 存活状态

### 复核动机
- 用户反馈“已经停了好像”。
- 这类状态判断不能靠感觉,必须重新核对真实进程与日志尾部。

### 动态证据
- `pgrep -af 'frame_to_model_icp|run_reconstruction|train_gs|eval_gs'` 仍能看到:
  - `pixi run python -m frame_to_model_icp --config.root-path output/flashvsr_reference_xhc_bai --config.icp-early-stopping-min-delta 5e-06 --config.out-suffix _zzisolated_probe_20260322_114420`
  - 以及其 Python 子进程。
- 日志 `/tmp/video_to_world_flashvsr_reference_xhc_bai_stage1_probe_isolated_20260322_114420.log` 已推进到:
  - `Frame 26` 完整结束
  - `Frame 27` 已进入 ICP / RoMa 阶段
- 当前日志继续增长,未见新的 `Traceback` 或 OOM。

### 当前结论
- “看起来停了” 这一判断目前不成立。
- 到 `2026-03-22 11:36:33 CST` 为止,isolated-worker 版 Stage 1 probe 仍在运行中。

### 状态
**目前在阶段5** - 继续观察 probe 是否完整跑完,再决定是否切正式 extensive。

## [2026-03-22 11:38:20] [Session ID: 1774147758-2955119] [记录类型]: 验证全局 600 帧上 stride=6 的 Stage 1 取帧分布

### 目标
- 用当前真实联合元数据验证: `num_frames=100, stride=6` 时,Stage 1 是否会跨 6 个视角取样。
- 判断这是否已经满足“不是单独每个镜头”的要求。

### 状态
**目前在阶段4** - 正在基于 `preprocess_frames.json` 的全局区间做索引分布验证。

## [2026-03-22 11:49:30] [Session ID: 3515473] [记录类型]: isolated-worker 版 Stage 1 probe 已完整成功,决定复用其结果进入正式 extensive 下半段

### 已验证结论
- `/tmp/video_to_world_flashvsr_reference_xhc_bai_stage1_probe_isolated_20260322_114420.log` 中未发现 `Traceback` / `OutOfMemoryError` / `ERROR`。
- 日志已完整推进到 `Frames: 100%|...| 49/49`。
- `Frame 49` 结束后仍保持:
  - `after_empty_cache allocated=0.37 GiB reserved=0.46 GiB`
- 产物目录已存在:
  - `output/flashvsr_reference_xhc_bai/frame_to_model_icp_50_2_offset0_zzisolated_probe_20260322_114420/after_non_rigid_icp`
- 关键产物已落盘:
  - `aligned_points.ply`
  - `config.json`
  - `roma_match_history.pt`
  - `per_frame_global_deform_*.pt`
  - `per_frame_local_deform_*.pt`

### 决策
- 不再重复执行正式 extensive 的 Stage 1。
- 直接使用 `--config.skip-alignment --config.alignment-run frame_to_model_icp_50_2_offset0_zzisolated_probe_20260322_114420` 进入 Stage 2/3。

### 这样做的原因
- 这轮 probe 的 Stage 1 参数与 extensive 要求一致:
  - `alignment.num_frames=50`
  - `alignment.stride=2`
  - `icp_early_stopping_min_delta=5e-06`
- 因此复用不会降低质量,只是在避免无意义重复耗时。

### 状态
**目前在阶段5** - 正在记录 probe 成功证据,下一步启动复用 Stage 1 结果的正式 extensive 下半段。

## [2026-03-22 11:50:20] [Session ID: 3515473] [记录类型]: 准备启动复用 Stage 1 结果的正式 extensive 下半段

### 启动命令
- `pixi run python run_reconstruction.py --config.root-path output/flashvsr_reference_xhc_bai --config.mode extensive --config.skip-alignment --config.alignment-run frame_to_model_icp_50_2_offset0_zzisolated_probe_20260322_114420`

### 运行目标
- 跳过已成功验收的 Stage 1。
- 正式进入 Stage 2 global optimization,随后继续 Stage 3.1 inverse deformation 和 Stage 3.2 训练。
- 观察新的首个真实阻塞点是否已经转移到 Stage 2/3。

### 状态
**目前在阶段5** - 已写入正式下半段启动记录,下一步立刻拉起进程并观察首批日志。

## [2026-03-22 11:49:37] [Session ID: 1774147758-2955119] [记录类型]: 计算 6 镜头 x 120 帧配置下各阶段实际用帧数

### 目标
- 结合 `preprocess_video.py` 与 `data_loading.py` 的真实公式,计算给定参数下 Stage 0 与 Stage 1 各自会用多少图。
- 先确认重复传入两个 `--config.alignment.stride` 时,实际哪一个值生效。

### 状态
**目前在阶段4** - 正在做最小 CLI 验证并按真实公式计算每阶段帧数。

## [2026-03-22 11:52:40] [Session ID: 3515473] [记录类型]: Stage 2 首次启动失败,已确认是可选 GPU KD-tree 依赖缺失,改走 CPU KD-tree 继续

### 现象
- 复用 Stage 1 结果进入正式 extensive 后,Stage 2 启动即报:
  - `ModuleNotFoundError: No module named 'torch_kdtree'`

### 静态证据
- `configs/stage2_global_optimization.py` 明确把 `knn_backend` 默认设为 `gpu_kdtree`。
- `algos/global_optimization.py` 的函数默认值其实是 `cpu_kdtree`。
- `README.md` 也把 `torch_kdtree` 标成 optional 安装项。

### 已验证结论
- 这不是 Stage 2 逻辑错误。
- 这是“默认启用可选 GPU KD-tree 加速,但当前环境没装对应扩展”。
- 将 Stage 2 改回 `cpu_kdtree` 只会主要影响速度,不会改变采样规模或故意降质量。

### 决策
- 不先去现场编译 `torch_kdtree`。
- 直接重启正式 extensive 下半段,追加:
  - `--config.stage2.knn-backend cpu_kdtree`

### 状态
**目前在阶段5** - 正在记录新阻塞点,下一步用 CPU KD-tree 重启 Stage 2/3。

## [2026-03-22 11:53:58] [Session ID: 3515473] [记录类型]: CPU KD-tree 方案已推动正式 extensive 越过 Stage 2,并进入 Stage 3.1 训练

### 已验证结论
-  已让 Stage 2 不再被  缺失阻塞。
- Global optimization 已经从初始化推进到多轮真实迭代,并成功越过  的中后段。
- 当前日志已进入  /  输出,说明 Stage 3.1 inverse deformation 已经开始。

### 当前状态判断
- 当前主流程已经越过:
  - Stage 1
  - Stage 2
- 当前正在进行:
  - Stage 3.1 inverse deformation
- 下一个待观察节点:
  - Stage 3.1 是否完整结束
  - Stage 3.2 2DGS / 3DGS 是否启动
  - 自动 eval 是否再次暴露新问题

### 状态
**目前在阶段5** - 正在继续观察 Stage 3.1 训练,并等待进入 GS 阶段。

## [2026-03-22 11:57:10] [Session ID: 3515473] [记录类型]: 更正上一条被 shell 命令替换污染的进度记录,正式确认 extensive 已越过 Stage 2 并进入 Stage 3.1

### 说明
- 上一条 `2026-03-22 11:53:58` 记录在写入时误用了未加引号 heredoc。
- 由于正文包含反引号,其中部分内容被 shell 当成命令替换,导致文字缺失。
- 本条是对应的正式更正版本,后续以本条为准。

### 已验证结论
- `--config.stage2.knn-backend cpu_kdtree` 已让 Stage 2 不再被 `torch_kdtree` 缺失阻塞。
- Global optimization 已经从初始化推进到多轮真实迭代,并成功越过 `iter=100` 的中后段。
- 当前日志已进入 `Training:` / `Epoch x/30` 输出,说明 Stage 3.1 inverse deformation 已经开始。

### 当前状态判断
- 当前主流程已经越过:
  - Stage 1
  - Stage 2
- 当前正在进行:
  - Stage 3.1 inverse deformation
- 下一个待观察节点:
  - Stage 3.1 是否完整结束
  - Stage 3.2 2DGS / 3DGS 是否启动
  - 自动 eval 是否再次暴露新问题

### 状态
**目前在阶段5** - 正在继续观察 Stage 3.1 训练,并等待进入 GS 阶段。

## [2026-03-22 11:57:54] [Session ID: 1774147758-2955119] [记录类型]: 用户询问如何设置输出目录

### 目标
- 区分多视角联合入口、单场景流水线入口、Stage 0 预处理三种层面的输出目录参数。
- 给出可直接复制的命令示例。

### 状态
**目前在阶段4** - 正在核对 `scene_root`、`root_path`、`output_root` 的真实语义。

## [2026-03-22 12:01:40] [Session ID: 3515473] [记录类型]: 正式 extensive 已越过 Stage 3.1,并进入 Stage 3.2 2DGS 训练

### 已验证结论
- inverse deformation 训练与验证已经完成,日志出现 `Round-trip validation summary`。
- 管线已打印:
  - `[PIPELINE] === Stage 3.2: 2DGS Training ===`
- `train_gs` 已经真正开始迭代:
  - `GS training (2dgs): ... 17/15000`

### 当前状态判断
- 当前正式 extensive 运行已经越过:
  - Stage 1
  - Stage 2
  - Stage 3.1
- 当前正在进行:
  - Stage 3.2 2DGS 训练
- 后续仍需继续观察:
  - 2DGS 是否稳定长跑
  - 之后的 3DGS 是否启动
  - 自动 eval 与 `gs_video/0000_extend_transforms.json` 相关分支是否触发

### 状态
**目前在阶段5** - 正在长跑 2DGS 训练,后续继续观察关键切换点。
