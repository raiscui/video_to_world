# 任务计划: 继续调通 pixi run setup

## [2026-03-21 23:47:00] [Session ID: codex-20260321-234700] [记录类型]: 续档后接手 tiny-cuda-nn 的 CUDA 编译问题

### 背景承接
- 旧任务计划已续档到 `task_plan_2026-03-21_234700.md`,避免继续在超长文件里追加导致上下文失控。
- 前一轮已验证:
  - `pixi run setup` 前面的 `install-torch-stack`、`setup-depth-anything-3`、`install-gsplat`、`pin-build-setuptools` 已通过。
  - 当前真实阻塞收敛到 `install-tinycudann` 的本地编译阶段。
  - tiny-cuda-nn 已经不再卡在 GitHub 拉取或子模块获取,而是暴露出 CUDA 工具链环境问题。

### 目标
- 找出 tiny-cuda-nn 当前编译失败时缺失的 CUDA 环境暴露点。
- 修复 `scripts/install_tinycudann.sh`,让 `pixi run install-tinycudann` 能正确识别 CUDA 并继续构建。
- 继续验证 `pixi run setup`,直到通过或收敛出新的真实阻塞点。

### 现象
- 已观察到的真实报错包括:
  - `sh: 1: nvcc: not found`
  - `#error C++17 or later compatible compiler is required to use PyTorch`
  - `fatal error: nvrtc.h: No such file or directory`
  - `fatal error: cusparse.h: No such file or directory`
- 同一轮构建日志里后续又出现了 `/usr/local/cuda/bin/nvcc`,这说明机器上大概率已有 CUDA,只是没有被 tiny-cuda-nn 的构建探测链路稳定识别。

### 主假设
- 当前主假设是:
  - CUDA toolkit 已安装,但 `PATH`、`CUDA_HOME`、头文件搜索路径没有在 tiny-cuda-nn 的构建入口前正确导出。

### 最强备选解释
- 也可能不是单纯的环境变量暴露问题,而是当前 CUDA 安装布局与 tiny-cuda-nn / torch 的 include 约定不一致,需要额外补 `CPATH`、`CPLUS_INCLUDE_PATH` 甚至库路径。

### 最小验证计划
- 先只验证 4 件事:
  - `nvcc` 实际在哪里
  - `nvrtc.h` 实际在哪里
  - `cusparse.h` 实际在哪里
  - `/usr/local/cuda` 是否只是符号链接,真实 include 目录是否在 `targets/x86_64-linux/include`
- 只有确认这些落点后,才对脚本做最小补丁。

### 阶段
- [x] 阶段1: 承接旧上下文并续档超长任务计划
- [ ] 阶段2: 验证本机 CUDA 的二进制与头文件布局
- [ ] 阶段3: 修补 tiny-cuda-nn 安装脚本的 CUDA 环境导出
- [ ] 阶段4: 运行脚本级、任务级和 setup 级验证

### 状态
**目前在阶段2** - 正在用最小探针确认 `nvcc`、`nvrtc.h`、`cusparse.h` 的真实路径,避免对 CUDA 布局拍脑袋。

## [2026-03-21 23:53:00] [Session ID: codex-20260321-234700] [记录类型]: CUDA 布局验证完成,转入动态环境注入实验

### 新证据
- `nvcc` 实际存在于:
  - `/usr/local/cuda/bin/nvcc`
  - `/usr/local/cuda-12.4/bin/nvcc`
- 当前 shell 的 `PATH` 不包含 `/usr/local/cuda/bin`,因此 `command -v nvcc` 为空。
- `torch.utils.cpp_extension.CUDA_HOME` 在 `pixi` 环境中返回 `/usr/local/cuda`。
- 系统 CUDA include 目录下只有基础 runtime 头,未发现 `nvrtc.h` / `cusparse.h`。
- `nvrtc.h` 与 `cusparse.h` 实际位于 `pixi` 环境:
  - `site-packages/nvidia/cuda_nvrtc/include`
  - `site-packages/nvidia/cusparse/include`
- 对应 `.so` 也位于各自的 `site-packages/nvidia/.../lib` 目录。
- `tiny-cuda-nn` 的 `bindings/torch/setup.py` 只会:
  - 通过 `nvcc --version` 决定是否切到 `C++17`
  - 依赖 `CUDAExtension` 自动推导 CUDA include / lib
  - 不会主动把上述两个 `site-packages/nvidia/...` 目录加进去

### 结论更新
- 上一条主假设被部分验证:
  - `nvcc not found` 确实是 `PATH` 暴露不足
- 同时新增了更具体的子结论:
  - `nvrtc.h` / `cusparse.h` 缺失不是“机器没有文件”,而是“编译搜索路径没覆盖 `pixi` 环境里的 NVIDIA 开发头和库”

### 下一步最小验证
- 不先改脚本。
- 先在单次命令里手动注入:
  - `PATH=/usr/local/cuda/bin:$PATH`
  - `CUDA_HOME=/usr/local/cuda`
  - `CPATH` / `CPLUS_INCLUDE_PATH` 指向系统 CUDA include + `pixi` 环境里的 `cuda_nvrtc/include` 与 `cusparse/include`
  - `LIBRARY_PATH` / `LD_LIBRARY_PATH` 指向系统 CUDA lib64 + `pixi` 环境里的 `cuda_nvrtc/lib` 与 `cusparse/lib`
- 如果这样能把构建推进到下一层,就把相同逻辑收敛进 `scripts/install_tinycudann.sh`。

### 阶段
- [x] 阶段1: 承接旧上下文并续档超长任务计划
- [x] 阶段2: 验证本机 CUDA 的二进制与头文件布局
- [ ] 阶段3: 修补 tiny-cuda-nn 安装脚本的 CUDA 环境导出
- [ ] 阶段4: 运行脚本级、任务级和 setup 级验证

### 状态
**目前在阶段3** - 正在做“不改脚本、只注入环境变量”的动态证伪实验,确认修复应落在哪一层。

## [2026-03-22 00:03:00] [Session ID: codex-20260321-234700] [记录类型]: 动态环境注入实验推翻“只补两个头文件目录就够”的子假设

### 动态证据
- 手动导出 `PATH`、`CUDA_HOME`、`CPATH`、`CPLUS_INCLUDE_PATH`、`LIBRARY_PATH`、`LD_LIBRARY_PATH` 后再次运行 `pixi run install-tinycudann`。
- 构建日志明确显示:
  - `Detected CUDA version 12.4`
  - `Targeting C++ standard 17`
- 这证明:
  - `nvcc not found` 已被解决
  - `C++17` 探测问题已被解决
  - `nvrtc.h` 与 `cusparse.h` 已不再是首个失败点
- 新的首个真实失败点变成:
  - `fatal error: cublas_v2.h: 没有那个文件或目录`

### 被推翻的子假设
- 上一轮的“只补 `cuda_nvrtc` 和 `cusparse` 两组目录就足够”不成立。

### 新主假设
- `pixi` 环境里应该还安装了更多 NVIDIA wheel,例如 `cublas`。
- tiny-cuda-nn 需要的不是零散补丁式路径,而是把 `site-packages/nvidia/*/include` 与 `site-packages/nvidia/*/lib` 统一拼到搜索路径中。

### 下一步
- 先列出 `pixi` 环境中的 `site-packages/nvidia/*` 目录,确认哪些包提供 `include` / `lib`。
- 如果证据成立,就把脚本改成“自动收集所有 NVIDIA wheel 的 include/lib 路径”,而不是硬编码个别库。

### 状态
**目前仍在阶段3** - 正在把修复从“局部补路径”收敛成“自动汇总所有 NVIDIA wheel 开发路径”。

## [2026-03-22 00:18:00] [Session ID: codex-20260321-234700] [记录类型]: `pixi run setup` fresh verification 通过

### 已验证结论
- `scripts/install_tinycudann.sh` 的新逻辑已经能自动:
  - 暴露 `/usr/local/cuda/bin`
  - 汇总 `pixi` 环境下 `site-packages/nvidia/*/include`
  - 汇总 `site-packages/nvidia/*/lib`
  - 为只有 `libfoo.so.12` 的 NVIDIA wheel 生成临时 `libfoo.so` 链接别名
  - 通过 `LDFLAGS` 注入运行时 `rpath`
- 真实命令验证结果:
  - `bash -n scripts/install_tinycudann.sh` 通过
  - `python3 -m unittest tests/test_pixi_manifest.py` 通过
  - `timeout 1800s pixi run install-tinycudann` 通过
  - `timeout 1800s pixi run setup` 通过
  - `pixi run python` 内 `import tinycudann as tcnn` 通过

### 关键动态证据
- 修复前的首错链路:
  - `nvcc: not found`
  - `C++17 or later compatible compiler is required to use PyTorch`
  - `nvrtc.h` / `cusparse.h` 缺失
- 手动环境注入后,首错推进到:
  - `cublas_v2.h` 缺失
- 扩展为“汇总全部 NVIDIA wheel include/lib”后,首错再推进到:
  - `-lnvrtc` 找不到
- 补上无版本 `.so` 链接别名与 `rpath` 后:
  - `tinycudann` 成功构建并安装
  - `setup` 主链路继续跑完 `setup-romav2`

### 收尾说明
- 为了让默认 `.envrc` 中的 `TINYCUDANN_LOCAL_REPO=/tmp/video_to_world-tiny-cuda-nn` 立即可用,本轮把它指向了已经验证过的本地 clone:
  - `/tmp/video_to_world-tiny-cuda-nn -> /tmp/tcnn-clone-test.HtOWVH`
- 当前没有新的未完成阻塞留在 `setup` 主链上。

### 阶段
- [x] 阶段1: 承接旧上下文并续档超长任务计划
- [x] 阶段2: 验证本机 CUDA 的二进制与头文件布局
- [x] 阶段3: 修补 tiny-cuda-nn 安装脚本的 CUDA 环境导出
- [x] 阶段4: 运行脚本级、任务级和 setup 级验证

### 状态
**目前已完成** - `pixi run setup` 已 fresh verification 通过,准备整理错误记录与交付说明。

## [2026-03-22 00:30:00] [Session ID: codex-20260321-234700] [记录类型]: 新任务初始化 - 用 `source/flashvsr_reference_xhc_bai` 做真实测试运行

### 目标
- 使用真实数据目录 `source/flashvsr_reference_xhc_bai/full_scale2x` 运行联合多视角重建入口。
- 验证“代码层 dry-run 正常”已经进一步升级为“真实数据链路可启动并继续运行”。
- 如果运行失败,收敛出新的真实阻塞点; 如果运行成功,记录输出路径和关键产物。

### 当前理解
- 这套数据目录是:
  - `full_scale2x/0..5/rgb/*.mp4`
- 它对应的入口不是单视频脚本,而是:
  - `run_multiview_reconstruction.py`
- 按当前文档,最合理的第一条真实测试命令是:
  - `pixi run python run_multiview_reconstruction.py --views-root source/flashvsr_reference_xhc_bai/full_scale2x --scene-root <test_scene_root> --config.mode fast`

### 主假设
- 当前主假设是:
  - 既然 `pixi run setup` 已 fresh verification 通过,这条真实联合入口至少应当能够进入 Stage 0,并继续对真实数据做处理。

### 最强备选解释
- 也可能环境依赖虽然装好了,但真实数据运行还会暴露:
  - GPU / 显存不足
  - 模型权重下载
  - 某个阶段对真实视频内容或帧数的约束问题

### 最小执行计划
- 先探针:
  - `nvidia-smi -L`
  - 输出目录是否可写
- 再直接跑真实联合入口:
  - 使用 `fast` 模式
  - 使用新的测试 `scene_root`,避免污染旧结果

### 阶段
- [ ] 阶段1: 确认真实数据目录、GPU 和输出路径
- [ ] 阶段2: 启动真实联合多视角重建
- [ ] 阶段3: 记录运行结果、产物和后续建议

### 状态
**目前在阶段1** - 正在确认真实测试运行的前置条件,随后立刻启动 `source/flashvsr_reference_xhc_bai` 的联合重建。

## [2026-03-22 00:33:00] [Session ID: codex-20260321-234700] [记录类型]: 真实运行前置探针完成

### 新证据
- `nvidia-smi -L` 返回:
  - `GPU 0: NVIDIA RTX 6000 Ada Generation`
- `/tmp` 与 `/workspace` 所在磁盘可用空间约 `1.6T`
- `source/flashvsr_reference_xhc_bai/full_scale2x` 下确认存在 6 个视角视频:
  - `0..5/rgb/xhc-bai_97e474c6.mp4`
- `/tmp` 可写

### 结论
- 当前真实联合运行的基础前提已满足:
  - 数据存在
  - GPU 存在
  - 输出路径可写

### 下一步
- 直接运行:
  - `pixi run python run_multiview_reconstruction.py --views-root source/flashvsr_reference_xhc_bai/full_scale2x --scene-root /tmp/video_to_world_joint_scene_xhc_bai_fast_run_20260322 --config.mode fast`

### 阶段
- [x] 阶段1: 确认真实数据目录、GPU 和输出路径
- [ ] 阶段2: 启动真实联合多视角重建
- [ ] 阶段3: 记录运行结果、产物和后续建议

### 状态
**目前在阶段2** - 正在启动 `source/flashvsr_reference_xhc_bai` 的真实联合重建。

## [2026-03-22 00:37:00] [Session ID: codex-20260321-234700] [记录类型]: 真实运行首个阻塞点已收敛到 Hugging Face 代理层

### 已观察现象
- 真实运行已经成功完成:
  - Stage 0 第一个视角的视频拆帧
  - `frames_subsampled` 生成
  - 进入 `DepthAnything3.from_pretrained(...)`
- 首个失败点不是算法逻辑,而是模型下载阶段:
  - 当前 shell 存在 `all_proxy=socks5://127.0.0.1:7897`
  - `huggingface_hub` / `httpx` 看到 SOCKS 代理后,因为环境里没有 `socksio`,直接报:
    - `ImportError: Using SOCKS proxy, but the 'socksio' package is not installed`
- 进一步最小验证显示:
  - 去掉 `ALL_PROXY`,只用 `http/https` 走 `127.0.0.1:7890` 后,请求已能发起,但又遇到 `SSL EOF`
  - 机器上也没有已缓存的 `depth-anything/DA3NESTED-GIANT-LARGE` 本地模型目录可直接复用

### 当前结论
- 真实运行阻塞已从“代码/环境安装问题”推进到“模型下载代理兼容问题”。
- 当前主修复方向是:
  - 先让 `httpx` 具备 SOCKS 能力
  - 再按用户给的 `127.0.0.1:7890` 代理做最小下载验证

### 下一步
- 在 `pixi` 环境里安装 `socksio`
- 用 `HTTP_PROXY=http://127.0.0.1:7890`、`HTTPS_PROXY=http://127.0.0.1:7890`、`ALL_PROXY=socks5://127.0.0.1:7890` 重试 `hf_hub_download`
- 若成功,立即重跑真实联合入口

### 状态
**目前仍在阶段2** - 正在修复 DA3 模型下载所需的代理兼容层,准备继续真实运行。

## [2026-03-22 00:50:00] [Session ID: codex-20260321-234700] [记录类型]: SOCKS 兼容层已补齐,准备在去代理环境下重跑真实数据

### 新证据
- `pixi` 环境原先确实缺少 `socksio`,已通过:
  - `timeout 300s env -u ... pixi install`
  - `timeout 60s env -u ... pixi run python`
  重新验证为 `socksio_installed=True`
- 但到 Hugging Face 的最小探针仍显示:
  - `127.0.0.1:7890` 代理路径会出现 `SSL EOF`
  - 直连路径在 60 秒窗口内无报错,但也未完成返回

### 当前策略
- 先不再强推 `7890` 代理。
- 直接在去掉旧代理变量的环境里,给真实运行更长窗口。
- 目标是区分:
  - “只是慢,最终可下”
  - 还是“外部链路长期不可达”

### 下一步
- 运行:
  - `env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy pixi run python run_multiview_reconstruction.py ...`

### 状态
**目前仍在阶段2** - 正在做“去代理环境下的真实重跑”验证。

## [2026-03-21 20:08:15] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 接手真实测试并先做离线模型可用性证伪

### 背景承接
- 已继承上一会话的动态证据:
  - `pixi run setup` 已通过
  - `source/flashvsr_reference_xhc_bai/full_scale2x` 的真实入口已能启动
  - 首个真实阻塞落在 `DepthAnything3.from_pretrained("depth-anything/DA3NESTED-GIANT-LARGE")`
- 上一会话已经证明:
  - 坏的 `7897` 代理会误导下载链路
  - `7890` 代理路径也没有稳定下载成功
  - 去代理直连则出现 `[Errno 101] Network is unreachable`

### 当前目标
- 继续推进 `source/flashvsr_reference_xhc_bai` 的真实测试运行。
- 优先确认当前机器是否已经存在可复用的本地 DA3 模型目录或 Hugging Face 缓存。
- 如果能转成本地模型路径,就绕过当前不稳定的外网下载链路,继续真实运行。

### 现象
- 已观察到的事实是:
  - 代码入口和 Stage 0 拆帧并没有失败
  - 当前失败集中在在线下载 `depth-anything/DA3NESTED-GIANT-LARGE`
- 还没有证据表明:
  - 仓库逻辑本身存在新的代码 bug

### 当前主假设
- 当前主假设是:
  - 只要本机已有完整 DA3 本地权重目录,就可以通过本地路径继续推进真实测试运行。

### 最强备选解释
- 也可能本机根本没有可用本地模型。
- 如果如此,那真实阻塞就仍然是外部 Hugging Face 链路,而不是命令参数问题。

### 最小验证计划
- 先做 3 个最小探针:
  - 搜索本机 Hugging Face 缓存和工作区中是否已有 `DA3NESTED-GIANT-LARGE`
  - 检查仓库 CLI 是否支持直接传入本地 `preprocess_model_name`
  - 如果存在本地目录,先用最小 `from_pretrained(<local_path>)` 探针验证可加载
- 只有本地路径可用时,才重跑整条真实流水线。

### 状态
**目前仍在阶段2** - 正在先做“本地模型可用性”证伪实验,避免继续盲目消耗长时间真实重跑窗口。

## [2026-03-21 20:11:30] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 发现可用镜像端点,准备切到真实权重下载

### 新证据
- 本地缓存搜索结果:
  - 没有发现现成的 `DA3NESTED-GIANT-LARGE` 权重目录
  - 只在 Hugging Face cache 中新增了通过镜像下载到的 `config.json`
- 代码入口确认:
  - `run_multiview_reconstruction.py` 支持 `--preprocess-model-name`
  - `preprocess_video.py` 的参数说明已明确支持 "HuggingFace repo or local"
- 最关键的新动态证据:
  - 去掉代理后,`hf_hub_download(..., endpoint='https://hf-mirror.com', filename='config.json')` 成功
  - 同样条件下,`hf_hub_download(..., dry_run=True, filename='model.safetensors')` 成功返回:
    - `commit_hash=8615eefb62f2db4f8d6ebaa59160086981672829`
    - `file_size=6759558100`
- 对比失败证据:
  - `7890` 代理路径访问官方域名与镜像域名都会稳定出现 `SSL EOF`

### 结论更新
- 上一轮“整条外部模型下载链路都不可用”的口径不成立。
- 当前更准确的结论是:
  - 官方 Hugging Face 域名在当前环境不可用
  - `hf-mirror.com` 在去代理条件下对 `huggingface_hub` 是可用的

### 下一步
- 先在 `HF_ENDPOINT=https://hf-mirror.com` 条件下真实下载 `model.safetensors`
- 下载完成后立刻重跑:
  - `pixi run python run_multiview_reconstruction.py --views-root source/flashvsr_reference_xhc_bai/full_scale2x --scene-root <test_scene_root> --config.mode fast`

### 状态
**目前仍在阶段2** - 已把问题收敛到“镜像下载 + 真实重跑”,不再继续围绕坏代理做无效尝试。

## [2026-03-21 20:51:53] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 上轮中断后恢复下载,确认已有 4.66 GiB 续传基础

### 新证据
- 上一轮被用户中断后:
  - 原下载进程 session 已不存在
  - 但 Hugging Face cache 中保留了:
    - `4655677440` 字节的 `model.safetensors.incomplete`
- 这说明:
  - `HF_ENDPOINT=https://hf-mirror.com` 的真实下载路径仍然成立
  - 只是进程被中途打断,不是链路重新失败

### 当前结论
- 当前最合适的下一步不是重新排查代理。
- 而是:
  - 在同样的去代理 + `HF_ENDPOINT=https://hf-mirror.com` 条件下恢复下载
  - 下载完成后立刻继续 `source/flashvsr_reference_xhc_bai` 的真实联合运行

### 状态
**目前仍在阶段2** - 正在从上轮中断点恢复 DA3 大权重下载,随后继续真实测试运行。

## [2026-03-21 20:51:53] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 按用户要求切换为先查 ModelScope 可用性

### 触发原因
- 用户新增要求:
  - 遇到 Hugging Face 模型下载时,先检查 `https://modelscope.cn/` 是否已有对应模型
  - 如果我这边不会找或找不到,需要明确告诉用户

### 已观察现象
- `modelscope.cn` 公开搜索页是前端渲染,直接 `curl` 只能拿到壳页面,拿不到结果列表。
- 通过 `opensearch.xml` 可以确认官方搜索入口是:
  - `https://www.modelscope.cn/search?search=...`
- 通过站外检索当前能稳定找到的相关 ModelScope 页面包括:
  - `https://modelscope.cn/models/onnx-community/depth-anything-v3-small`
  - `https://modelscope.cn/models/depth-anything/Metric-Video-Depth-Anything-Base`
  - `https://modelscope.cn/models/cubeai/depth_anything_vitl14`
- 但到目前为止,还没有找到与当前代码精确匹配的:
  - `depth-anything/DA3NESTED-GIANT-LARGE`

### 当前结论
- 当前不能把“ModelScope 上没有”说死。
- 更准确的说法是:
  - 我这边目前能找到若干相关 `depth-anything` 模型
  - 但还没查到当前流水线所需的精确 DA3 模型页面

### 下一步
- 先把当前查找结论和已找到的相关链接告诉用户。
- 如果用户能提供更准确的 ModelScope 链接,我就转为走 ModelScope 或本地目录继续跑 `source/flashvsr_reference_xhc_bai`。

## [2026-03-21 21:36:41] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 按用户要求继续 hf-mirror,确认 DA3 权重已完整落盘

### 新证据
- 当前没有残留下载进程在跑。
- Hugging Face cache 中已经出现完整文件:
  - `6759558100 /root/.cache/huggingface/hub/models--depth-anything--DA3NESTED-GIANT-LARGE/blobs/8899...`
- 对应 snapshot 目录也已存在:
  - `snapshots/8615eefb62f2db4f8d6ebaa59160086981672829/`
  - 其中 `config.json` 和 `model.safetensors` 都已经正确链接到 `blobs/`

### 结论更新
- 当前真实阻塞已经不再是 DA3 大权重下载。
- 下一步应该转成:
  - 先用本地 snapshot 目录做一次最小 `from_pretrained` 加载验证
  - 验证通过后,直接重跑 `source/flashvsr_reference_xhc_bai` 的真实联合入口

### 状态
**目前仍在阶段2** - 正在把“镜像下载成功”推进为“本地模型可加载 + 真实运行继续”。

## [2026-03-21 21:37:30] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 本地 snapshot 加载验证通过,切换到离线 DA3 真实重跑

### 新证据
- `hf_hub_download(..., local_files_only=True)` 已能直接返回本地 `model.safetensors` 路径。
- `DepthAnything3.from_pretrained('/root/.cache/huggingface/hub/models--depth-anything--DA3NESTED-GIANT-LARGE/snapshots/8615eefb62f2db4f8d6ebaa59160086981672829')` 已真实成功。
- 输出确认:
  - `Loading weights from local directory`
  - `MODEL_NAME da3nested-giant-large`

### 当前结论
- DA3 这一层已经可以完全离线运行,不需要再碰 Hugging Face 在线路径。

### 下一步
- 使用新的干净 `scene_root`
- 显式传入本地 `--preprocess-model-name <snapshot_dir>`
- 直接重跑 `source/flashvsr_reference_xhc_bai/full_scale2x`

### 状态
**目前仍在阶段2** - 正在切到“本地 DA3 离线模式”的真实联合重跑。

## [2026-03-21 21:57:14] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 联合预处理已全通,新的首阻塞转移到 RoMaV2 权重下载

### 已验证现象
- `source/flashvsr_reference_xhc_bai/full_scale2x` 的 6 个视角都已完成:
  - 本地 DA3 加载
  - `results.npz`
  - `gs_video`
- 联合 `preprocess_multiview_summary.json` 已成功写出,总帧数 `600`
- `run_reconstruction.py` 已进入 Stage 1:
  - `frame_to_model_icp` 正在运行
- 新的首个外部下载点是:
  - `https://github.com/Parskatt/RoMaV2/releases/download/weights/romav2.pt`
- 当前真实下载速度只有约 `9-19 kB/s`,且本机无现成 `romav2.pt`

### 当前结论
- 这说明 Hugging Face / DA3 层已不再是阻塞。
- 当前真实阻塞已经转移到 RoMaV2 的 GitHub 权重下载。

### 测试运行优先策略
- 对“先把这套数据跑起来做测试”而言,继续硬等 1GB 的 RoMaV2 权重并不划算。
- 代码中已确认存在正式开关:
  - `--config.stage1.roma.use-roma-matching false`
- 因此下一步采用:
  - 停掉当前几乎不可用的 RoMaV2 下载
  - 复用已完成的 Stage 0 输出
  - 重新运行 `run_reconstruction.py`
  - 关闭 RoMa matching
  - 用新的 `stage1.out_suffix` 隔离结果

### 状态
**目前仍在阶段2** - 正在从“完整质量路径”切换到“测试运行优先路径”,以避免再被外部大文件下载拖住。
## [2026-03-21 21:59:55] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 从已完成的联合 Stage 0 继续推进后半程测试运行

### 当前现象
- `source/flashvsr_reference_xhc_bai/full_scale2x` 的联合 Stage 0 已真实跑通。
- 当前新的首阻塞不是 Hugging Face,而是 Stage 1 默认会下载 GitHub 上的 `romav2.pt`。
- 现有场景根目录下已经有一次未完成的 `frame_to_model_icp_50_2_offset0`,因此继续测试时要避免把新运行结果和旧残留混在一起。

### 当前假设
- 主假设:
  - 直接复用已经成功的联合 Stage 0 输出,并在 `run_reconstruction.py` 中正式关闭 RoMa matching,可以绕过外部 1GB 权重下载,继续推进真实测试运行。
- 备选解释:
  - 即使关闭 RoMa matching,Stage 1 或后续训练阶段仍可能暴露新的运行时问题。

### 最小验证计划
- 先快速复核 CLI 布尔参数和输出后缀参数是否可用。
- 再用新的 `stage1.out_suffix` 启动真实运行,避免污染已有半成品目录。
- 运行期间持续观察日志,确认是否成功生成新的 Stage 1 输出目录并继续进入后续阶段。

### 状态
**目前仍在阶段3** - 正在基于已完成的联合 Stage 0 结果,推进“关闭 RoMa matching 的后半程真实测试运行”。
## [2026-03-21 22:13:00] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: Stage 1 与 Stage 3.1 已通,Stage 3.2 转入“去 LPIPS 下载”的测试跑策略

### 已验证现象
- 关闭 RoMa matching 后,新的 Stage 1 目录 `frame_to_model_icp_50_2_offset0_nroma_20260321_2201` 已真实成功产出。
- `inverse_deformation` 目录及 round-trip validation 产物已真实落盘,说明 Stage 3.1 也已完成。
- 新的首阻塞转移到 Stage 3.2:
  - `train_gs` 在 `lpips_weight > 0` 时会调用 `lpips.LPIPS(net='vgg')`
  - 这会触发 `download.pytorch.org/models/vgg16-397923af.pth`
  - 当前下载速度只有约 `0.1~0.2 MB/s`,不足以作为“测试运行优先”路径

### 当前假设
- 主假设:
  - 对“先把这套数据测试跑通”而言,直接复用已完成的 Stage 1 + Stage 3.1 输出,并在 `train_gs` 中正式把 `lpips_weight` 设为 `0`,可以绕过 VGG 下载并继续验证 Stage 3.2 的核心训练链路。
- 备选解释:
  - 即使关闭 LPIPS 下载,Stage 3.2 仍可能在渲染器、显存或自动评估阶段暴露新的运行时问题。

### 下一步最小验证
- 不再重跑 Stage 1 / Stage 3.1。
- 直接调用 `train_gs`:
  - 指向已落盘的 `run` 与 `inverse_deformation`
  - 使用新的 `out_dir` 隔离被中断的默认 `gs_3dgs` 目录
  - 设置 `lpips_weight=0`
  - 缩短 `num_iters`,以测试跑为优先

### 状态
**目前仍在阶段3** - 已经把阻塞从 RoMaV2 下载推进到 VGG16 下载,正在改走“Stage 3.2 去 LPIPS 下载”的快速验证路径。
## [2026-03-21 22:12:38] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 后半程测试运行已拿到可交付结果

### 已完成事项
- [x] 复用联合 Stage 0 结果继续推进后半程
- [x] 关闭 RoMa matching,真实跑通新的 Stage 1
- [x] 确认 Stage 3.1 `inverse_deformation` 已真实落盘
- [x] 关闭 LPIPS 下载阻塞,完成一轮短程 Stage 3.2 真实训练
- [x] 收集日志证据并核对关键产物文件

### 当前状态
**目前在阶段4** - 已经拿到 `source/flashvsr_reference_xhc_bai` 的后半程真实测试结果,正在整理交付说明与后续建议。
## [2026-03-21 22:14:40] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 用户选择方案1,转入补齐 RoMaV2 / VGG16 缓存并重跑默认全量路径

### 用户选择
- 用户选择上一轮给出的方案 `1`:
  - 补齐 `romav2.pt` 和 `vgg16-397923af.pth` 本地缓存
  - 然后重新跑默认全量路径

### 当前现象
- 当前测试路径已经证明 Stage 0 / 1 / 3.1 / 3.2 核心链路可运行。
- 但默认全量路径仍会被两个在线权重下载拖住:
  - `romav2.pt`
  - `vgg16-397923af.pth`

### 当前假设
- 主假设:
  - 只要先把这两个大权重补进本地缓存,默认全量路径就能继续推进,不再被网络层频繁打断。
- 备选解释:
  - 即使权重补齐,默认长跑仍可能在更后面的长训练阶段暴露新的资源或运行时问题。

### 下一步最小验证
- 先确认本机当前缓存现状与代码实际读取路径。
- 再判断最稳的补齐方式: 本地已有副本 / 官方源续传 / 可验证的镜像源。
- 权重补齐后,重新发起默认全量路径重跑。

### 状态
**目前仍在阶段3** - 正在把“测试跑已通”推进到“默认全量路径可继续执行”。
## [2026-03-21 22:35:00] [Session ID: codex-20260321-223500] [记录类型]: 接手默认全量路径重跑,先清理残留探针并验证 DINOv3 torch hub 缓存阻塞

### 背景承接
- 用户已选择方案 `1`:
  - 补齐 `romav2.pt`
  - 补齐 `vgg16-397923af.pth`
  - 然后重跑默认全量路径
- 上一轮会话已经完成:
  - `romav2.pt` 本地缓存
  - `vgg16-397923af.pth` 本地缓存
  - 一个最小初始化探针,并观察到新的首阻塞转移到 DINOv3 的 torch hub GitHub zip 下载
- 当前会话先确认了旧探针残留进程,并已清理完成。

### 当前现象
- 已观察到的事实:
  - `RoMaV2(RoMaV2.Cfg(compile=False))` 还会触发 `torch.hub` 拉取 `facebookresearch/dinov3` 的固定 commit zip
  - `romav2.pt` 与 `vgg16-397923af.pth` 已不再是首个缺失项
  - 现场目前没有残留的 `run_reconstruction` / `train_gs` / `torch hub` 相关进程

### 当前假设
- 主假设:
  - 只要预热好 DINOv3 的 torch hub 缓存,最小初始化就能离线通过,默认全量路径也能越过新的下载阻塞点。
- 备选解释:
  - 即使 zip 缓存补齐,torch hub 仍可能因为解压目录命名或后续权重逻辑再次触发联网。

### 最小验证计划
- 先读本地代码和缓存目录,确认 torch hub 对 DINOv3 的期望缓存文件名与目录名。
- 再用最小方式补齐 DINOv3 repo cache,优先避免直接长时间卡在 GitHub 官方下载。
- 然后重跑最小初始化探针:
  - `RoMaV2(RoMaV2.Cfg(compile=False))`
  - `lpips.LPIPS(net='vgg')`
- 若探针通过,再准备 fresh scene root 并发起默认全量路径重跑。

### 状态
**目前在阶段3** - 正在把默认全量路径的首阻塞从 `romav2.pt / vgg16` 进一步推进到 `DINOv3 torch hub cache` 层。
## [2026-03-21 22:37:30] [Session ID: codex-20260321-223500] [记录类型]: DINOv3 torch hub 缓存已补齐,转入 fresh root 的默认全量路径重跑

### 已验证结论
- `romav2.pt` 本地缓存有效
- `vgg16-397923af.pth` 本地缓存有效
- `facebookresearch_dinov3_adc254450203739c8149213a7a69d8d905b4fcfa` 已手动预热到 `/root/.cache/torch/hub`
- 最小初始化探针已经成功输出:
  - `roma_model_ok RoMaV2`
  - `lpips_ok LPIPS`
- 当前默认全量路径已越过此前三个外部下载阻塞:
  - DA3 / HF
  - `romav2.pt`
  - `vgg16-397923af.pth`
  - DINOv3 torch hub repo zip

### 下一步最小验证
- 不直接复用混有旧 Stage 1 / 测试 Stage 3 目录的 scene root。
- 先从 `/tmp/video_to_world_joint_scene_xhc_bai_fast_run_local_da3_20260321_2142` 裁出一个 fresh root,只保留 Stage 0 所需产物。
- 然后在 fresh root 上运行默认参数的:
  - `pixi run python run_reconstruction.py --config.root-path <fresh_root> --config.mode fast`
- 持续观察它是否真正进入:
  - 默认 Stage 1 RoMa matching
  - 默认 Stage 3.2 LPIPS 路径

### 状态
**目前仍在阶段3** - 外部缓存阻塞已解除,正在把验证推进到“fresh root 上的默认全量路径真实重跑”。
## [2026-03-21 22:42:30] [Session ID: codex-20260321-223500] [记录类型]: 默认全量路径已越过下载层,新的首阻塞变为 RoMa sampling 的 CUDA OOM

### 已验证现象
- 默认 `run_reconstruction.py --config.mode fast` 已成功进入真实的 RoMa matching 路径。
- 失败不再发生在缓存或下载阶段。
- 当前首个失败点是:
  - `third_party/RoMaV2/src/romav2/romav2.py:529`
  - `torch.cdist(x, x)`
  - `torch.OutOfMemoryError`
- 失败时 GPU 状态明确显示只剩约 `442.88 MiB` 空闲显存,而该步还想额外申请约 `764 MiB`。

### 当前假设
- 主假设:
  - 默认 RoMa sampling 配置对当前场景过重,需要通过已有正式配置先收敛显存占用。
- 备选解释:
  - RoMa / ICP 中间状态可能存在逐帧累积,导致显存不是单次峰值而是逐步堆积。

### 下一步最小验证
- 先查明默认 RoMa sampling 相关配置和释放路径。
- 再决定是“正式参数降采样”还是“代码层修复显存累积”。

### 状态
**目前仍在阶段3** - 默认全量路径的外部缓存问题已解决,正在收敛新的运行时首阻塞 `RoMa CUDA OOM`。
## [2026-03-21 23:31:00] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 继续默认 RoMa 路径显存修复验证,先打通本地单测再重跑真实 Stage 1

### 当前已知现象
- `romav2.pt`、`vgg16-397923af.pth`、DINOv3 torch hub 缓存都已补齐。
- 默认全量路径已经越过下载层,新的首阻塞是 RoMa 阶段 CUDA OOM。
- 当前代码已落下一版“历史状态下沉 CPU + 按需迁移回 GPU”的修法,但还没完成 fresh verification。

### 当前主假设
- 这版修法如果成立,应当先体现为:
  - 新增单测全部通过
  - 真实 Stage 1 的炸点继续后移,或直接跑通
- 备选解释:
  - 单测只覆盖 device 迁移语义,但真实 OOM 还可能来自别的逐帧 GPU 常驻对象。

### 下一步行动
- [ ] 修复 `tests/test_roma_memory_offload.py` 中过严的 device 断言。
- [ ] 重新跑 `py_compile` 和该单测,确认本地验证链通过。
- [ ] 基于 fresh root 重跑真实 Stage 1,检查是否越过先前 frame 12 左右的 OOM 点。

### 状态
**目前仍在阶段3** - 正在先打通新增显存管理修法的本地验证,然后立刻进入真实 Stage 1 长跑验证。
## [2026-03-21 23:33:30] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 新增显存管理修法的本地验证链已打通,转入真实 Stage 1 长跑

### 已完成事项
- [x] 修复 `tests/test_roma_memory_offload.py` 中过严的 device 断言。
- [x] 跑通 `py_compile` 与新增单测。

### 当前状态
**目前仍在阶段3** - 本地短验证已通过,现在进入 fresh root 上的真实 Stage 1 长跑,检查默认 RoMa 路径是否越过先前 OOM 点。
## [2026-03-21 23:05:30] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 已确认 RoMaV2 显存是跨帧累计,转入“按帧刷新 matcher”后的真实 Stage 1 再验证

### 已验证结论
- [x] CPU 下沉修法有效,已把默认失败点从 frame 9 / 12 推迟到 frame 15。
- [x] 最小探针证明: 单帧 15 个 pair 都能成功,但同一 matcher 实例会在每个 pair 后持续抬高 `memory_allocated()`。
- [x] `gc.collect()` 不能回收这部分显存,`del matcher` 会带来部分回落。

### 下一步行动
- [ ] 基于“按帧刷新 matcher”的新代码,重新跑真实 Stage 1。
- [ ] 验证是否越过 frame 15 并继续推进默认 RoMa 路径。

### 状态
**目前仍在阶段3** - 已把问题收敛为 RoMaV2 的跨帧生命周期累计,现在进入新的真实 Stage 1 验证。
## [2026-03-21 23:21:30] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 主流程内的 RoMa 新算 pair 仍会跨帧污染显存,改为独立进程预热剩余 cache

### 已验证结论
- [x] memtrace 证明: 新算 pair 后的显存会在 `after_roma` 留下,并直接延续到下一帧 `before_roma`。
- [x] frame 21 独立进程试跑成功,说明“每帧一个新进程”可以稳定产出 cache。

### 下一步行动
- [ ] 用独立进程补齐 `src=21..49` 的剩余 RoMa cache。
- [ ] cache 补齐后重跑真实 Stage 1,验证主流程只读 cache 时是否稳定跑完。

### 状态
**目前仍在阶段3** - 进入“先补齐剩余 RoMa cache,再重跑主流程”的执行阶段。
## [2026-03-21 23:33:40] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 剩余 RoMa cache 已补齐到 src=49,开始重跑只读 cache 的真实 Stage 1

### 已完成事项
- [x] 使用独立进程补齐 `src=21..49` 的 RoMa cache。
- [x] 当前 cache 覆盖已完整,不存在缺失帧。

### 下一步行动
- [ ] 重跑真实 Stage 1,验证全程只读 cache 是否稳定跑完。
- [ ] 若 Stage 1 跑通,继续默认后半程 `skip-alignment` 验证。

### 状态
**目前仍在阶段3** - 进入“全量 cache 命中”的真实主流程验证。
## [2026-03-21 23:43:30] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 默认 RoMa 路径 Stage 1 已真实跑通,转入 skip-alignment 后半程验证

### 已完成事项
- [x] 真实跑通 `frame_to_model_icp_50_2_offset0_allcache_20260321_2334`
- [x] 证明全量 cache 命中后,RoMa 显存保持稳定

### 下一步行动
- [ ] 使用新的 `alignment-run` 执行 `run_reconstruction.py --config.skip-alignment`
- [ ] 验证 Stage 2 / Stage 3 是否也能基于默认 RoMa Stage 1 结果继续跑通

### 状态
**目前仍在阶段3** - Stage 1 已完成,正在进入默认后半程真实验证。

## [2026-03-21 23:44:48] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 从上次未完成步骤继续,开始执行 skip-alignment 后半程真实验证

### 继续原因
- 上一轮已经真实跑通默认 RoMa Stage 1, 当前最关键的未完成步骤是验证 Stage 2 / Stage 3 是否能基于该结果继续跑通。

### 下一步行动
- [ ] 检查 GPU / 进程现场,避免旧进程或旧显存状态污染本轮长跑。
- [ ] 执行 `run_reconstruction.py --config.skip-alignment` 的真实后半程运行。
- [ ] 记录新的首阻塞或完整成功结果,并同步回六文件。

### 状态
**目前仍在阶段3** - 正在从上次未完成步骤继续,准备启动 skip-alignment 后半程真实验证。

## [2026-03-21 23:45:31] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: skip-alignment 后半程已启动并进入 inverse deformation 训练

### 已观察到的现象
- 现场 GPU 空闲, 没有残留旧进程。
- `run_reconstruction.py --config.skip-alignment` 已成功进入 Stage 2。
- 当前日志已出现 `Created inverse deformation model`、`Starting training...`、`Epoch 1/15`。

### 当前假设
- 主假设: 现阶段的首个验证重点已经从“能否启动”转为“Stage 2 训练能否稳定完成并继续推进到 Stage 3”。
- 备选解释: 即使 Stage 2 能跑, 仍可能在 round-trip validation、GS 训练或 eval 阶段出现新的阻塞。

### 状态
**目前仍在阶段3** - 后半程真实长跑已开始, 正在等待 Stage 2 是否稳定完成。

## [2026-03-21 23:49:25] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: Stage 2 已完成并进入默认 LPIPS 的 GS 训练,开始评估测试运行是否需要缩短 GS 轮数

### 已验证现象
- round-trip validation summary 已写入日志。
- 默认 LPIPS 权重已成功加载, `gs_3dgs` 训练已经进入真实迭代。
- 当前默认配置是 10000 iter, 按现场速度估算需要约 2.5 小时。

### 当前假设
- 主假设: 对“测试运行”来说, 当前已经证明默认 Stage 2 / Stage 3 路径可启动, 下一步更有价值的是用正式参数缩短 GS 轮数,完成一次可收尾的 smoke 验证。
- 备选解释: 也可能需要保留当前长跑直到完整结束, 才能证明默认终态没有隐藏问题。

### 下一步行动
- [ ] 查明 `run_reconstruction.py` 是否支持直接覆盖 GS `num_iters`。
- [ ] 根据结果决定继续长跑,还是改为短程完整收尾验证。

### 状态
**目前仍在阶段3** - 默认 LPIPS GS 训练已启动, 正在判断测试运行的最优收尾方式。

## [2026-03-21 23:49:59] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 已证实默认 GS 路径可启动,切换为短程 smoke 完整收尾验证

### 已验证结论
- Stage 2 inverse deformation 与 round-trip validation 已真实完成。
- 默认 LPIPS 的 `gs_3dgs` 训练已真实进入迭代, 不是启动即失败。
- `run_reconstruction.py` 支持 `--config.gs.num-iters` 等正式覆盖参数。

### 决策
- 不继续让默认 10000 iter 长跑占用约 2.5 小时。
- 改为执行一条短程但可完整收尾的 smoke 命令, 目标是尽快得到 Stage 3 的保存 / eval / 导出证据。

### 状态
**目前仍在阶段3** - 正在从“默认长跑已证明可启动”切换到“短程完整收尾验证”。

## [2026-03-21 23:50:36] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 已启动短程默认 LPIPS smoke 验证

### 运行参数
- `run_reconstruction.py --config.skip-alignment`
- `--config.gs.num-iters 150`
- `--config.gs.save-every 100`
- `--config.gs.eval-every 100`
- 独立 `--config.gs.out-dir` 与独立日志文件

### 状态
**目前仍在阶段3** - 短程 smoke 已启动, 正在等待 Stage 2 重跑结束并进入 150 iter 的 GS 收尾验证。

## [2026-03-21 23:52:19] [Session ID: 2435180] [记录类型]: 启用 git 发布支线上下文 `__git_publish`

### 启用原因
- 当前用户请求是独立的 Git 提交与推送动作。
- 这和主线的 `pixi run setup` / 重建链路调试不是同一个执行目标。
- 为避免把发布日志和主线调试日志混在一起,本轮改用支线六文件上下文 `__git_publish`。

### 支线主题
- 主题: 整理当前仓库改动,执行 git commit,并推送到 `https://github.com/raiscui/video_to_world.git`
- 对应文件:
  - `task_plan__git_publish.md`
  - `notes__git_publish.md`
  - `WORKLOG__git_publish.md`
  - `LATER_PLANS__git_publish.md`
  - `EPIPHANY_LOG__git_publish.md`
  - `ERRORFIX__git_publish.md`

### 状态
**主线保持不变** - 本条仅登记支线索引,后续发布动作只写入 `__git_publish` 文件集。

## [2026-03-21 23:53:50] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 发现 run_reconstruction 的 GS 覆盖参数未生效,转入静态验证

### 已观察到的现象
- 明确传入 `--config.gs.num-iters 150`。
- 真实日志仍显示 `GS training (3dgs): ... /10000`。
- 同时 `--config.gs.out-dir` 已生效,说明不是所有 GS 子参数都失效。

### 当前主假设
- 主假设: `run_reconstruction.py` 在某个阶段重建 / 覆盖了 GS 配置,导致 `num_iters` 被模式默认值重新写回 10000。
- 备选解释: 真正被训练代码读取的不是 CLI 看到的这个字段,而是另一份配置对象。

### 下一步行动
- [ ] 追踪 `num_iters` 在配置与调用链中的实际流向。
- [ ] 根据证据决定修复覆盖逻辑,还是改用 `train_gs` 直接完成测试运行。

### 状态
**目前仍在阶段3** - 已确认 GS 轮数覆盖未生效, 正在做最小静态验证。

## [2026-03-21 23:56:16] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 修复后已启动真实 GS smoke 运行

### 运行策略
- 复用已存在的 `inverse_deformation` 输出,跳过 Stage 3.1。
- 通过修复后的 `run_reconstruction.py` 真实下发 `--config.gs.num-iters 150`。
- 目标是获取 checkpoint / eval / final model 等落盘证据。

### 状态
**目前仍在阶段3** - 修复后的真实 GS smoke 已启动, 正在等待 150 iter 收尾结果。

## [2026-03-22 00:00:34] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 修复后 GS smoke 训练已完成,新的首阻塞转为 auto eval 缺失 transforms

### 已观察到的现象
- 150 iter 的 GS 训练已经完成。
- `checkpoint_000100.pt`、`checkpoint_000149.pt`、`model_final.pt`、`splats_3dgs.ply` 已落盘。
- `eval_gs` 在读取 `/tmp/video_to_world_joint_scene_xhc_bai_fast_run_full_default_20260321_2238/gs_video/0000_extend_transforms.json` 时报 `FileNotFoundError`。

### 当前主假设
- 主假设: 当前 root 缺少 auto eval 依赖的 transforms 资产, 所以错误发生在评估阶段, 不在训练阶段。
- 备选解释: `eval_gs` 对 joint scene 的默认 transforms 路径推导本身有兼容性问题。

### 下一步行动
- [ ] 追踪 `train_gs -> eval_gs` 的 transforms 路径来源。
- [ ] 决定修默认路径, 还是通过正式参数关闭 auto eval 并完成无错误 smoke 收尾。

### 状态
**目前仍在阶段3** - GS 训练本体已完成, 正在处理 auto eval 的 transforms 缺失问题。

## [2026-03-22 00:08:35] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: auto eval 的 transforms 问题已修复,新的首阻塞转为父训练进程占用显存导致子评估 OOM

### 已验证现象
- 手动独立执行 `eval_gs` 已成功。
- `train_gs` 内的 auto eval 仍然失败, 错误为 `torch.OutOfMemoryError`。
- 报错中明确显示父训练进程在 auto eval 启动时仍占用约 24.87 GiB 显存。

### 当前主假设
- 主假设: `train_gs` 在 `subprocess.run(eval_gs)` 前没有释放 GPU 大对象, 子进程因此被父进程残留显存挤爆。
- 备选解释: `eval_gs` 一次性把过多原图搬到 GPU, 即使父进程释放显存也仍可能超限。

### 下一步行动
- [ ] 追踪 `train_gs` auto eval 前的显存释放路径。
- [ ] 做最小修复并再次跑入口级 smoke,确认没有 error。

### 状态
**目前仍在阶段3** - 正在处理 auto eval 的跨进程显存占用问题。

## [2026-03-22 00:16:43] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 默认后半程测试运行已完成,本轮真实阻塞已收敛并验证通过

### 已完成事项
- [x] 继续默认后半程真实运行,确认 Stage 2 与默认 LPIPS Stage 3.2 都能启动
- [x] 修复 `run_reconstruction.py` 吞掉 `gs.num_iters` 显式覆盖的问题
- [x] 修复 `eval_gs.py` 对缺失 `gs_video` transforms 的硬依赖
- [x] 修复 `train_gs.py` 在 auto eval 前未释放父进程 CUDA 状态的问题
- [x] 跑通入口级 smoke,确认最终日志中无 `Automatic eval failed` / `Traceback` / `[ERROR]`

### 当前结果
- 默认 Stage 1 成功目录:
  - `/tmp/video_to_world_joint_scene_xhc_bai_fast_run_full_default_20260321_2238/frame_to_model_icp_50_2_offset0_allcache_20260321_2334`
- 最终无 error 的入口级 smoke 目录:
  - `/tmp/video_to_world_joint_scene_xhc_bai_fast_run_full_default_20260321_2238/frame_to_model_icp_50_2_offset0_allcache_20260321_2334/gs_3dgs_lpips_postoomfix_20260322_001016`
- 最终关键日志:
  - `/tmp/video_to_world_xhc_bai_run_reconstruction_postoomfix_20260322_001016.log`

### 状态
**目前在阶段4** - 本轮默认后半程测试运行已完成,正在整理最终交付结论。
## [2026-03-22 00:25:40] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 回答 gs_video transforms 与自动降级语义

### 已确认结论
- `gs_video/0000_extend_transforms.json` 是 DA3 在导出 `gs_video/0000_extend.mp4` 时同步导出的 NeRF-style 相机轨迹文件。
- 文件内包含评估所需的全局内参(`fl_x/fl_y/cx/cy/w/h`)与每帧 `transform_matrix` 相机位姿。
- 缺少该文件时, `eval_gs` 现在会自动关闭 `render_gs_video_path`,仅保留 `input_poses` 与 `optimised_poses` 两条渲染分支。
- 这不会影响 GS 训练本体与最终 checkpoint / ply 结果,但会影响沿 DA3 flythrough 轨迹的那条 novel-view 评估输出。

### 状态
**目前在阶段4** - 代码与验证都已完成,正在向用户交付最终说明与影响分析。
## [2026-03-22 01:22:38] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 继续追踪缺失 transforms 是否可由现有场景数据重建

### 已观察到的现象
- 用户怀疑缺失的 `0000_extend_transforms.json` 对应的是 "Camera moves in a clockwise circular path"。
- 本地源码已确认存在 DA3 相机轨迹生成逻辑,并且 `extend` / `wander` / `smooth` 等模式在第三方实现中有明确分支。

### 当前主假设
- 主假设: 可以基于现有 scene 数据和 DA3 的轨迹生成逻辑,在不重跑完整预处理的前提下补生成一个兼容 `eval_gs` 的 transforms 文件。
- 备选解释: `extend` 轨迹依赖 DA3 推理阶段的中间状态,不能仅靠现有 root 中的最终产物无损复刻。

### 下一步行动
- [ ] 阅读 DA3 的 `camera_trj_helpers.py` 与 `gs_renderer.py`,确认 `extend` / `wander` 的真实轨迹几何含义。
- [ ] 检查当前 scene root 是否具备反推该轨迹所需的位姿和内参。
- [ ] 若证据充分,直接生成缺失的 transforms JSON 并做最小验证。

### 状态
**目前在阶段4** - 正在验证是否能安全补生成 `gs_video/0000_extend_transforms.json`。
## [2026-03-22 01:26:11] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] [记录类型]: 已补生成缺失的 `0000_extend_transforms.json` 并完成动态验证

### 已完成事项
- [x] 阅读 DA3 的 `camera_trj_helpers.py` 与 `gs_renderer.py`,确认 `extend` / `wander` 的真实轨迹几何含义。
- [x] 检查当前 scene root 是否具备反推该轨迹所需的位姿和内参。
- [x] 基于 `exports/npz/results.npz` 补生成 `gs_video/0000_extend_transforms.json`。
- [x] 用 `load_nerf_transforms_json()` 和 `eval_gs --config.max-frames 3` 验证新文件可被评估链路直接使用。

### 当前结论
- `0000_extend_transforms.json` 已成功生成并落盘:
  - `/tmp/video_to_world_joint_scene_xhc_bai_fast_run_full_default_20260321_2238/gs_video/0000_extend_transforms.json`
- 它对应的是 DA3 `extend` 长轨迹,不是单独的纯 circular `wander` 文件。
- 动态验证结果:
  - `eval_gs` 已打印 `Loaded 3 gs_video camera poses from: .../0000_extend_transforms.json`
  - 成功输出 `render_gs_video.mp4`

### 状态
**目前在阶段4** - 补生成与验证已完成,正在向用户交付结果与差异说明。
