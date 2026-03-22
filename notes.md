# 研究笔记

## [2026-03-22 04:39:30] [Session ID: e7d33bb8-22af-4207-a9b3-224a0f3a3b4e] 笔记: 六文件续档前的最小持续学习摘要

### 来源
- 当前默认六文件:
  - `task_plan.md` 的旧续档文件
  - `WORKLOG.md`
  - `LATER_PLANS.md`
  - `EPIPHANY_LOG.md`
  - `ERRORFIX.md`
- 当前相关历史文件:
  - `archive/task_plan_2026-03-21_234700.md` (本轮已阅读后归档)
  - `notes_2026-03-22_043931.md` (由本轮续档生成)
  - `task_plan_2026-03-22_043931.md` (由本轮续档生成)

### 六文件摘要
- 任务目标:
  - 之前的主线已经完成环境修复、后半程测试跑、GS auto eval OOM 修复,以及 GS resume 的 OpenSpec 准备。
- 关键决定:
  - `source/flashvsr_reference_xhc_bai` 作为多视角数据时,应走 `run_multiview_reconstruction.py` 而不是单视角入口。
  - `eval_gs` 缺失 `gs_video/0000_extend_transforms.json` 时允许自动降级,但那只影响评估覆盖,不影响训练本体。
  - 当前机器显存是否足够,不能只看 OOM 现象,要区分真实容量不足和生命周期/跨进程占卡。
- 关键发现:
  - 当前机器是 `RTX 6000 Ada 49 GB`,之前默认 3DGS 正式长跑已能稳定起跑。
  - 当前 GS checkpoint 还不能正式 resume,但对应 OpenSpec change 已 apply-ready。
- 实际变更:
  - 已经修过 `run_reconstruction.py` 的 GS 轮数覆盖问题。
  - 已经修过 `eval_gs.py` 的 transforms 缺失降级。
  - 已经修过 `train_gs.py` 的 auto eval 前显存释放。
- 暂缓事项 / 后续方向:
  - 未来仍值得做 smoke-test preset。
  - 未来仍值得实现正式的 GS training resume。
- 可复用点候选:
  - 多视角联合数据应优先用多视角入口执行,避免把入口选错成单视频模式。
  - GPU OOM 分析必须分开看单进程峰值和父子进程生命周期。
  - 长跑任务要同时挂训练日志和 GPU 采样日志,这样后续排障才有对时证据。

### 沉淀去向判断
- 本轮未发现必须立刻同步到 `AGENTS.md` 的新项目级硬规则。
- 当前也没有需要立即改写 `docs/` / `specs/` 的新稳定知识点。
- 以上摘要足以支撑本轮继续执行 extensive 正式运行。

## [2026-03-22 04:42:36] [Session ID: e7d33bb8-22af-4207-a9b3-224a0f3a3b4e] 笔记: `source/flashvsr_reference_xhc_bai` 的 extensive 多视角正式运行已成功拉起

### 来源
- 主运行日志:
  - `/tmp/video_to_world_flashvsr_reference_xhc_bai_extensive_20260322_044004.log`
- GPU 采样日志:
  - `/tmp/video_to_world_flashvsr_reference_xhc_bai_extensive_gpu_20260322_044004.log`
- 输出目录快照:
  - `output/flashvsr_reference_xhc_bai/per_view/view_0..4`

### 已验证事实
- extensive 使用的真实入口命令为:
  - `pixi run python run_multiview_reconstruction.py --views-root source/flashvsr_reference_xhc_bai/full_scale2x --scene-root output/flashvsr_reference_xhc_bai --config.mode extensive`
- 运行环境中同时启用了:
  - `http_proxy` / `https_proxy` / `all_proxy`
  - `HF_ENDPOINT=https://hf-mirror.com`
- 当前主日志已显示 `Stage 0: preprocess_multiview.py` 正在顺序处理多个视角。
- `view_0` 到 `view_3` 已明确完成 DA3 preprocessing,并各自产生:
  - `exports/npz/results.npz`
  - `gs_video`
- `view_4` 已开始处理。
- 当前还没有看到需要人工介入的错误栈或超时卡点。

### 当前判断
- 到目前为止,这不是“命令刚发出去”的假启动,而是真正已经进入多视角 extensive 的执行路径。
- 下一阶段的重点不再是“能不能启动”,而是“Stage 0 合并后,是否能继续进入 extensive 主流程的后续阶段”。

## [2026-03-22 10:30:30] [Session ID: e7d33bb8-22af-4207-a9b3-224a0f3a3b4e] 笔记: `source/flashvsr_reference_xhc_bai` 的 extensive 长跑已在 Stage 1 失败退出

### 来源
- 主运行日志:
  - `/tmp/video_to_world_flashvsr_reference_xhc_bai_extensive_20260322_044004.log`
- PTY 会话:
  - `90694`
- 进程检查:
  - 当前无相关 pipeline 进程存活

### 已验证事实
- 这次运行并未完成。
- 失败位置在 `frame_to_model_icp` 的 Stage 1 中,调用链进入 RoMaV2 refiner 时触发 OOM。
- 关键报错为:
  - `torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 200.00 MiB`
- 日志给出的失败时 GPU 状态是:
  - 总显存约 `47.37 GiB`
  - 空闲仅 `122.88 MiB`
  - 该进程占用约 `46.86 GiB`
  - PyTorch allocated 约 `42.59 GiB`
- 失败发生在 Stage 1 中后段,不是启动即失败:
  - Stage 0 已全部完成
  - Stage 1 至少推进到 `Frames 8/49`

### 当前判断
- 这不是“入口选错”或“代理没配好”的问题。
- 当前更像是 extensive 模式下 Stage 1 的 RoMa 相关显存峰值过高,并且峰值出现在处理中段而不是第一帧。
- 后续如果继续跑 extensive,需要先针对 Stage 1 的显存生命周期做收敛,否则重复直接重跑大概率还会撞到同一处。

## [2026-03-22 10:31:41] [Session ID: e7d33bb8-22af-4207-a9b3-224a0f3a3b4e] 笔记: 当前 OOM 不是“明显的同一 RoMa matcher 跨帧复用”型问题

### 来源
- 静态代码:
  - `frame_to_model_icp.py` 第 540-605 行附近
  - `models/roma_matcher.py` 第 521-560 行附近
- 动态日志:
  - `/tmp/video_to_world_flashvsr_reference_xhc_bai_extensive_20260322_044004.log`

### 已验证事实
- 代码里已经实现了两层 matcher 重建:
  - 每帧 RoMa 结束后重建一次
  - 单帧内每 4 个新 pair 还会再重建一次
- 日志里重复出现 `Initializing RoMa matcher`,说明这条重建路径在真实运行中确实发生了。
- 因此,当前不能再把问题简单表述成“同一个 RoMa matcher 一直复用所以泄漏”。

### 当前更强的候选假设
- 随着 Stage 1 推进,模型点云和相关状态持续增长。
- 到 `frame 8` 左右时,Stage 1 常驻显存已经很高,再叠加一次 RoMaV2 refiner 的瞬时前向峰值,于是触发 OOM。
- 这个判断来自“静态生命周期证据 + 动态 `model_pts` 增长与 OOM 时点”,但还需要专门的显存打点来最终确认。

## [2026-03-22 10:41:55] [Session ID: 2e546d88-242b-47b8-a6a3-eff09359ded0] 笔记: `run_reconstruction.py` 会按字典序选择最后一个 Stage 1 目录,当前 probe 目录会干扰正式续跑

### 来源
- 静态代码:
  - `run_reconstruction.py` 第 343-346 行附近
  - `frame_to_model_icp.py` 第 165-183 行附近
- 当前目录现状:
  - `output/flashvsr_reference_xhc_bai/frame_to_model_icp_50_2_offset0`
  - `output/flashvsr_reference_xhc_bai/frame_to_model_icp_50_2_offset0_oomfix_probe_20260322_103545`

### 已验证事实
- `frame_to_model_icp.py` 默认会把 Stage 1 输出写到固定目录:
  - `frame_to_model_icp_<num_frames>_<stride>_offset<offset><out_suffix>`
- 若不显式指定新的 `out_suffix`,重跑 Stage 1 会继续写回旧的 `frame_to_model_icp_50_2_offset0`。
- `run_reconstruction.py` 在 Stage 1 后不会读取“当前这次命令实际写入的目录”,而是调用 `_find_subdir(root_path, "frame_to_model_icp_")` 取字典序最后一个目录。
- 在当前现场里,probe 目录名 `frame_to_model_icp_50_2_offset0_oomfix_probe_20260322_103545` 会排在默认目录之后。

### 当前判断
- 如果直接按原默认目录重跑,Stage 2/3 存在误接到 probe 目录的真实风险。
- 当前最稳的执行策略不是删历史证据,而是给本次正式 Stage 1 指定一个新的、按字典序确保排在最后的 `out_suffix`,让 downstream 明确接到这次正式运行的目录。

## [2026-03-22 10:45:08] [Session ID: 2e546d88-242b-47b8-a6a3-eff09359ded0] 笔记: 修复后的正式 extensive 长跑在 `RoMaV2.sample -> kde -> torch.cdist` 处再次 OOM

### 来源
- 主日志:
  - `/tmp/video_to_world_flashvsr_reference_xhc_bai_extensive_resume_20260322_104213.log`
- GPU 日志:
  - `/tmp/video_to_world_flashvsr_reference_xhc_bai_extensive_resume_gpu_20260322_104213.log`

### 已验证事实
- 这次正式长跑已越过旧的 `frame 8` OOM 点,并推进到 `frame 13`。
- 新的栈顶不在上一轮的 refiner,而在:
  - `models/roma_matcher.py::_match_images_v2`
  - `self.model.sample(preds, num_samples)`
  - `third_party/RoMaV2/src/romav2/romav2.py::sample`
  - `third_party/RoMaV2/src/romav2/romav2.py::kde`
  - `scores = (-(torch.cdist(x, x) ** 2) / (2 * std**2)).exp()`
- 动态报错为:
  - `Tried to allocate 764.00 MiB`
  - 当时 GPU 空闲约 `460.88 MiB`
  - 该进程总占用约 `46.53 GiB`

### 当前判断
- 这次新的峰值更像是 `sample()` 里的 KDE / pairwise distance 造成的 `O(N^2)` 瞬时显存开销,而不再是上一轮已经修过的 matcher 生命周期问题。
- 下一步需要直接审查 `sample()` / `kde()` 的实现,确认是否可以做 chunked 计算或更低峰值的 fallback。

## [2026-03-22 10:50:04] [Session ID: 1774147758-2955119] 笔记: run_multiview_reconstruction 的视频帧采样链路

### 来源

#### 来源1: run_multiview_reconstruction.py
- 要点:
  - 多视角入口本身不直接处理视频帧,它只是先调用 `preprocess_multiview.py`,再调用 `run_reconstruction.py`。
  - 默认会把 `preprocess_max_frames=100` 和 `preprocess_max_stride=8` 传给联合预处理。

#### 来源2: preprocess_multiview.py
- 要点:
  - 每个视角都会独立调用一次 `preprocess_video.py`。
  - 也就是说,视频采样语义实际由单视角预处理决定,多视角层只负责汇总和合并。

#### 来源3: preprocess_video.py
- 要点:
  - 当输入是 `--input_video` 时,先用 `ffmpeg -i <video> -vsync 0` 把视频全量解成 `frames/*.png`。
  - 之后再调用 `subsample_frames()` 从这些已抽出的帧里选出一部分,并复制到 `frames_subsampled/`。
  - DA3 实际只对 `frames_subsampled/` 里的帧做推理。
  - 默认参数是 `max_frames=100`, `max_stride=8`。
  - 如果视频总帧数 `<= max_frames`,就直接全量使用,此时 stride=1。
  - 如果总帧数更大,就按 stride 选帧,并且最多只保留 `max_frames` 帧。

### 综合发现
- 现象:
  - 从实现看,流程不是“直接对原视频逐帧一路跑到重建”。
- 结论:
  - 更准确地说,它是“先全量解码成帧,再对子帧集合做稀疏采样,最后只用采样后的帧进入 DA3 和后续重建”。
  - 只有在视频本身帧数不超过 `max_frames` 时,才会表现为近似逐帧全量处理。

## [2026-03-22 10:53:28] [Session ID: 1774147758-2955119] 笔记: 真实多视角数据的默认采样结果

### 来源

#### 来源1: output/flashvsr_reference_xhc_bai/preprocess_frames.json
- 要点:
  - 联合场景一共使用了 600 帧。
  - 6 个视角各自贡献 100 帧。
  - 合并后的全局帧区间依次是: view_0=[0,100), view_1=[100,200), view_2=[200,300), view_3=[300,400), view_4=[400,500), view_5=[500,600)。

#### 来源2: per_view/view_*/preprocess_frames.json + 原始解帧目录统计
- 要点:
  - 每个视角的 `source_frames_dir` 中都有 121 帧。
  - 每个视角的 `frames_subsampled` 中都有 100 帧。
  - 每个视角的 `actual_stride` 都是 1,不是 8。

#### 来源3: 对 `frames_subsampled` 与 `frames` 做文件内容比对
- 要点:
  - 每个视角的 100 张 `frames_subsampled` 都能一一匹配回原始 `frames`。
  - 匹配结果显示,它们正好对应原始的前 100 帧,也就是 `000001.png` 到 `000100.png`。
  - 未进入后续 DA3 的尾部帧是 `000101.png` 到 `000121.png`,共 21 帧。

### 综合发现
- 现象:
  - 这份真实数据里,每个视角原始视频解出了 121 帧,但后续只用了 100 帧。
- 代码解释:
  - 因为 `121 / 100 = 1.21 <= max_stride(8)`,所以 `subsample_frames()` 选择 `stride=1`。
  - 随后由于 `range(0, 121, 1)` 会产生 121 个索引,代码又把它截断成前 100 个。
- 已验证结论:
  - 这份多视角数据的默认采样不是“每隔 8 帧取一张”。
  - 实际上是“每个视角连续取前 100 帧,丢掉最后 21 帧”。

## [2026-03-22 11:15:40] [Session ID: 3515473] 笔记: Stage 1 lazy probe 已把 late-frame 显存台阶进一步收敛到帧内 inner refresh

### 来源

#### 来源1: `/tmp/video_to_world_flashvsr_reference_xhc_bai_stage1_probe_lazy_20260322_110034.log`
- 要点:
  - `frame 15~17` 的 `after_roma` 都维持在约 `0.89~0.90 GiB`。
  - `frame 18` 的 `after_roma` 直接跳到 `18.84 GiB`。
  - `frame 19` 的 `after_roma` 再跳到 `37.76 GiB`。
  - `frame 20` 在 `before_roma=37.76 GiB` 的基线上再次 OOM,报 `Tried to allocate 200.00 MiB`。

#### 来源2: `models/roma_matcher.py::compute_roma_matches_for_frame`
- 要点:
  - 当前函数在每 4 个新 pair 后会执行一次:
    - `del roma_matcher`
    - `gc.collect()`
    - `torch.cuda.empty_cache()`
    - `roma_matcher = RoMaMatcherWrapper(...)`
  - 也就是它会在**同一帧内部**重复重建 RoMaV2 模型。

#### 来源3: lazy probe 的 `frame 18` / `frame 19` 上下文日志
- 要点:
  - `frame 18` 的单帧 RoMa 段里出现了 5 次 `RoMa v2 initialized`。
  - `frame 19` 的单帧 RoMa 段里也出现了 5 次 `RoMa v2 initialized`。
  - 这些重复初始化恰好对应当前帧参考数达到 18/19,与 `refresh_every_n_new_pairs=4` 的节奏一致。

### 综合发现
- 现象:
  - 外层按帧懒创建后,跨帧常驻显存已经被明显压低。
  - 但当单帧内需要计算较多新 pair 时,帧内 refresh 逻辑会触发多次新模型初始化。
- 当前主假设:
  - 问题重点已经不再是“跨帧一直复用同一个 matcher”。
  - 更像是“同一帧里连续重建多个 RoMaV2 实例,而旧实例没有在下一次初始化前及时真正释放”,于是显存按模型份数阶梯式抬高。
- 最强备选解释:
  - 即使去掉帧内重复重建,单个 matcher 连续跑 18~20 个 pair 仍可能有新的单帧峰值问题。
  - 但当前证据已经足够支持先做这个最小修复,因为台阶跃迁和 repeated init 的对应关系非常直接。

## [2026-03-22 11:17:27] [Session ID: 1774147758-2955119] 笔记: 澄清 Stage 0 与 Stage 1 两层 stride 的叠加语义

### 待验证问题
- `--preprocess-max-frames 100 --preprocess-max-stride 2` 是否等于 Stage 0 一定产出 50 帧?
- `--config.alignment.stride 2` 是否会在 Stage 0 的结果上再次减半?
- Stage 1 里 `num_frames` 和 `stride` 是先后什么关系?

## [2026-03-22 11:32:10] [Session ID: 3515473] 笔记: 去掉 inner refresh 后,旧的多次初始化台阶问题消失,但单帧 20 个新 pair 仍会把常驻显存抬到 20GiB+

### 来源

#### 来源1: `/tmp/video_to_world_flashvsr_reference_xhc_bai_stage1_probe_innerfix_20260322_111920.log`
- 要点:
  - `frame 18` 的 `before_roma=0.90 GiB`, `after_roma=0.90 GiB`。
  - `frame 19` 的 `before_roma=0.90 GiB`, `after_roma=0.90 GiB`。
  - `frame 20` 的 `before_roma=0.91 GiB`, `after_roma=20.81 GiB`。
  - `frame 20` 结束后的 `after_empty_cache` 仍然是 `20.81 GiB`。
  - `frame 21` 的 `before_roma` 直接继承到 `20.81 GiB`,随后再次在 `refiner.py: z = z.float()` OOM。

#### 来源2: 同一份日志中的 `RoMa v2 initialized`
- 要点:
  - `frame 20` 段内只看到 1 次初始化,不再是上一轮 `frame 18/19` 那种单帧 5 次初始化。
  - 说明“帧内 repeated init 导致阶梯式爆涨”这一条已经被修掉。

#### 来源3: `output/flashvsr_reference_xhc_bai/roma_cache/matches_4c35997b503fcab5.pt`
- 要点:
  - 这轮 probe 启动时日志显示已加载 `190` 个 cached ROMA pair。
  - `190 = 1 + 2 + ... + 19`,正好意味着前 19 帧 pair 都已缓存。
  - 因此这轮里 `frame 18` / `frame 19` 实际主要是在吃缓存,而 `frame 20` 是第一个需要新算 `20` 个 pair 的帧。

### 综合发现
- 已验证结论:
  - 旧问题已经变化: 不再是“同一帧内 5 次重建模型后显存按模型份数上台阶”。
  - 新问题更像是“单个 matcher 在一个 uncached late-frame 内连续算约 20 个新 pair 后,会留下约 20 GiB 级别的 GPU 常驻状态,且当前帧结束时没有真正释放”。
- 当前主假设:
  - 泄漏主体已经缩到“单帧内 repeated `match_images()` 的累计状态”,而不是 repeated init。
  - 需要在 pair 粒度继续观察 `match_images()` 前后显存,并验证是否需要更强的 unload/offload 手段来打断单帧累计。
- 最强备选解释:
  - 也可能不是逻辑泄漏,而是 RoMaV2 在第 20 个新 pair 左右天然会产生过高峰值,并且 PyTorch allocator 不能及时回收到可复用状态。

## [2026-03-22 11:30:24] [Session ID: 1774147758-2955119] 笔记: 之前 Stage 1 ICP 运行的实际 stride 与取帧范围

### 来源

#### 来源1: `output/flashvsr_reference_xhc_bai/frame_to_model_icp_*/after_non_rigid_icp/config.json`
- 要点:
  - 当前输出目录下所有已落盘的 Stage 1 运行,`alignment.num_frames` 都是 50。
  - 当前输出目录下所有已落盘的 Stage 1 运行,`alignment.stride` 都是 2。
  - 当前输出目录下所有已落盘的 Stage 1 运行,`alignment.offset` 都是 0。

#### 来源2: `output/flashvsr_reference_xhc_bai/per_view/view_*/preprocess_frames.json`
- 要点:
  - 每个视角 Stage 0 的 `actual_stride` 都是 1。
  - 每个视角 Stage 0 都保留了前 100 帧。

#### 来源3: `output/flashvsr_reference_xhc_bai/preprocess_frames.json`
- 要点:
  - 联合序列按视角顺序拼接。
  - 全局区间是: view_0=[0,100), view_1=[100,200), ... view_5=[500,600)。

### 综合发现
- 已验证结论:
  - 之前所有已落盘的 ICP 运行,配置上的 Stage 1 stride 都是 2。
  - 由于 Stage 0 的实际 stride 是 1,所以对单个视角来说,这相当于从 Stage 0 保留下来的前 100 帧里每 2 帧取 1 帧。
- 推导结论:
  - 按当前联合序列的拼接方式和 `num_frames=50, stride=2, offset=0`,Stage 1 选中的全局索引是 0,2,4,...,98。
  - 这批索引全部落在 view_0 的全局区间 `[0,100)`,也就是只覆盖了第一个视角的 Stage 0 结果。

## [2026-03-22 11:37:30] [Session ID: 3515473] 笔记: isolated-worker probe 在用户怀疑已停止时,实际仍稳定推进到 frame 27

### 来源

#### 来源1: 进程复核命令
- 要点:
  - `pgrep -af 'frame_to_model_icp|run_reconstruction|train_gs|eval_gs'` 仍能看到当前 probe 的 `pixi` 进程与 Python 子进程。

#### 来源2: `/tmp/video_to_world_flashvsr_reference_xhc_bai_stage1_probe_isolated_20260322_114420.log`
- 要点:
  - `Frame 26` 已完整完成,并打印:
    - `after_empty_cache allocated=0.35 GiB reserved=0.38 GiB`
  - `Frame 27` 已开始,日志仍持续增长。
  - 到当前观察点仍未出现新的 `Traceback`。

### 综合发现
- 已验证结论:
  - 当前 probe 不是“已经停了”,而是仍在正常推进。
  - isolated worker 方案在 late-frame 区间至少已稳定推进到 `frame 27`,并且主进程显存仍保持低位。
- 当前主假设:
  - 只要后续帧的 late-frame 模式相近,这轮 probe 很有希望完整跑完 Stage 1。
- 最强备选解释:
  - 也不能只凭 `frame 27` 就宣布跑通,因为后半段仍可能在 ICP 或 RoMa worker 交互处暴露新失败点。

## [2026-03-22 11:38:57] [Session ID: 1774147758-2955119] 笔记: 在当前顺排联合序列上,全局 stride=6 的本地帧相位并不一致

### 来源
- 基于 `output/flashvsr_reference_xhc_bai/preprocess_frames.json` 的全局帧区间,对 `num_frames=100, stride=6, offset=0` 做索引分解。

### 已验证事实
- 全局采样确实会覆盖 6 个视角,分布约为 17/17/16/17/17/16。
- 但映射回各视角的本地帧号后,并不是每个视角都取相同的本地序列。
- 当前结果大致是:
  - view_0 取本地 `0,6,12,...,96`
  - view_1 取本地 `2,8,14,...,98`
  - view_2 取本地 `4,10,16,...,94`
  - 后续视角再重复这个相位模式

### 结论
- 这说明“在当前顺排联合序列上做全局 stride 采样”与“按相同时间步跨视角同步采样”不是同一件事。
- 如果目标是让 6 个镜头在相近时间点成组进入 ICP,更好的方案是交织排序或显式按 `(time_idx, view_id)` 采样。

## [2026-03-22 11:49:30] [Session ID: 3515473] 笔记: isolated-worker 版 Stage 1 probe 已完整跑通,late-frame 到 Frame 49 都维持低位显存

### 来源

#### 来源1: `/tmp/video_to_world_flashvsr_reference_xhc_bai_stage1_probe_isolated_20260322_114420.log`
- 要点:
  - 全程未发现 `Traceback` / `OutOfMemoryError` / `ERROR`。
  - 日志推进到 `Frames: 100%|...| 49/49`。
  - `Frame 44~49` 的 `before_roma` 约为 `0.37 GiB` 到 `1.06 GiB reserved`。
  - `Frame 44~49` 的 `after_empty_cache` 稳定回到 `allocated=0.37 GiB reserved=0.46 GiB`。

#### 来源2: `output/flashvsr_reference_xhc_bai/frame_to_model_icp_50_2_offset0_zzisolated_probe_20260322_114420/after_non_rigid_icp`
- 要点:
  - 已落盘完整 Stage 1 结果,包括 `aligned_points.ply`、`roma_match_history.pt`、全量 per-frame deform 文件等。

### 综合发现
- 已验证结论:
  - isolated worker 方案已经足够让当前这张卡完整跑完 extensive 所需的 Stage 1 配置。
  - 之前的 OOM 不是“这张卡绝对跑不动 Stage 1”,而是“原实现的进程内 RoMa GPU 状态累计把它拖死了”。
- 当前主假设:
  - 在复用这份成功的 Stage 1 结果后,正式 extensive 的下一个真实风险点将转移到 Stage 2 或 Stage 3 的训练/自动评估链路。
- 最强备选解释:
  - 即使 Stage 1 已跑通,后续 Stage 2/3 仍可能因为新的 GPU 峰值或自动 eval 逻辑暴露不同问题,需要继续按阶段验收。

## [2026-03-22 11:52:40] [Session ID: 3515473] 笔记: Stage 2 的 `torch_kdtree` 缺失属于可选加速依赖,可安全回退到 `cpu_kdtree`

### 来源

#### 来源1: `/tmp/video_to_world_flashvsr_reference_xhc_bai_extensive_stage23_resume_20260322_115020.log`
- 要点:
  - Stage 2 刚启动就在 `utils/knn.py -> from torch_kdtree import build_kd_tree` 处失败。
  - 栈顶是 `ModuleNotFoundError: No module named 'torch_kdtree'`。

#### 来源2: `configs/stage2_global_optimization.py`
- 要点:
  - `GlobalOptimizationConfig.knn_backend` 默认值是 `gpu_kdtree`。

#### 来源3: `algos/global_optimization.py` 与 `README.md`
- 要点:
  - 算法层默认是 `cpu_kdtree`。
  - README 把 `torch_kdtree` 描述成 optional GPU-accelerated KD-tree。

### 综合发现
- 已验证结论:
  - Stage 2 当前失败不是“这台机器不能跑 global optimization”。
  - 只是默认选中了一个未安装的可选 GPU KD-tree backend。
- 当前主假设:
  - 用 `--config.stage2.knn-backend cpu_kdtree` 重启后,Stage 2 应能继续推进。
- 最强备选解释:
  - 即使切到 CPU KD-tree 后能启动,后面仍可能在 Stage 2 的其他大张量或 Stage 3 训练阶段暴露新的资源瓶颈。

## [2026-03-22 11:53:58] [Session ID: 3515473] 笔记: 正式 extensive 已在 CPU KD-tree 方案下越过 Stage 2 并进入 Stage 3.1

### 来源

#### 来源1: 
- 要点:
  - Stage 2 从初始化成功推进到 。
  - 期间多次  重建均成功。
  - 后续日志已出现  与 , ,  等输出。

### 综合发现
- 已验证结论:
  - 对当前环境来说,Stage 2 用 CPU KD-tree 是有效可行路径。
  - 这条 extensive 运行已经不再卡在 Stage 2 初始化。
- 当前主假设:
  - 如果 Stage 3.1 训练显存和数据链路都稳定,后续会继续进入 GS 训练阶段。
- 最强备选解释:
  - 真正更重的风险可能会在 GS 训练或自动评估阶段再出现。

## [2026-03-22 11:57:10] [Session ID: 3515473] 笔记: 更正上一条被 shell 命令替换污染的记录,正式确认 extensive 已在 CPU KD-tree 方案下越过 Stage 2 并进入 Stage 3.1

### 说明
- 上一条 `2026-03-22 11:53:58` 的记录正文被 shell 命令替换污染,本条为正式更正版本。

### 来源

#### 来源1: `/tmp/video_to_world_flashvsr_reference_xhc_bai_extensive_stage23_cpu_kdtree_20260322_115240.log`
- 要点:
  - Stage 2 从初始化成功推进到 `iter=100+`。
  - 期间多次 `estimate_normals[cpu_kdtree]` 重建均成功。
  - 后续日志已出现 `Training:` 与 `Epoch 1/30`, `Epoch 2/30`, `Epoch 3/30` 等输出。

### 综合发现
- 已验证结论:
  - 对当前环境来说,Stage 2 用 CPU KD-tree 是有效可行路径。
  - 这条 extensive 运行已经不再卡在 Stage 2 初始化。
- 当前主假设:
  - 如果 Stage 3.1 训练显存和数据链路都稳定,后续会继续进入 GS 训练阶段。
- 最强备选解释:
  - 真正更重的风险可能会在 GS 训练或自动评估阶段再出现。
