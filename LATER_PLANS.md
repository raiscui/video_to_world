# 后续计划

## [2026-03-20 21:54:01] [Session ID: codex-20260320-203623] 主题: 多视角联合重建的后续方向

### 备忘
- 当前新增的是“多视角批处理入口”,不是“多视角联合重建单一 canonical scene”。
- 如果后续需要把 `0..5` 六个视频真的融合成一个统一场景,需要继续改造:
  - `preprocess` 层如何组织多个 `results.npz`
  - `data_loading` 层如何读取多视角/多序列输入
  - Stage 1 对齐如何跨视频建立 correspondence
  - Stage 2/3 如何共享 canonical space 与训练数据

## [2026-03-20 22:54:43] [Session ID: codex-20260320-203623] 主题: 上一条后续方向已部分落地

### 说明
- 上一条关于“联合单场景输入”的需求,本轮已经落地到 Stage 0 联合预处理与单场景入口。
- 目前剩余的真正二期内容是:
  - 是否要做更强的跨视角 frame ordering / reference selection
  - 是否要为联合场景提供专门的 eval transforms 组织方式
  - 是否要在 Stage 1/2 中显式利用 per-view 分组信息提升稳定性

## [2026-03-20 23:09:40] [Session ID: codex-20260320-230940] 主题: 联合入口还需要一次真实非 dry-run 验证

### 备忘
- 当前已完成并证实的是:
  - `pixi` 环境能启动
  - 单元测试通过
  - 真实 `0..5` 目录能成功 dry-run
- 仍值得后续补做的一次验证是:
  - 在第三方依赖、模型权重和 GPU 条件都准备好的机器上,真实执行一次:
    - `pixi run python run_multiview_reconstruction.py --views-root source/flashvsr_reference_xhc_bai/full_scale2x --scene-root <joint_scene> --config.mode fast`
- 这一步主要是验证:
  - per-view `results.npz` 在真实输出下能否稳定 merge
  - 联合后的 `frames_subsampled` 与 `results.npz` 帧数是否严格一致
  - Stage 1 对联合后帧序列的实际稳定性
## [2026-03-21 22:12:38] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 主题: 为测试运行提供正式的“去外部大权重下载”模式

### 备忘
- 当前测试跑要手动组合两类参数才能避开外部下载阻塞:
  - `--config.stage1.roma.no-use-roma-matching`
  - `train_gs` 或 `run_reconstruction.py --config.gs.lpips-weight 0`
- 后续值得考虑提供一个更正式的 smoke-test / quick-test 预设,把以下选择集中起来:
  - 关闭 RoMa matching
  - 关闭 LPIPS
  - 缩短 GS `num_iters`
  - 可选关闭自动 eval

## [2026-03-22 12:16:10] [Session ID: eab9d6c3-318b-4c00-96b4-b400f09605f6] 主题: multiview 入口应在 Stage 0 之前预校验透传参数

### 备忘
- 当前 `run_multiview_reconstruction.py` 会先完成昂贵的 Stage 0,然后才在调用 `run_reconstruction.py` 时暴露透传参数名错误。
- 值得后续补一个更早失败的机制,例如:
  - 启动前对透传参数做 `run_reconstruction.py --help` 级别的校验。
  - 或增加兼容 alias,把旧的 `--config.alignment.*` 映射到 `--config.stage1.alignment.*`。
- 这样可以避免“Stage 0 成功后才发现 CLI 写错”的高成本失败。
