# 工作记录

## [2026-03-20 20:36:23] [Session ID: codex-20260320-203623] 任务名称: 使用 pixi 代替 conda 管理环境依赖

### 任务内容
- 新增 `pixi.toml`,为仓库建立 `pixi` 环境清单与安装任务。
- 更新 `README.md`,把环境准备说明切换到 `pixi` 工作流。
- 更新 `AGENTS.md`,把开发与检查命令统一为 `pixi run ...`。
- 更新 `models/roma_matcher.py`,让缺依赖报错提示与新的环境入口保持一致。
- 更新 `.gitignore`,忽略 `.pixi/` 目录。

### 完成过程
- 先读取仓库现有环境说明,确认只有 README 使用了 `conda`,代码本身没有直接耦合 `conda`。
- 使用本机 `pixi 0.65.0` 做临时工程实验,验证了 `pypi-dependencies`、editable path 和 task 依赖写法。
- 采用“基础依赖进 manifest,重型源码/编译依赖进 task”的方案,避免首次 clone 时被 `third_party/` path 依赖卡住。
- 用 `pixi task list` 做静态验证,再用受限时长的 `pixi install` 做动态探针验证。

### 总结感悟
- 对这种混合了 PyPI、git 源码、补丁和本地 editable 包的研究仓库,`pixi + task` 比“把所有东西都塞进 manifest”更稳。
- 文档迁移时,不要只改 README,还要顺手清掉运行时报错里的旧安装提示,否则用户体验会撕裂。

## [2026-03-20 21:54:01] [Session ID: codex-20260320-203623] 任务名称: 为 0..5 目录结构增加多视角批处理流程

### 任务内容
- 为 `source/flashvsr_reference_xhc_bai/full_scale2x/0..5/rgb/*.mp4` 这类目录新增统一批处理入口。
- 保持现有单视频重建流程不变,通过新的 orchestrator 做批量调度。
- 为新增流程补充文档、规格图和单元测试。

### 完成过程
- 先读取真实目录和 manifest,确认 `0..5` 是同一 `scene_stem` 的不同视角。
- 再核对现有代码的数据入口,确认下游阶段都严格依赖单个 `root_path/results.npz`。
- 因此实现了 `run_multiview_reconstruction.py`,采用“每个视角单独 scene_root + 批量调度”的方式落地。
- 补充了 `tests/test_run_multiview_reconstruction.py`,并用真实目录做了 `/tmp` 落点的 dry-run 验证。
- 同时新增 `specs/multiview_batch_pipeline.md`,并用 `beautiful-mermaid-rs` 验证图表语法。

### 总结感悟
- 当底层算法天然是单输入模型时,先补 orchestrator 往往比强行改底层更稳,也更容易验证。
- 对你现在这套 `0..5` 目录,批处理入口已经能直接提供可执行流程。

## [2026-03-20 22:54:43] [Session ID: codex-20260320-203623] 任务名称: 把多镜头视频改为联合单场景输入

### 任务内容
- 将错误的“多视角批处理”方向回滚。
- 改造成“多个视频联合进入同一 scene_root”的单场景流程。

### 完成过程
- 先承认上一假设不成立,依据是用户明确指出“这是一个场景”。
- 新增 `preprocess_multiview.py`,采用“每视角独立 DA3 -> 联合合并 results.npz”的策略。
- 重写 `run_multiview_reconstruction.py`,让它只跑一次联合预处理和一次单场景重建。
- 补充并更新了测试、规格图和 README 说明。
- 用真实目录 `source/flashvsr_reference_xhc_bai/full_scale2x` 做了 dry-run,确认命令结构已切到联合版。

### 总结感悟
- “多视频”不等于“多任务批处理”,关键要先分清用户要的是“多个结果”还是“一个联合结果”。
- 对现有单 `results.npz` 下游来说,最务实的联合方案是先在 Stage 0 合并输入,再尽量复用后面的阶段。

## [2026-03-20 21:59:46] [Session ID: codex-20260320-215510] 任务名称: 修复 Pixi 多行 shell task 解析失败

### 任务内容
- 修复 `pixi.toml` 中 `setup-depth-anything-3` 的运行期解析错误。
- 顺手修复同类结构的 `setup-romav2` 与 `install-torch-kdtree`,避免主入口 `setup` 后续继续失败。

### 完成过程
- 先读取 `pixi.toml`,确认出错任务是多行字符串形式的 shell task。
- 用最小临时工程分别验证了:
  - 多行 `if ... then ... fi` 会在 `pixi run` 时触发 `Unsupported reserved word`
  - `cmd = ["bash", "-lc", """..."""]` 可以稳定执行同一段脚本
- 将仓库里的三处复杂任务统一改为显式调用 `bash -lc`,并加上 `set -euo pipefail`。
- 在仓库内重新执行 `pixi task list` 和相关 dry-run,随后真实执行 `setup-depth-anything-3` 验证错误类型已从“解析失败”切换为“GitHub 网络连接失败”。

### 总结感悟
- Pixi 的 task 能跑 shell 命令,不等于能跑完整 bash 语法。复杂脚本一定要显式交给真正的 shell。
- 调试配置问题时,看到错误类型发生层级切换,就是很重要的动态证据。它能帮助我们确认“上一层已经修好”,避免继续误修。

## [2026-03-20 23:07:10] [Session ID: codex-20260320-225624] 任务名称: 修复 gsplat 安装阶段的 TLS 连接失败

### 任务内容
- 定位 `install-gsplat` 在 `pip` 拉取 GitHub 仓库时的 TLS EOF 错误。
- 修复 GitHub 相关 Pixi 任务在坏 loopback 代理环境下的安装失败。

### 完成过程
- 先对比了“当前代理环境”和“手动去掉代理”两种情况下的 `git ls-remote` 行为。
- 证据表明 GitHub 直连本身可用,失败来自 shell 中残留的 `127.0.0.1:7897/7897` 代理变量。
- 新增了 `scripts/pixi_task_helpers.sh`,专门清理失效的 loopback 代理变量。
- 将 `install-gsplat` 改成显式 clone 到 `third_party/gsplat`,然后 checkout 官方 `v1.5.3` 对应 commit,再从本地路径安装。
- 同步让其他 GitHub 任务也复用了这个 helper,避免后续 setup 继续被同类问题击穿。
- 补充了 `tests/test_pixi_manifest.py`,防止 manifest 结构回退。

### 总结感悟
- 网络类错误最容易把人带偏。先做“同一命令,只改环境变量”的最小实验,能非常快地看出到底是网络、代理还是命令本身的问题。
- 对 GitHub 依赖较重的项目,把“坏 loopback 代理自动旁路”收进任务层,比让每次执行都靠人工记忆环境变量稳得多。

## [2026-03-21 00:29:11] [Session ID: codex-20260321-002404] 任务名称: 让 DepthAnything-3 setup 优先复用本地 commit / 本地镜像

### 任务内容
- 修复 `setup-depth-anything-3` 即使本地已满足条件仍无条件远程 `fetch` 的问题。
- 把用户提供的 `/workspace/depth-anything-3` 接入为正式本地镜像兜底。

### 完成过程
- 先核对了两个本地仓库:
  - `/workspace/depth-anything-3`
  - `third_party/depth-anything-3`
- 两边都确认已有目标 commit `2c21ea...`,因此判断原先的远程 fetch 是不必要的。
- 第一版尝试把新的分支逻辑直接写回 `pixi.toml`,随后被运行期新证据推翻:
  - Pixi 会在 task 字符串里预展开 `$target_commit` 这类局部变量
- 于是改成新增独立脚本 `scripts/setup_depth_anything_3.sh`,把复杂逻辑交回真正的 bash 执行。
- 再用真实任务 `pixi run setup-depth-anything-3` 验证,确认已命中本地 commit 路径并安装成功。

### 总结感悟
- “把脚本塞进 task 字符串里”一开始看着方便,但一旦需要局部变量、条件分支和路径推导,独立脚本会稳很多。
- 新证据推翻旧修法时,尽快承认并切换路径,比围着原实现继续叠转义和补丁更省时间。

## [2026-03-20 23:09:40] [Session ID: codex-20260320-230940] 任务名称: 补齐联合多视角入口的动态验证与交付证据

### 任务内容
- 复查 `preprocess_multiview.py` 和 `run_multiview_reconstruction.py` 是否仍保持“单场景联合输入”的语义。
- 在 `pixi` 环境下重新验证测试和真实目录 dry-run。
- 把当前会话的新证据补写回上下文文件,避免只靠上一轮记录口头继承结论。

### 完成过程
- 先读取六文件上下文和当前仓库状态,确认上一轮已经完成联合入口代码改造。
- 重新检查联合入口相关文件,确认 `run_multiview_reconstruction.py` 现在只会调一次 `run_reconstruction.py --config.root-path <scene_root>`。
- 运行 `timeout 60s pixi run python --version`,确认 `pixi` 环境现在已能直接起 Python。
- 运行 `timeout 60s pixi run python -m unittest discover -s tests`,确认 6 个测试全部通过。
- 使用真实目录 `source/flashvsr_reference_xhc_bai/full_scale2x` 分别执行联合主入口 dry-run 和联合预处理 dry-run,并检查 `/tmp/video_to_world_joint_scene/multiview_reconstruction_summary.json`。

### 总结感悟
- 对这种“上一轮已经改完,但当前会话要继续负责”的任务,最重要的不是重复造轮子,而是补上新的动态证据,确认代码和现实状态还一致。
- 这次最有价值的新事实是: `pixi` 默认环境已经能直接执行仓库 Python 命令,联合多视角入口的验证链条比上一轮更完整了。

## [2026-03-20 23:47:52] [Session ID: codex-20260320-234752] 任务名称: 新增联合多视角使用命令文档

### 任务内容
- 根据当前联合多视角入口,新增一份“怎么实际使用”的命令文档。
- 将文档落到 `docs/cmd.md`。

### 完成过程
- 先检查仓库,确认此前没有 `docs/` 目录,也没有现成的 `docs/cmd.md`。
- 结合 `run_multiview_reconstruction.py`、`preprocess_multiview.py` 和已验证过的真实命令,整理出最常用的几类命令。
- 新建 `docs/cmd.md`,写入环境准备、dry-run、真实运行、部分视角、单独联合预处理和输出目录说明。
- 再用两个 `--help` 命令回头校对参数名,避免文档写错入口参数。

### 总结感悟
- 使用文档最重要的是“拿来就能跑”,所以直接围绕真实目录和真实命令写,比抽象介绍更有用。
- 对命令文档做一次 `--help` 反查很值,能避免文档和代码慢慢漂移。

## [2026-03-21 12:48:58] [Session ID: codex-20260321-123719] 任务名称: 修复 gsplat 安装阶段的坏 glm 子模块报错链路

### 任务内容
- 定位 `gsplat` wheel 构建失败的真实首个错误。
- 修复 `install-gsplat` 在 `glm` 子模块损坏时只暴露晚期 `ninja` 编译报错的问题。

### 完成过程
- 先重新抓取 `pip install -v --no-build-isolation --no-deps third_party/gsplat` 的完整输出,确认首个失败点是 `glm/gtc/type_ptr.hpp` 缺失。
- 再检查本地 `third_party/gsplat` 的子模块状态,发现 `glm` 目录里只有 `.git`,进入子模块后 `HEAD` 不可验证,属于损坏 checkout。
- 将 `install-gsplat` 抽成独立脚本 `scripts/install_gsplat.sh`,补上 pinned commit 复用、坏子模块清理重建和头文件预检。
- 新增行为级回归测试 `tests/test_install_gsplat_script.py`,用假命令包装器模拟“坏子模块修复成功”和“修复后仍缺头文件”两条路径。
- 最后用 shell 语法检查、单元测试、`pixi task list` 和真实仓库短探针完成收尾验证。

### 总结感悟
- `git submodule status` 看起来正常,不代表子模块工作树真的可用。对会参与编译的子模块,最好直接验证关键头文件或源码文件是否存在。
- 安装脚本里最值钱的不是“自动重试”,而是把错误停在正确层级。比起让用户只看到 `ninja` 崩掉,提前指出“glm 子模块不完整”更能节省排障时间。

## [2026-03-21 14:45:13] [Session ID: codex-20260321-123719] 任务名称: 让 gsplat 在 glm 子模块超时时复用本地头文件成功安装

### 任务内容
- 处理用户在真实执行 `pixi run install-gsplat` 时遇到的 `glm` 子模块初始化超时。
- 将修复从“提前暴露错误”进一步推进到“在当前机器上真实安装成功”。

### 完成过程
- 先验证 `g-truc/glm` 的 GitHub 访问仍会超时,确认这不是单纯把 timeout 调大就能稳过的场景。
- 再搜本机现成的 `glm` 副本,找到多个可复用路径。
- 在 `scripts/install_gsplat.sh` 中增加本地 `glm` 搜索和 `GSPLAT_GLM_LOCAL_DIR` 覆盖入口。
- 让脚本在 `glm` 头文件缺失时,优先复制本地 `glm/` 头文件树,而不是死等子模块 clone。
- 重新跑真实 `pixi run install-gsplat`,确认当前机器已经完整装成 `gsplat 1.5.3`。

### 总结感悟
- Header-only 依赖如果已经在本机其他工作区存在,完全可以把它视为“本地缓存层”,不必每次都硬依赖上游仓库实时可达。
- 这次最关键的不是“又加了一个 fallback”,而是先用证据确认上游访问真的不稳,再把 fallback 放到最有价值的地方。

## [2026-03-21 14:59:14] [Session ID: codex-20260321-123719] 任务名称: continuous-learning 沉淀 gsplat / glm 安装经验

### 任务内容
- 从六文件里提炼这次 `gsplat` 与 `glm` 子模块排障的可复用知识。
- 将适合长期保留的内容分流到项目文档与新的 `self-learning.*` skill。

### 完成过程
- 先回读默认六文件,确认本轮没有支线后缀上下文集,也没有需要归档的历史版本文件。
- 检查项目内 `README.md`、`AGENTS.md`、`docs/cmd.md`、`specs/multiview_joint_pipeline.md`,确认真正需要同步的是环境安装说明,不是多视角文档。
- 检索现有 `self-learning.*` skills,确认目前没有覆盖 `gsplat` 的 `glm` 子模块缺失 / 超时问题。
- 于是同步更新项目文档,并新增一个专门记录该模式的 `self-learning.*` skill。

### 总结感悟
- 持续学习最有价值的地方,不是“多写一个文件”,而是把知识分到真正会被未来人看到的位置。
- 这次最适合沉淀的内容,一半是 repo-specific 的 README / AGENTS 约定,另一半是跨项目可复用的 `gsplat + glm` 排障 skill。

## [2026-03-22 00:21:00] [Session ID: codex-20260321-234700] 任务名称: 修复 tiny-cuda-nn 在 pixi 混合 CUDA 环境下的构建与链接失败

### 任务内容
- 继续接手 `pixi run setup` 的真实剩余阻塞,把 tiny-cuda-nn 的本地编译失败彻底打通。
- 让 `install-tinycudann` 不再依赖手工导出 CUDA / NVIDIA 路径。
- 用 fresh verification 证明整条 `pixi run setup` 已恢复可用。

### 完成过程
- 先续档了超长的 `task_plan.md`,避免当前会话继续把计划文件写到失控。
- 通过静态探针确认:
  - `nvcc` 确实存在于 `/usr/local/cuda/bin`
  - `nvrtc.h`、`cusparse.h`、`cublas_v2.h` 实际来自 `.pixi/envs/default/lib/python3.10/site-packages/nvidia/*/include`
  - 对应共享库也来自 `site-packages/nvidia/*/lib`
- 再做两轮最小动态实验:
  - 第一轮只补 `nvrtc` / `cusparse` 路径,把错误推进到 `cublas_v2.h`
  - 第二轮补齐全部 `nvidia/*/include` 后,把错误推进到链接阶段 `-lnvrtc`
- 最终在 `scripts/install_tinycudann.sh` 中实现:
  - 自动收集所有 NVIDIA wheel 的 include/lib 路径
  - 自动生成 `libfoo.so -> libfoo.so.12` 临时链接别名
  - 自动注入 `LDFLAGS` 的 `-L` 和 `rpath`
- 最后跑完:
  - `bash -n scripts/install_tinycudann.sh`
  - `python3 -m unittest tests/test_pixi_manifest.py`
  - `pixi run install-tinycudann`
  - `pixi run setup`
  - `pixi run python` 导入 `tinycudann`

### 总结感悟
- 对 PyTorch CUDA 扩展来说,“机器上有 nvcc”不等于“构建环境完整”。
- 当 CUDA 来自系统,而开发头和库来自 PyPI NVIDIA wheels 时,问题往往不在编译选项本身,而在 include / link / rpath 这三层路径拼接。
## [2026-03-21 22:12:38] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 任务名称: 继续 `source/flashvsr_reference_xhc_bai` 的真实测试运行并打通后半程

### 任务内容
- 复用已经完成的联合 Stage 0 结果,继续推进 `source/flashvsr_reference_xhc_bai/full_scale2x` 的真实测试运行。
- 绕开新的外部大文件下载阻塞,把 Stage 1、Stage 3.1 和 Stage 3.2 的测试路径真实跑起来。

### 完成过程
- 先复核 `run_reconstruction.py` 的正式参数,确认可以使用 `--config.stage1.roma.no-use-roma-matching` 和新的 `stage1.out_suffix`。
- 然后基于 `/tmp/video_to_world_joint_scene_xhc_bai_fast_run_local_da3_20260321_2142` 重跑后半程,成功产出新的 Stage 1 目录 `frame_to_model_icp_50_2_offset0_nroma_20260321_2201`。
- 观察到 Stage 3.1 已顺利完成,并生成 `inverse_deformation` 与 round-trip validation 结果。
- 之后发现 Stage 3.2 会被 LPIPS 触发的 VGG16 下载拖住,于是停止长时间下载,改为直接调用 `train_gs`。
- 最终使用独立输出目录 `gs_3dgs_lpips0_test_20260321_2210`,以 `lpips_weight=0`、`num_iters=100` 完成一轮短程 3DGS 真实训练。
- 验证得到:
  - `checkpoint_000099.pt`
  - `model_final.pt`
  - `eval_000099/`
  - `splats_3dgs.ply`

### 总结感悟
- 对“先跑通测试链路”这类任务,把外部大权重下载从主路径上摘掉,往往比盲等更有价值。
- 这次最关键的不是单纯“降配”,而是先用真实运行证明 Stage 0/1/3.1 已经可靠,再有针对性地把 Stage 3.2 改成可验证的短程路径。

## [2026-03-22 00:16:43] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 任务名称: 继续 `source/flashvsr_reference_xhc_bai` 的默认后半程测试运行并修复真实阻塞

### 任务内容
- 基于已经跑通的默认 RoMa Stage 1 结果,继续验证默认后半程。
- 处理运行中真实暴露的 GS 配置覆盖问题与 auto eval 问题。
- 让 `run_reconstruction.py` 的入口级 smoke 能无 error 收尾。

### 完成过程
- 先真实执行 `run_reconstruction.py --config.skip-alignment`,确认 Stage 2 inverse deformation 和 round-trip validation 都能正常完成,默认 LPIPS 的 GS 训练也确实能启动。
- 然后发现 `--config.gs.num-iters 150` 没生效,通过 dry-run + 静态读码确认是 `run_reconstruction.py` 的 mode preset 把用户显式覆盖写回了 10000。
- 接着修复 `run_reconstruction.py`,新增 `tests/test_run_reconstruction.py`,并用 dry-run 证明最终下发命令已变成 `--config.num-iters 150`。
- 再做 150 iter 的真实 GS smoke,拿到了 checkpoint / model / ply 等落盘证据,同时暴露 `eval_gs` 对缺失 `gs_video` transforms 的硬依赖。
- 继续修复 `eval_gs` 的降级路径,新增 `tests/test_eval_gs.py`,并手动在真实 checkpoint 上跑通 `eval_gs`。
- 最后发现 `train_gs` 的 auto eval 会被父训练进程残留显存挤爆,于是补上 auto eval 前的显存释放。
- 重新执行 1 iter 的入口级 `run_reconstruction.py` smoke,确认训练保存、PLY 导出、自动评估和 pipeline 收尾都完成,日志中没有新的 error 标记。

### 总结感悟
- 对 GPU 管线来说, “主流程能训练” 和 “主流程末尾还能安全拉起 GPU 子流程” 是两件事, 两者都要单独验证。
- 配置预设如果要保留,必须明确区分“mode 默认值”和“用户显式覆盖值”, 否则入口参数看起来存在,实际上会被吞掉。
## [2026-03-22 00:25:40] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 任务名称: 说明 eval_gs 的 transforms 依赖与自动降级影响

### 任务内容
- 核对 `README.md`、`eval_gs.py`、`configs/eval_gs.py`、`data/data_loading.py`、`preprocess_video.py`、DA3 导出补丁与第三方导出实现。
- 解释 `gs_video/0000_extend_transforms.json` 的定义、生成来源、命名规则与缺失时的运行语义。

### 完成过程
- 确认该文件是 DA3 `gs_video` 导出阶段同步写出的 NeRF-style transforms JSON,用于复现 flythrough 相机轨迹。
- 确认当前 `eval_gs` 缺少该文件时会自动关闭 `render_gs_video_path`,并继续渲染 `input_poses` / `optimised_poses`。
- 确认影响范围只在评估渲染覆盖,不影响 GS 训练本体与最终模型落盘。

### 总结感悟
- 这类“自动降级”要区分“避免流程失败”和“功能完全等价”,两者不是一回事。
- 对用户解释时必须明确分开“训练结果是否受影响”和“评估产物是否变少”这两个维度。
## [2026-03-22 01:26:11] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 任务名称: 补生成 `gs_video/0000_extend_transforms.json` 并验证可用于 `eval_gs`

### 任务内容
- 判断缺失的 `0000_extend_transforms.json` 是否可以从现有 scene 数据反推生成。
- 生成兼容 `eval_gs` 的 transforms 文件,并确认评估链路能直接使用。

### 完成过程
- 先阅读 DA3 的轨迹生成源码,确认 `extend` 真实逻辑是“插值 + 平滑 + 中段插入 wander / dolly_zoom”,而不是单纯 circular path。
- 再检查当前 `results.npz`,确认其中已有 600 帧 `extrinsics` / `intrinsics` 与渲染分辨率,足够重建轨迹。
- 然后用一段临时 Python 脚本复用 DA3 的轨迹辅助函数,在 `/tmp/.../gs_video/0000_extend_transforms.json` 写出 722 帧的 NeRF-style transforms。
- 最后先用 `load_nerf_transforms_json()` 成功载入,再让 `eval_gs` 只跑 `gs_video` 前 3 帧 smoke,成功生成 `render_gs_video.mp4`。

### 总结感悟
- 这次最关键的不是“手工造一个看起来像的轨迹”,而是尽量复用上游真实轨迹生成逻辑,把坐标系和插值规则保持一致。
- `extend` 和 `wander` 在视觉上可能都像“绕着场景动”,但语义不同。文件名缺的是 `extend`,就应该按 `extend` 补,不能凭印象用纯 circular path 替代。
## [2026-03-22 01:49:10] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 任务名称: 判断当前机器 GPU 显存是否不足以正式跑完整流程

### 任务内容
- 核对当前机器 GPU 规格。
- 回看 Stage 1 与 auto eval 的 OOM / 成功证据,判断是否能直接归因为“显存不够”。

### 完成过程
- 通过 `nvidia-smi` 确认本机为 `NVIDIA RTX 6000 Ada Generation`, 总显存 `49140 MiB`。
- 回看日志确认 `train_gs -> eval_gs` 的 OOM 是父训练进程未释放显存造成的跨进程竞争,不是单纯单进程容量不足。
- 回看 Stage 1 日志确认早期默认 RoMa OOM 也被继续定位为 matcher 生命周期 / 新算 pair 显存累积问题,后续默认 Stage 1 已真实跑通。
- 最终给出分层结论: 当前证据不足以说明“这台机器显存不够正式跑完整流程”,但也尚未完成默认 10000 iter 全量长跑的最终动态验收。

### 总结感悟
- GPU OOM 不能一看到就归因于“显存小”。很多时候,真正的问题是对象生命周期、跨进程显存竞争,或者局部实现的平方级中间张量。
- 回答“机器够不够”时,最好拆成“硬件上限是否低”和“当前代码路径是否把显存用对了”这两个问题分别说清楚。
## [2026-03-22 02:10:54] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 任务名称: 启动默认业务配置的 3DGS 正式长跑并挂上显存监控

### 任务内容
- 基于已经完成的默认 Stage 1 / Stage 2 产物,正式启动 `3dgs + 10000 iter + lpips_weight=0.2 + auto_eval=true` 的业务长跑。
- 同步记录 GPU 显存曲线,用于判断是否存在新的早期显存风险。

### 完成过程
- 先确认当前没有残留的 `train_gs` / `run_reconstruction` / `eval_gs` 相关进程占卡。
- 然后启动正式训练会话,输出目录为 `gs_3dgs_formal_full_20260322_020615`,训练日志写到 `/tmp/video_to_world_formal_gs_longrun_20260322_020615.log`。
- 同时启动独立 `nvidia-smi` 周期采样,把 GPU 利用率、显存占用和 compute app 写入 `/tmp/video_to_world_formal_gs_longrun_20260322_020604_gpu.log`。
- 首批观测显示训练已稳定推进到 200+ iter,显存稳定在约 28.37 GiB,未出现新的早期 OOM。

### 总结感悟
- 对这种长跑任务,最值钱的不是“先把命令敲出去”,而是同时把训练日志和 GPU 采样都挂上,这样后面任何异常都能对时定位。
- 当前首批动态证据进一步支持: 这台机器并不是一进入默认 GS 正式训练就因显存不足而失败。
## [2026-03-22 02:47:29] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 任务名称: 为 GS 正式 resume 能力建立 OpenSpec change

### 任务内容
- 在当前仓库中初始化 OpenSpec。
- 创建承载“GS 正式 resume 能力”的规范化 change。
- 获取第一份 artifact 模板,为后续 proposal 撰写做准备。

### 完成过程
- 先确认仓库尚未初始化 OpenSpec,因此先执行 `openspec init --tools codex .`。
- 再创建 change `add-gs-training-resume`,schema 为默认 `spec-driven`。
- 然后读取 change 状态,确认当前只有 `proposal` 处于 ready 状态。
- 最后获取 `proposal.md` 的 instructions / template,为下一步产出 proposal 做准备。

### 总结感悟
- 这一步最重要的是把“resume 能力”从口头需求变成规范化变更单,这样后面的 specs / design / tasks 才有依赖链。
- 当前仓库还没有 `openspec/specs/`,所以这次 change 也顺带完成了 OpenSpec 基础设施落地。
## [2026-03-22 04:04:35] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 任务名称: 使用 openspec-ff-change 完成 `add-gs-training-resume` 全套 artifacts

### 任务内容
- 将已经创建的 `add-gs-training-resume` change 一次性推进到 apply-ready。
- 按 spec-driven 顺序生成 proposal、specs、design、tasks。

### 完成过程
- 先读取当前 change 状态与各 artifact instructions,确认 proposal 是第一步。
- 再创建 `proposal.md`,明确 resume 的动机、能力边界和影响范围。
- 接着创建 `specs/gs-training-resume/spec.md` 与 `design.md`,把 resume 能力、checkpoint 结构和下游兼容策略写实。
- 最后创建 `tasks.md`,把实现拆成配置/检查点、训练流程、下游兼容、验证文档四组任务。
- 完成后执行 `openspec validate add-gs-training-resume`,确认 change 有效。

### 总结感悟
- 这次最关键的不是多写几个 Markdown 文件,而是把“resume 能力”从零散想法收敛成可实现、可验证、可拆任务的规范化变更。
- 由于 checkpoint 格式升级会波及 `eval_gs`、viewer、PLY 导出,在 design 阶段就把兼容性写进去,比实现时临时补锅稳得多。

## [2026-03-22 04:44:54] [Session ID: e7d33bb8-22af-4207-a9b3-224a0f3a3b4e] 任务名称: 启动 `source/flashvsr_reference_xhc_bai` 的 extensive 多视角正式运行并完成首批稳定性验收

### 任务内容
- 以多视角入口正式启动 `source/flashvsr_reference_xhc_bai/full_scale2x` 的 `extensive` 重建。
- 输出目录固定到 `output/flashvsr_reference_xhc_bai`。
- 同步挂载主运行日志与 GPU 采样日志,验证是否真正进入 extensive 主流程。

### 完成过程
- 先按项目六文件规则完成超长 `task_plan.md` 与 `notes.md` 的续档,并做最小持续学习摘要。
- 再使用带代理和 `HF_ENDPOINT=https://hf-mirror.com` 的环境启动:
  - `pixi run python run_multiview_reconstruction.py --views-root source/flashvsr_reference_xhc_bai/full_scale2x --scene-root output/flashvsr_reference_xhc_bai --config.mode extensive`
- 将主日志写到:
  - `/tmp/video_to_world_flashvsr_reference_xhc_bai_extensive_20260322_044004.log`
- 将 GPU 采样写到:
  - `/tmp/video_to_world_flashvsr_reference_xhc_bai_extensive_gpu_20260322_044004.log`
- 动态观察确认:
  - `view_0..view_5` 全部完成 DA3 preprocessing
  - 联合 `results.npz` 已写出
  - 管线已进入 `run_reconstruction.py` 的 `Stage 1: Iterative Alignment`
  - `Back-projecting frames 600/600` 已完成
  - Stage 1 GPU 实算期间显存已观测到约 `22 GiB`,暂未见 OOM 或 `Traceback`

### 总结感悟
- 对这类超长管线,真正有价值的不是“把命令敲出去”,而是同时拿到主日志、输出目录快照和 GPU 采样三份证据。
- 这次动态证据已经说明 extensive 入口选择和输出目录设置是对的,当前风险已从“能不能启动”切换到“后续长跑会不会在中后段暴露新阻塞”。

## [2026-03-22 10:50:28] [Session ID: 1774147758-2955119] 任务名称: 说明 run_multiview_reconstruction 的视频帧采样语义

### 任务内容
- 核对多视角入口在视频源输入下,是否对视频逐帧全量处理。
- 确认真实控制采样的脚本、参数和默认值。

### 完成过程
- 先读取 `run_multiview_reconstruction.py`,确认它只负责编排,不会自己解视频。
- 再读取 `preprocess_multiview.py`,确认它会对每个视角独立调用 `preprocess_video.py`。
- 最后读取 `preprocess_video.py`,确认流程是“ffmpeg 全量解帧 -> subsample_frames 选帧 -> 仅对 frames_subsampled 跑 DA3”。

### 总结感悟
- 这个入口的“采样”发生在预处理阶段,不是发生在后续重建阶段。
- 回答这类问题时,要区分“视频是否先被逐帧解码”与“后续算法是否逐帧全量消费”这两个不同层面。

## [2026-03-22 10:53:58] [Session ID: 1774147758-2955119] 任务名称: 核对 flashvsr 多视角数据的默认采样实际取帧

### 任务内容
- 对真实数据 `source/flashvsr_reference_xhc_bai/full_scale2x` 核对默认采样到底选中了哪些帧。
- 给出每个视角的实际用帧数量、stride 和尾部被丢弃的范围。

### 完成过程
- 读取 `output/flashvsr_reference_xhc_bai/preprocess_frames.json` 与各视角 `per_view/view_*/preprocess_frames.json`。
- 统计每个视角 `frames/` 与 `frames_subsampled/` 的真实文件数量,确认每个视角都是 121 -> 100。
- 再对 `frames_subsampled` 和原始 `frames` 做哈希匹配,确认 `frames_subsampled/000000..000099` 实际对应原始 `frames/000001..000100`。

### 总结感悟
- `max_stride=8` 在这份数据上并没有生效成“每 8 帧取 1 帧”。
- 真正发生的是: 先判定可以用 stride=1,然后再被 `max_frames=100` 截断成前 100 帧。

## [2026-03-22 11:09:20] [Session ID: 1774147758-2955119] 任务名称: 在 docs/cmd.md 补充 stride 设置命令

### 任务内容
- 在命令手册里加入 Stage 0 视频预处理 stride 的设置方法。
- 给出多视角入口、联合预处理、单视频预处理三种可直接复制的命令。

### 完成过程
- 先读取 `docs/cmd.md` 当前内容与 `README.md` 的相关段落。
- 再核对 `run_multiview_reconstruction.py`、`preprocess_multiview.py`、`preprocess_video.py` 的真实参数名。
- 然后在 `docs/cmd.md` 中新增小节,补上命令示例和参数区别,并补充 Stage 1 stride 的区分说明。

### 总结感悟
- 文档里只给参数名不够,必须把“入口不同,参数名不同”写清楚,否则用户很容易把 `--preprocess-max-stride` 和 `--config.alignment.stride` 混在一起。
- 这次还顺手把 `max_stride` 不是“固定隔帧”的语义写进去了,能减少后续误判。

## [2026-03-22 12:01:40] [Session ID: 3515473] 任务名称: 推动 `source/flashvsr_reference_xhc_bai` 的正式 extensive 运行越过 Stage 3.1 并进入 2DGS 训练

### 任务内容
- 继续推进 `output/flashvsr_reference_xhc_bai` 的正式 extensive 管线。
- 不降低 Stage 1 质量,复用已验收成功的 Stage 1 结果继续跑 Stage 2/3。
- 在遇到新阻塞时,只处理新的真实阻塞点,不回退到已修掉的旧 OOM 问题。

### 完成过程
- 先复核并确认 isolated-worker 版 Stage 1 probe 已完整跑通到 `Frame 49/49`。
- 再复用该 Stage 1 输出,用 `--config.skip-alignment --config.alignment-run ...` 正式切入 Stage 2/3。
- Stage 2 首次因缺少 optional 的 `torch_kdtree` 失败后,确认 `gpu_kdtree` 只是默认加速后端,随即切到 `cpu_kdtree` 继续。
- 重新启动后,Stage 2 global optimization 成功推进并完成。
- 随后 Stage 3.1 inverse deformation 完成训练与 round-trip validation。
- 当前已正式进入 `Stage 3.2: 2DGS Training`。

### 总结感悟
- 当前这台机器并不是“显卡绝对不够跑 extensive”。
- 真实结论是: Stage 1 之前被 RoMa 单进程 GPU 状态累计拖死; Stage 2 之前被 optional GPU KD-tree 依赖阻塞。
- 这两处分别修正后,正式 extensive 已经能推进到 GS 长跑阶段。
