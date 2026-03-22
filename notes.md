# 研究笔记

## [2026-03-20 20:36:23] [Session ID: codex-20260320-203623] 笔记: pixi 环境迁移前的仓库现状

### 来源
- 本地仓库文件:
  - `README.md`
  - `pyproject.toml`
  - `AGENTS.md`
- 本地命令:
  - `pixi --version`
  - `rg -n "conda|pixi|pip install|third_party|torch_kdtree|CONDA_PREFIX" -S /workspace/video_to_world`

### 要点
- 当前机器已安装 `pixi 0.65.0`。
- 仓库尚无 `pixi.toml`、`pixi.lock`、`environment.yml` 之类的环境描述文件。
- `README.md` 当前以 `conda create` / `conda activate` 开头,其后大量依赖用 `pip install` 分段安装。
- 第三方安装有几类:
  - git clone + checkout + `pip install -e` 本地源码包
  - 直接从 Git 安装 PyPI 依赖
  - 需要 `--no-build-isolation` 的编译型依赖
  - 可选安装 `torch_kdtree`
- 代码中没有发现直接依赖 `conda` 的运行逻辑,仅 README 有 `CONDA_PREFIX` 示例。

### 初步判断
- 现象: 环境管理入口仍是 `conda + pip` 手工脚本。
- 假设: 这个仓库适合改造成 “`pixi` 管 Python 与基础依赖,`pixi task` 统一第三方安装命令” 的模式。
- 备选解释: 若 `pixi` 对部分 git/path/editable 依赖声明不够稳,则需要退回到 “基础环境用 `pixi`,重型第三方依赖继续由任务内部调用 `python -m pip` 安装”。
- 验证计划: 继续核对 `pixi` 官方对 `pypi-dependencies`、git 源、本地 editable path 和 task 的支持,然后在本地执行 `pixi project validate`。

## [2026-03-20 20:36:23] [Session ID: codex-20260320-203623] 笔记: 本地 pixi 行为验证

### 来源
- 本地临时工程实验:
  - `pixi init --format pixi`
  - `pixi add python=3.10`
  - `pixi add --pypi numpy==1.26.4`
  - `pixi add --pypi --editable "demo @ file://..."`
  - `pixi task add hello 'echo hi'`
- 结果来自 `pixi.toml` 实际输出,不是推测。

### 综合发现
- `pixi 0.65.0` 默认 manifest 结构为:
  - `[workspace]`
  - `[tasks]`
  - `[dependencies]`
- 普通 PyPI 包会写入:
  - `[pypi-dependencies]`
  - 例如 `numpy = "==1.26.4"`
- editable 本地包会写成:
  - `demo = { path = "/abs/path", editable = true }`
- task 可以是简单字符串:
  - `hello = "echo hi"`
- task 也可以是带依赖的表:
  - `b = { cmd = "echo b", depends-on = ["a"] }`
- 聚合 task 可以只写依赖:
  - `all = { depends-on = ["a"] }`

### 对本仓库的意义
- 可以把常规包直接进 manifest。
- 可以把 `gsplat`、`tiny-cuda-nn`、`DepthAnything-3`、`RoMaV2` 这类“需要 git clone / patch / editable / no-build-isolation”的步骤收敛到 task。
- 这样既满足“用 `pixi` 管环境”,又避免首次安装时被尚未 clone 的 `third_party/` 路径卡住。

## [2026-03-20 20:36:23] [Session ID: codex-20260320-203623] 笔记: 实施后的验证结果

### 来源
- 本地命令:
  - `pixi task list`
  - `timeout 90s pixi install`
  - `timeout 20s pixi run python --version`
  - `timeout 20s pixi run python -m ruff --version`

### 要点
- `pixi task list` 成功列出:
  - `format`
  - `install-gsplat`
  - `install-tinycudann`
  - `install-torch-kdtree`
  - `install-torch-stack`
  - `lint`
  - `pin-build-setuptools`
  - `setup`
  - `setup-depth-anything-3`
  - `setup-romav2`
- `pixi install` 没有报 TOML 解析错误,说明 `pixi.toml` 至少在语法和任务结构上是可接受的。
- 仓库根目录生成了 `pixi.lock`,说明 `pixi` 已经成功完成依赖求解并写出锁文件。
- 安装过程中出现:
  - `WARN Skipped running the post-link scripts because run-post-link-scripts = false`
  - 指向 `librsvg` 的 post-link 脚本
- 在当前 90 秒窗口内没有完成完整安装,所以还不能宣称“环境已经完整安装成功”。

### 结论
- 已验证结论:
  - `pixi.toml` 可被本机 `pixi 0.65.0` 识别。
  - 文档和仓库入口已经完成从 `conda` 到 `pixi` 的迁移。
- 尚未完全验证:
  - 首次完整 `pixi install` 到可直接 `pixi run python ...` 的端到端耗时与最终成功结果。

## [2026-03-20 21:55:10] [Session ID: codex-20260320-215510] 笔记: Pixi 多行任务脚本解析失败定位

### 来源
- 本地仓库文件:
  - `pixi.toml`
- 本地命令:
  - `pixi --version`
  - `pixi run -n setup-depth-anything-3`
  - 临时最小复现工程中的 `pixi run broken`
  - 临时修复样例中的 `pixi run via-array`
- `exa_code` 检索:
  - Pixi advanced tasks 文档
  - `pixi run` 文档
  - `prefix-dev/pixi` 中关于 task interpreter 的 PR 说明

### 现象
- 仓库里的 `setup-depth-anything-3`、`setup-romav2`、`install-torch-kdtree` 都是多行 task 字符串。
- `pixi run -n setup-depth-anything-3` 只会打印任务文本,不会触发运行期解析错误。
- 但在最小复现工程中执行:
  - `pixi run broken`
  - 结果稳定报错: `failed to parse shell script` / `Unsupported reserved word`

### 静态证据
- `exa_code` 返回的 Pixi 文档明确说明, task 由 `deno_task_shell` 执行。
- `deno_task_shell` 只支持有限的 bourne-shell 语法。
- 在当前本机 `pixi 0.65.0` 上, `interpreter = "bash"` 仍不是合法字段,会报 `Unexpected keys`。

### 动态证据
- 最小失败样例:
  - task 内容:
    - `if [ -f /etc/hosts ]; then`
    - `  echo ok`
    - `fi`
  - 运行结果:
    - `pixi run broken`
    - 报 `Unsupported reserved word`
- 最小成功样例:
  - task 写法:
    - `cmd = ["bash", "-lc", """..."""]`
  - 运行结果:
    - `pixi run via-array`
    - 输出 `ok`

### 结论
- 已验证结论:
  - 根因不是 `git clone`、`patch` 或路径本身。
  - 真正失败点是: 多行 task 字符串被 `deno_task_shell` 解析时,不支持 `if ... then ... fi`。
  - 在 `pixi 0.65.0` 上,当前可行修法是把复杂脚本显式交给 `bash -lc` 执行。
- 备选方案结论:
  - `interpreter = "bash"` 这条路在当前版本不可用,不能作为本仓库修复方案。

## [2026-03-20 21:59:46] [Session ID: codex-20260320-215510] 笔记: 仓库内验证与网络环境分层

### 来源
- 本地命令:
  - `pixi task list`
  - `pixi run -n setup-depth-anything-3`
  - `pixi run -n setup-romav2`
  - `pixi run -n install-torch-kdtree`
  - `timeout 300s pixi run setup-depth-anything-3`
  - `env | grep -i '^http_proxy\\|^https_proxy\\|^all_proxy\\|^no_proxy' | sort`
  - `timeout 30s env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy git ls-remote https://github.com/ByteDance-Seed/depth-anything-3 HEAD`

### 要点
- 修复后的三个复杂任务都能被 Pixi 正确展开成:
  - `bash -lc "..."`
- 仓库内真实执行 `setup-depth-anything-3` 时,不再出现 `Unsupported reserved word`。
- 当前环境存在以下代理变量:
  - `HTTP_PROXY=http://127.0.0.1:7897`
  - `HTTPS_PROXY=http://127.0.0.1:7897`
  - `ALL_PROXY=socks5h://127.0.0.1:7897`
  - 以及一组小写变量指向 `127.0.0.1:7897`
- 任务失败时的报错已经切换为 Git 网络连接错误。
- 去掉代理后直接 `git ls-remote` 也在 30 秒内超时,说明当前会话对 GitHub 的连通性本身也不足以完成远程拉取验证。

### 结论
- 本次仓库修复已经通过“错误类型变化”得到动态证据支撑:
  - 原问题: Pixi shell 语法解析失败
  - 修复后: 进入 bash 执行,再在网络层失败
- 因此,应把当前剩余阻塞归类为环境网络问题,不要继续围绕 `pixi.toml` 叠补丁。

## [2026-03-20 23:07:10] [Session ID: codex-20260320-225624] 笔记: gsplat 安装失败的根因与修法

### 来源
- 本地命令:
  - `git ls-remote https://github.com/nerfstudio-project/gsplat.git HEAD`
  - `env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy git ls-remote https://github.com/nerfstudio-project/gsplat.git HEAD`
  - `timeout 120s env -u ... pixi run install-gsplat`
  - `timeout 120s pixi run install-gsplat`
- `exa_code` 检索:
  - `gsplat` 官方 README / release 页面
  - pip 官方 `pip install` 文档

### 现象
- 用户原始报错发生在:
  - `pip` 内部调用 `git clone --filter=blob:none --quiet ...`
- 报错文本:
  - `TLS connect error`
  - `unexpected eof while reading`
- 当前 shell 中同时存在两套 loopback 代理:
  - `127.0.0.1:7897`
  - `127.0.0.1:7897`

### 静态证据
- `gsplat` 官方 README 提供两种安装入口:
  - `pip install gsplat`
  - `pip install git+https://github.com/nerfstudio-project/gsplat.git`
- pip 官方文档确认:
  - 支持从 VCS URL 安装
  - 也支持从本地 project path 安装
- `gsplat` 官方 release 页面显示:
  - `v1.5.3` 对应 commit `937e29912570c372bed6747a5c9bf85fed877bae`

### 动态证据
- 在当前代理环境下:
  - `git ls-remote ...`
  - 结果: 直接失败,并提示访问 `127.0.0.1:7897` 被拒绝
- 去掉代理后:
  - 同样的 `git ls-remote ...`
  - 结果: 成功返回 `HEAD`
- 去掉代理后运行:
  - `timeout 120s env -u ... pixi run install-gsplat`

## [2026-03-21 20:11:30] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 笔记: `flashvsr_reference_xhc_bai` 真实运行的 DA3 下载链路验证

### 来源
- 本地命令:
  - `find /root/.cache/huggingface -maxdepth 5 ...`
  - `rg -n "DepthAnything3|from_pretrained|model_name|preprocess_model" ...`
  - `pixi run python - <<'PY' ... hf_hub_download(...)`
  - `curl -I -L https://huggingface.co/.../config.json`
  - `curl -I -L https://hf-mirror.com/.../config.json`

### 现象
- `source/flashvsr_reference_xhc_bai/full_scale2x` 的真实联合入口已经能跑到:
  - Stage 0 拆帧
  - `frames_subsampled`
  - `DepthAnything3.from_pretrained(...)`
- 本机没有现成的 `DA3NESTED-GIANT-LARGE` 本地完整权重目录。
- `7890` 代理下:
  - `curl` 访问官方域名和 `hf-mirror.com` 都报 `SSL EOF`
  - `huggingface_hub` 也会报 `SSL EOF` 或 `client has been closed`

### 静态证据
- `run_multiview_reconstruction.py` 暴露了:
  - `--preprocess-model-name`
- `preprocess_video.py` 参数说明明确写的是:
  - `DA3 model name/path (HuggingFace repo or local).`
- `DepthAnything3` 继承 `PyTorchModelHubMixin`,说明它本身走的是 Hugging Face Hub 风格加载。

### 动态证据
- 去掉代理后:
  - `HF_ENDPOINT=https://hf-mirror.com pixi run python - <<'PY' ... hf_hub_download(..., filename='config.json')`
  - 成功下载到:
    - `/root/.cache/huggingface/hub/models--depth-anything--DA3NESTED-GIANT-LARGE/snapshots/8615eefb62f2db4f8d6ebaa59160086981672829/config.json`
- 同样条件下:
  - `hf_hub_download(..., filename='model.safetensors', dry_run=True)`
  - 成功返回:
    - `commit_hash='8615eefb62f2db4f8d6ebaa59160086981672829'`
    - `file_size=6759558100`

### 当前结论
- 当前主结论:
  - 官方 Hugging Face 域名不可用,但 `hf-mirror.com` 在去代理条件下对 `huggingface_hub` 是可用的。
- 这意味着:
  - 当前最值得推进的路径是 `HF_ENDPOINT=https://hf-mirror.com`
  - 而不是继续尝试 `7890` 代理

## [2026-03-21 20:51:53] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 笔记: ModelScope 上的 `depth-anything` 检索结果

### 来源
- 站点公开描述:
  - `https://www.modelscope.cn/opensearch.xml`
- 站外检索:
  - `site:modelscope.cn depth-anything modelscope.cn`
  - `site:modelscope.cn "Depth Anything 3" modelscope.cn`
  - `site:modelscope.cn/models "DA3NESTED-GIANT-LARGE"`

### 现象
- `modelscope.cn` 的搜索和模型列表页主要是前端渲染。
- 直接 `curl`:
  - 只能拿到 HTML 壳页面
  - 不能像传统 SSR 页面那样直接看到结果列表

### 已找到的相关页面
- `https://modelscope.cn/models/onnx-community/depth-anything-v3-small`
- `https://modelscope.cn/models/depth-anything/Metric-Video-Depth-Anything-Base`
- `https://modelscope.cn/models/cubeai/depth_anything_vitl14`
- `https://modelscope.cn/models/popatry/Depth-Anything-V2_Safetensors`
- `https://modelscope.cn/models/fudanU123/depth_anything_small_hf`

### 未找到的精确匹配
- 目前还没有查到与当前仓库代码默认模型名精确对应的页面:
  - `depth-anything/DA3NESTED-GIANT-LARGE`

### 当前结论
- 不能据此断言 ModelScope 完全没有 DA3。
- 但可以确认:
  - 我这边目前只找到了相关 `depth-anything` 模型
  - 还没找到当前流水线精确需要的 DA3 nested giant large 模型页面

## [2026-03-20 23:09:40] [Session ID: codex-20260320-230940] 笔记: 联合多视角入口的当前会话动态验证

### 来源
- 本地命令:
  - `timeout 60s pixi run python --version`
  - `timeout 60s pixi run python -m unittest discover -s tests`
  - `timeout 60s pixi run python run_multiview_reconstruction.py --views-root source/flashvsr_reference_xhc_bai/full_scale2x --scene-root /tmp/video_to_world_joint_scene --dry-run --config.mode fast`
  - `timeout 60s pixi run python preprocess_multiview.py --views-root source/flashvsr_reference_xhc_bai/full_scale2x --scene-root /tmp/video_to_world_joint_scene_preprocess --dry-run`
- 产物文件:
  - `/tmp/video_to_world_joint_scene/multiview_reconstruction_summary.json`

### 现象
- `pixi run python --version` 已能立即返回 `Python 3.10.20`。
- 测试集在 `pixi` 环境内全部通过,共 6 个测试。
- 联合入口 dry-run 摘要里明确列出了 `0..5` 六个视角,并且 `scene_stem` 一致为 `xhc-bai_97e474c6`。
- 联合入口输出的重建命令只有一条 `run_reconstruction.py --config.root-path /tmp/video_to_world_joint_scene --config.mode fast --config.dry-run`。

### 综合发现
- 已验证结论:
  - 现在的联合入口语义是“多视角合入一个 scene_root”,不是“每个视角各自产出一个 scene_root”。
  - `preprocess_multiview.py` 的 dry-run 已能为每个视角生成独立 Stage 0 命令,说明视角发现与 per-view 落点规划正常。
  - `run_multiview_reconstruction.py` 的 dry-run 已能把这些视角再汇总为一次共享重建调用,说明 orchestration 口径正确。
- 仍未验证:
  - 非 dry-run 模式下真实执行 DA3 后,合并 `results.npz` 时是否会遇到跨视角 shape 不一致。
  - Stage 1/2/3 对联合后帧序列的质量表现如何,这属于后续质量验证范畴。

## [2026-03-20 23:47:52] [Session ID: codex-20260320-234752] 笔记: docs/cmd.md 的内容边界与参数校对

### 来源
- 本地文件:
  - `docs/cmd.md`
  - `run_multiview_reconstruction.py`
  - `preprocess_multiview.py`
- 本地命令:
  - `timeout 60s pixi run python run_multiview_reconstruction.py --help`
  - `timeout 60s pixi run python preprocess_multiview.py --help`

### 要点
- 当前 `docs/cmd.md` 重点服务的是“联合多视角入口怎么用”。

## [2026-03-21 23:52:00] [Session ID: codex-20260321-234700] 笔记: tiny-cuda-nn 编译失败时的 CUDA 布局证据

### 来源
- 本地命令:
  - `command -v nvcc`
  - `find /usr/local/cuda /usr -name nvcc -o -name nvrtc.h -o -name cusparse.h`
  - `ls -ld /usr/local/cuda /usr/local/cuda/bin /usr/local/cuda/include /usr/local/cuda/targets/x86_64-linux/include`
  - `pixi run python` 内检查 `torch.utils.cpp_extension.CUDA_HOME`
  - `pixi run python` 内检查 `nvidia.cuda_nvrtc` 与 `nvidia.cusparse` 包路径
  - 读取 `/tmp/tcnn-clone-test.HtOWVH/bindings/torch/setup.py`

### 现象
- 当前 shell 的 `PATH` 里没有 `/usr/local/cuda/bin`,所以直接 `command -v nvcc` 为空。
- 但系统上真实存在:
  - `/usr/local/cuda/bin/nvcc`
  - `/usr/local/cuda-12.4/bin/nvcc`
- `torch.utils.cpp_extension.CUDA_HOME` 在 `pixi` 环境内返回 `/usr/local/cuda`。
- 系统 CUDA include 目录里能看到:
  - `cuda_runtime.h`
  - `cuda_runtime_api.h`
- 但系统目录下没有搜到:
  - `nvrtc.h`
  - `cusparse.h`
- 这两个头文件实际位于:
  - `/workspace/video_to_world/.pixi/envs/default/lib/python3.10/site-packages/nvidia/cuda_nvrtc/include/nvrtc.h`
  - `/workspace/video_to_world/.pixi/envs/default/lib/python3.10/site-packages/nvidia/cusparse/include/cusparse.h`
- 对应共享库也位于 `site-packages/nvidia/.../lib` 下。

### 静态分析
- tiny-cuda-nn 的 `bindings/torch/setup.py` 有两个关键行为:
  - 它用 `os.system("nvcc --version")` 决定 CUDA 版本,进而决定是否切到 `C++17`
  - 它依赖 `CUDAExtension(...)` 自动带入 CUDA include / lib 路径,自身没有额外把 `pixi` 环境里的 `nvidia/cuda_nvrtc` 和 `nvidia/cusparse` 头文件目录加进去
- 这意味着当前失败不是“系统完全没有 CUDA”,而是“构建入口只看到了系统 CUDA 的一部分,没看到 `pixi` 提供的额外开发头和库”。

### 当前结论
- 已验证结论:
  - `nvcc not found` 的直接原因是 `PATH` 没有带 `/usr/local/cuda/bin`
  - `nvrtc.h` / `cusparse.h` 缺失的直接原因不是机器完全没文件,而是编译器搜索路径没有覆盖 `pixi` 环境里的 NVIDIA wheel 路径
- 仍待动态验证:
  - 只通过导出 `PATH`、`CUDA_HOME`、`CPATH`、`LIBRARY_PATH`、`LD_LIBRARY_PATH` 是否就足以让 tiny-cuda-nn 编译通过

## [2026-03-22 00:02:00] [Session ID: codex-20260321-234700] 笔记: 手动注入 CUDA 环境后的动态结果

### 来源
- 本地命令:
  - 在单次执行里手动导出:
    - `PATH=/usr/local/cuda/bin:$PATH`
    - `CUDA_HOME=/usr/local/cuda`
    - `CPATH` / `CPLUS_INCLUDE_PATH` 指向系统 CUDA include + `nvidia/cuda_nvrtc/include` + `nvidia/cusparse/include`
    - `LIBRARY_PATH` / `LD_LIBRARY_PATH` 指向系统 CUDA lib + `nvidia/cuda_nvrtc/lib` + `nvidia/cusparse/lib`
  - 然后运行:
    - `pixi run install-tinycudann`

### 动态证据
- 构建日志已明确出现:
  - `nvcc: NVIDIA (R) Cuda compiler driver`
  - `Detected CUDA version 12.4`
  - `Targeting C++ standard 17`
- 这说明:
  - `nvcc not found` 已被消除
  - tiny-cuda-nn 已正确切到 `C++17`
  - `nvrtc.h` / `cusparse.h` 已不再是首个失败点
- 新的首个真实失败点变成:
  - `fatal error: cublas_v2.h: 没有那个文件或目录`

### 结论
- 已验证结论:
  - 之前的修复方向正确,问题确实在“构建入口缺少完整 CUDA / NVIDIA include+lib 暴露”
- 新的更具体假设:
  - 不应只手工补 `cuda_nvrtc` 和 `cusparse`
  - 应该自动把 `pixi` 环境中 `site-packages/nvidia/*/include` 与 `site-packages/nvidia/*/lib` 全量拼入搜索路径
- 这样可以避免后面继续一个头文件一个头文件地追 `cublas`、`curand`、`cusolver` 等依赖

## [2026-03-22 00:19:00] [Session ID: codex-20260321-234700] 笔记: tiny-cuda-nn 最终成功的构建条件

### 来源
- 本地命令:
  - `pixi run install-tinycudann`
  - `pixi run setup`
  - `pixi run python -c 'import tinycudann'`
- 本地文件:
  - `scripts/install_tinycudann.sh`

### 关键发现
- 光有 `CPATH` / `CPLUS_INCLUDE_PATH` 还不够。
- `pixi` 的 NVIDIA wheel 库目录里多数只有:
  - `libnvrtc.so.12`
  - `libcublas.so.12`
  - `libcusparse.so.12`
- 但链接器处理 `-lnvrtc` / `-lcublas` / `-lcusparse` 时需要:
  - `libnvrtc.so`
  - `libcublas.so`
  - `libcusparse.so`
- 所以最终有效修法必须同时包含两部分:
  - 头文件层: 收集 `site-packages/nvidia/*/include`
  - 链接层: 为 `site-packages/nvidia/*/lib/lib*.so.*` 生成临时无版本别名,并通过 `LDFLAGS` 加 `-L...` 与 `-Wl,-rpath,...`

### 最终验证
- `pixi run install-tinycudann`
  - 成功构建并安装 `tinycudann-2.0`
- `pixi run setup`
  - 成功完成整条安装链路
- `pixi run python` 导入 `tinycudann`
  - 通过,说明这次链接修复不只是“能编译”,运行时动态库查找也没炸
- 文档没有扩散去写完整单视频流程,这样边界更清楚。
- 文档里保留了用户当前真实目录 `source/flashvsr_reference_xhc_bai/full_scale2x`,方便直接套用。
- 文档中的关键参数与 `--help` 输出一致:
  - `run_multiview_reconstruction.py`: `--views-root`、`--scene-root`、`--view-ids`、`--dry-run`
  - `preprocess_multiview.py`: `--views-root`、`--scene-root`、`--view-ids`、`--dry-run`

### 结论
- 已验证结论:
  - `docs/cmd.md` 里的命令和当前联合入口参数一致。
  - 这份文档已经足够回答“我要怎么用”这个问题。
- 当前没有新增代码风险,主要是文档层补充。
  - 结果: 不再出现 TLS EOF,任务进入正常 clone 阶段
- 应用修复后,在保留当前坏代理环境的情况下运行:
  - `timeout 120s pixi run install-gsplat`
  - 结果: helper 会先打印被清理的 loopback 代理变量,然后进入 `git clone third_party/gsplat`

### 结论
- 已验证结论:
  - 原始失败点在环境代理,不是 `gsplat` 仓库本身。
  - 本机对 GitHub 的直连是可用的,只是被坏代理变量盖住了。
  - 将 `install-gsplat` 改成“显式 clone 固定 commit + 本地 path 安装”更稳,也更方便后续复用和排障。

## [2026-03-21 00:29:11] [Session ID: codex-20260321-002404] 笔记: DepthAnything-3 本地优先安装路径修复

### 来源
- 用户提供的本地仓库:
  - `/workspace/depth-anything-3`
- 本地命令:
  - `git -C /workspace/depth-anything-3 rev-parse HEAD`
  - `git -C /workspace/depth-anything-3 cat-file -t 2c21ea...`
  - `git -C third_party/depth-anything-3 rev-parse HEAD`
  - `timeout 180s pixi run setup-depth-anything-3`
- 代码验证:
  - `python3 -m unittest tests/test_pixi_manifest.py`
  - `python3 -m unittest discover -s tests`

### 现象
- 用户失败日志发生在 `git -C third_party/depth-anything-3 fetch --tags --force`。
- 但本地现状显示:
  - `/workspace/depth-anything-3` 已在目标 commit `2c21ea...`
  - `third_party/depth-anything-3` 也已在目标 commit `2c21ea...`
- 也就是说,任务失败时访问远端并不是必要条件。

### 第一轮假设与回滚
- 第一轮假设:
  - 只要在 `pixi.toml` 里加上“本地 commit 优先,本地镜像次之”的 bash 分支就够了。
- 推翻该假设的新证据:
  - 跑任务后报 `empty string is not a valid pathspec`
  - 直接在 shell 手动执行同样脚本则完全正常
- 新结论:
  - 问题不是 Git 逻辑本身,而是 Pixi task 字符串会预展开 `$target_commit` 这类局部 shell 变量
  - 因此复杂脚本必须挪到独立 `bash` 文件里

### 最终方案
- 新增 `scripts/setup_depth_anything_3.sh`
- 执行优先级:
  - 当前 `third_party` repo 已有目标 commit -> 直接用
  - 否则,本地镜像 `/workspace/depth-anything-3` 有目标 commit -> 从本地镜像 clone / fetch
  - 否则才回退到 GitHub
- `pixi.toml` 中仅保留:
  - `setup-depth-anything-3 = "bash scripts/setup_depth_anything_3.sh"`

### 结论
- 已验证结论:
  - 用户提供的本地 clone 非常有用,而且已经成为正式兜底路径的一部分。
  - 新路径下 `setup-depth-anything-3` 已完整成功。

## [2026-03-20 21:54:01] [Session ID: codex-20260320-203623] 笔记: 多视角输入目录现状与约束

### 来源
- 本地目录扫描:
  - `find source/flashvsr_reference_xhc_bai -maxdepth 3`
  - `find .../full_scale2x -path '*/rgb/*.mp4'`
- 元数据:
  - `flashvsr_reference_summary.json`
  - `full_scale2x/0/manifests/xhc-bai_97e474c6.json`
- 代码阅读:
  - `run_reconstruction.py`
  - `preprocess_video.py`

### 现象
- `full_scale2x/0..5/rgb/` 下各有且仅有一个 `xhc-bai_97e474c6.mp4`。
- 每个视角 manifest 中的 `scene_stem` 都是 `xhc-bai_97e474c6`,但 `view_id` 不同。
- `run_reconstruction.py` 的输入模型是:
  - 单个 `--config.input-video`
  - 或单个 `--config.frames-dir`
  - 或单个 `--config.root-path`
- 下游各阶段都基于单个 `root_path/exports/npz/results.npz` 运作。

### 当前判断
- 静态证据:
  - `data/data_loading.py`、`frame_to_model_icp.py`、`train_inverse_deformation.py`、`train_gs.py` 都围绕单个 `root_path` 和单个 `results.npz` 展开。
- 候选结论:
  - 当前仓库没有现成的“多视频联合输入”通道。
  - 第一阶段应实现批处理 orchestrator,而不是直接修改底层重建算法。

## [2026-03-20 21:54:01] [Session ID: codex-20260320-203623] 笔记: 多视角批处理入口验证结果

### 来源
- 本地验证:
  - `python3 -m py_compile run_multiview_reconstruction.py tests/test_run_multiview_reconstruction.py`
  - `python3 -m unittest ...`
  - `python3 run_multiview_reconstruction.py --views-root source/flashvsr_reference_xhc_bai/full_scale2x --batch-root /tmp/... --summary-path /tmp/.../summary.json --dry-run --config.mode fast`
- Mermaid 验证:
  - `beautiful-mermaid-rs --ascii`

### 已验证结论
- 新脚本能正确扫描 `source/flashvsr_reference_xhc_bai/full_scale2x/0..5/rgb/*.mp4`。
- 新脚本能从 manifest 读取 `scene_stem = xhc-bai_97e474c6`。
- dry-run 下生成的 per-view 输出目录形如:
  - `/tmp/.../out/xhc-bai_97e474c6/view_0`
  - `/tmp/.../out/xhc-bai_97e474c6/view_1`
  - ...
  - `/tmp/.../out/xhc-bai_97e474c6/view_5`
- 新脚本会把额外 CLI 参数继续转发给 `run_reconstruction.py`,例如 `--config.mode fast`。

### 仍未验证部分
- 尚未执行真实的重型重建阶段,因此没有验证 GPU 环境、DA3、RoMaV2、gsplat、tiny-cuda-nn 在这 6 个视角上的完整端到端耗时与稳定性。

## [2026-03-20 22:54:43] [Session ID: codex-20260320-203623] 笔记: 上一方案被用户需求推翻

### 现象
- 用户明确指出,目标是“一个场景的多镜头联合处理”。

### 结论
- 之前实现的 `run_multiview_reconstruction.py` 批处理版只能得到多个独立结果。
- 它不满足“单一 canonical scene”的目标。

### 新方案约束
- 不能再让 `view_0..5` 各自产出一个 `scene_root` 作为最终结果。
- 应改成:
  - 每个视角可有自己的中间 DA3 子目录
  - 但最终要合并成一个统一 `scene_root`
  - 然后只对这个统一 `scene_root` 跑 Stage 1/2/3

## [2026-03-20 22:54:43] [Session ID: codex-20260320-203623] 笔记: 联合单场景版本的验证结论

### 已验证结论
- 新入口 `run_multiview_reconstruction.py` 不再为每个视角单独调用一次完整重建。
- 新入口现在只会生成:
  - 一个联合预处理命令 `preprocess_multiview.py`
  - 一个单场景重建命令 `run_reconstruction.py --config.root-path <scene_root>`
- `preprocess_multiview.py` 会把 per-view 中间结果整理到:
  - `<scene_root>/per_view/view_<id>/...`
- 然后在联合根目录产出:
  - `<scene_root>/exports/npz/results.npz`
  - `<scene_root>/frames_subsampled/`
  - `<scene_root>/preprocess_frames.json`
  - `<scene_root>/preprocess_multiview_summary.json`

### 仍未验证部分
- 还没有执行真实的 DA3 / Stage 1 / Stage 2 / Stage 3 重型流程。
- 因此当前证据是:
  - 联合输入的编排逻辑已经打通
  - 真实 GPU 端到端效果仍待下一轮运行验证
## [2026-03-21 12:31:05] [Session ID: ca9da93f-9a71-4a7a-a8b3-f1e3f04ca932] 笔记: gsplat 构建失败的首轮证据

### 来源
- 本地命令:
  - `git -C third_party/gsplat submodule status`
  - `find third_party/gsplat/gsplat/cuda/csrc/third_party -maxdepth 3 -type f`
  - `find third_party/gsplat -path '*glm/gtc/type_ptr.hpp'`
- 本地文件:
  - `third_party/gsplat/setup.py`
  - `third_party/gsplat/gsplat/cuda/include/Common.h`
  - `third_party/gsplat/docs/DEV.md`
  - `pixi.toml`

### 现象
- 构建报错统一落在 `Common.h` 的 `#include <glm/gtc/type_ptr.hpp>`。
- `setup.py` 把 `glm` include path 写死为:
  - `gsplat/cuda/csrc/third_party/glm`
- 当前本地 `third_party/gsplat` 中:
  - `glm` 目录没有任何头文件
  - `git submodule status` 显示该子模块前缀为 `-`,表示未初始化
- 官方 `docs/DEV.md` 明确写了:
  - `git clone --recurse-submodules URL`

### 当前判断
- 主假设:
  - 仓库级安装任务缺少 `submodule update --init --recursive`,因此本地 checkout 不完整。
- 备选解释:
  - 固定 commit 与当前 `setup.py` 预期路径不一致,即使补子模块也可能有第二层问题。

### 下一步最小验证
- 先补一条最小命令:
  - `git -C third_party/gsplat submodule update --init --recursive`
- 然后重新检查:
  - `find third_party/gsplat -path '*glm/gtc/type_ptr.hpp'`
- 如果文件出现,就可以把修复点收敛到 `pixi.toml` 的 `install-gsplat` 任务。

## [2026-03-21 12:43:56] [Session ID: codex-20260321-123719] 笔记: gsplat 编译失败的第二轮证据收敛

### 来源
- 本地命令:
  - `timeout 60s pixi run python - <<'PY' ...`
  - `env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy pixi run bash -lc 'python -m pip install -v --no-build-isolation --no-deps third_party/gsplat'`
  - `find third_party/gsplat/gsplat/cuda/csrc/third_party/glm -maxdepth 3 -type f`
  - `git -C third_party/gsplat submodule foreach --recursive 'pwd; git status --short --branch; git rev-parse --verify HEAD'`
  - `env -u ... git -C third_party/gsplat submodule update --init --recursive`

### 现象
- `pixi` 环境里:
  - `torch=2.10.0+cu128`
  - `torch.version.cuda=12.8`
  - `cuda_available=True`
  - `CUDA_HOME=<unset>`
  - `nvcc_path=<missing>` 但实际编译时 `torch` 仍找到了 `/usr/local/cuda/bin/nvcc`
- 重新抓完整构建日志后,首个真实失败点是:
  - `Common.h:5:10: fatal error: glm/gtc/type_ptr.hpp: 没有那个文件或目录`
- 当前 `third_party/gsplat/gsplat/cuda/csrc/third_party/glm` 目录里只有一个 `.git` 文件,没有任何头文件。
- `git submodule status --recursive` 表面上显示了 pinned commit:
  - `33b4a621... gsplat/cuda/csrc/third_party/glm ()`
- 但真正进入子模块执行 `git rev-parse --verify HEAD` 会报:
  - `fatal: 需要一个单独的版本`
  - 说明这是一个坏掉的子模块工作树,不是可用 checkout。
- 在这个坏状态下重新执行:
  - `git -C third_party/gsplat submodule update --init --recursive`
  - 会直接失败:
    - `fatal: 需要一个单独的版本`
    - `fatal: 无法在子模组路径 'gsplat/cuda/csrc/third_party/glm' 中找到当前版本`

### 当前判断
- 主假设:
  - 根因已经收敛到 `gsplat` 的 `glm` 子模块处于“目录存在但 checkout 损坏”的状态。
  - 现有 `install-gsplat` 没有在 pip build 前验证 `glm/gtc/type_ptr.hpp` 是否真实存在,所以用户最终只看到了下游 `ninja` 编译失败。
- 备选解释:
  - 网络当前也无法稳定访问 GitHub,因此即使简单补一条 `submodule update`,也不一定能自动恢复。
  - 这意味着修复不能只依赖“再拉一次”,还需要更清楚的预检和更稳的坏状态自恢复逻辑。

### 修复方向
- 把 `install-gsplat` 从 `pixi.toml` 的 inline task 抽成独立脚本。
- 在脚本里先做三件事:
  - 复用已有 checkout,只有缺 commit 时才 fetch
  - 检测 `glm` 头文件是否存在,若子模块坏掉则先清理旧状态再重建
  - 如果重建后仍缺头文件,就提前报一个明确错误,不要继续落到 `ninja` 才炸

## [2026-03-21 14:45:13] [Session ID: codex-20260321-123719] 笔记: glm 本地兜底路径验证成功

### 来源
- 本地命令:
  - `find /workspace /opt /usr/include /usr/local/include -path '*/glm/gtc/type_ptr.hpp'`
  - `timeout 20s env -u ... pixi run install-gsplat`
  - `timeout 420s env -u ... pixi run install-gsplat`
  - `timeout 30s pixi run python - <<'PY' ... import gsplat ...`

### 现象
- 去掉代理后:
  - `git ls-remote https://github.com/g-truc/glm.git HEAD`
  - 30 秒内仍会超时
- 但本机其实存在多个可复用的 `glm` 头文件源,例如:
  - `/workspace/Human3R/.pixi/envs/cuda-moge/lib/python3.11/site-packages/gsplat/cuda/csrc/third_party/glm`
  - `/workspace/dropgaussion/submodules/diff-gaussian-rasterization_fastgs/third_party/glm`
- 改完脚本后,真实探针输出已变为:
  - `Using local glm headers from ...`
  - `glm headers restored successfully`
- 再继续完整执行 `pixi run install-gsplat`,最终输出:
  - `Successfully built gsplat`
  - `Successfully installed gsplat-1.5.3 ...`
- 安装后导入验证:
  - `pixi run python - <<'PY' import gsplat; print(gsplat.__version__)`
  - 输出 `1.5.3`

### 结论
- 当前机器上的真实主阻塞不是 `gsplat` 主仓库本身,而是 `g-truc/glm` 子模块访问慢/不可达。
- 对这种 header-only 依赖,优先复用本地现成副本,比一味延长 GitHub clone timeout 更稳。

## [2026-03-21 14:59:14] [Session ID: codex-20260321-123719] 笔记: continuous-learning 六文件摘要

## 六文件摘要（用于决定如何沉淀知识）
- 涉及的上下文集（默认 / 支线后缀）：
  - 默认六文件
  - 未发现带统一后缀的支线上下文集
  - 未发现需要本轮归档的历史版本文件
- 任务目标（task_plan.md）：
  - 把 `gsplat` 安装失败从“误导性的晚期 `ninja` 报错”收敛到真实根因,并在当前机器上完成真实安装
- 关键决定（task_plan.md）：
  - 不再只依赖 `git submodule status`
  - 将 `install-gsplat` 抽成独立脚本
  - 对 `glm` 这种 header-only 依赖,优先复用本地副本而不是一味等待上游子模块 clone
- 关键发现（notes.md）：
  - `glm/gtc/type_ptr.hpp` 缺失才是首个真实失败点
  - `git submodule status` 可能“表面正常,实际损坏”
  - 当前机器访问 `g-truc/glm` 会超时,但本机已有可复用的 `glm` 头文件树
- 实际变更（WORKLOG.md）：
  - 新增 `scripts/install_gsplat.sh`
  - 为 `install-gsplat` 增加坏子模块修复和本地 `glm` fallback
  - 新增 / 更新测试覆盖
- 支线组摘要（如有, 按后缀分别写）：
  - 无
- 暂缓事项 / 后续方向（LATER_PLANS.md，如有）：
  - 与本次 `gsplat` 修复直接相关的后续事项已完成,无需保留额外待办
- 错误与根因（ERRORFIX.md，如有）：
  - `RuntimeError: Error compiling objects for extension` 是误导性的晚期现象
  - 真实根因是 `glm` 子模块损坏或上游超时,且安装脚本缺少关键头文件预检与本地 fallback
- 重大风险 / 灾难点 / 重要规律（EPIPHANY_LOG.md，如有）：
  - 对会参与编译的 third-party 子模块,关键文件探针比 `submodule status` 更可靠
  - 对 header-only 依赖,本地副本本身就是可利用的缓存层
- 可复用点候选（1-3 条）：
  - `gsplat` 构建时 `glm/gtc/type_ptr.hpp` 缺失的排障流程
  - 坏子模块工作树的 `deinit + rm -rf + sync + update` 恢复模式
  - 对 header-only 第三方依赖采用本地副本 fallback 的思路
- 最适合写到哪里：
  - `skill`
  - `README.md`
  - `AGENTS.md`
- 需要同步的现有 `docs/` / `specs/` / plan 文档：
  - `README.md`
  - `AGENTS.md`
  - 已检查 `docs/cmd.md` 与 `specs/multiview_joint_pipeline.md`,无需同步
- 是否需要新增或更新 `docs/` / `specs/` / plan 文档：
  - 是
  - 更新 `README.md` 与 `AGENTS.md` 的 `gsplat` 安装说明
- 是否提取/更新 skill：
  - 是
  - 这次结论包含不明显、已验证、跨项目可复用的 `gsplat + glm` 排障模式
## [2026-03-21 22:12:38] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 笔记: `source/flashvsr_reference_xhc_bai` 后半程真实测试运行的动态证据

## 来源

### 来源1: 真实重建日志
- 文件: `/tmp/video_to_world_xhc_bai_run_reconstruction_nroma_20260321_2201.log`
- 关键命令:
  - `pixi run python run_reconstruction.py --config.root-path /tmp/video_to_world_joint_scene_xhc_bai_fast_run_local_da3_20260321_2142 --config.mode fast --config.stage1.roma.no-use-roma-matching --config.stage1.out-suffix _nroma_20260321_2201`
- 要点:
  - `Stage 1 produced: frame_to_model_icp_50_2_offset0_nroma_20260321_2201`
  - `Skipping Stage 2`
  - `Round-trip validation summary | direct RMSE mean/median/max: 8.647630e-03 / 8.625552e-03 / 1.022871e-02 | nn RMSE mean/median/max: 8.406501e-03 / 8.337596e-03 / 9.854057e-03`
  - `Using inverse deformation: .../inverse_deformation`

### 来源2: GS 短程测试跑日志
- 文件: `/tmp/video_to_world_xhc_bai_train_gs_lpips0_test_20260321_2210.log`
- 关键命令:
  - `pixi run python -m train_gs --config.root-path /tmp/video_to_world_joint_scene_xhc_bai_fast_run_local_da3_20260321_2142 --config.run frame_to_model_icp_50_2_offset0_nroma_20260321_2201 --config.global-opt-subdir after_non_rigid_icp --config.original-images-dir /tmp/video_to_world_joint_scene_xhc_bai_fast_run_local_da3_20260321_2142/frames_subsampled --config.inverse-deform-dir /tmp/video_to_world_joint_scene_xhc_bai_fast_run_local_da3_20260321_2142/frame_to_model_icp_50_2_offset0_nroma_20260321_2201/inverse_deformation --config.renderer 3dgs --config.out-dir /tmp/video_to_world_joint_scene_xhc_bai_fast_run_local_da3_20260321_2142/frame_to_model_icp_50_2_offset0_nroma_20260321_2201/gs_3dgs_lpips0_test_20260321_2210 --config.lpips-weight 0 --config.num-iters 100 --config.no-auto-eval`
- 要点:
  - `Output directory: .../gs_3dgs_lpips0_test_20260321_2210`
  - `Saved checkpoint: .../checkpoint_000099.pt`
  - `Eval [step 99]: avg PSNR = 19.47 dB`
  - `Training complete. Final model: .../model_final.pt`
  - `Wrote 3DGS PLY .../splats_3dgs.ply (2326020 splats, sh_degree=3)`

### 来源3: 产物落盘检查
- 本地命令:
  - `find .../frame_to_model_icp_50_2_offset0_nroma_20260321_2201 -maxdepth 2 ...`
  - `ls -lah .../gs_3dgs_lpips0_test_20260321_2210`
- 要点:
  - `inverse_deformation/inverse_local.pt` 已存在
  - `gs_3dgs_lpips0_test_20260321_2210/model_final.pt` 已存在
  - `gs_3dgs_lpips0_test_20260321_2210/eval_000099/` 已存在
  - `gs_3dgs_lpips0_test_20260321_2210/splats_3dgs.ply` 已存在

## 综合发现

### 现象
- Hugging Face / DA3 已经不再是后半程阻塞。
- 真实后半程先后暴露了两个新的外部下载点:
  - Stage 1 的 `romav2.pt`
  - Stage 3.2 的 `vgg16-397923af.pth`

### 已验证结论
- 对测试运行优先路径而言:
  - `--config.stage1.roma.no-use-roma-matching` 可以让 Stage 1 真实跑通
  - `train_gs` 里把 `lpips_weight` 设为 `0` 可以绕过 VGG 下载,并继续完成一轮短程 3DGS 训练
- 这套数据当前已经至少真实完成:
  - 联合 Stage 0
  - Stage 1
  - Stage 3.1
  - Stage 3.2 的 100 iter 短程 3DGS 训练 + 内置评估 + 最终 PLY 导出
## [2026-03-21 22:37:30] [Session ID: codex-20260321-223500] 笔记: DINOv3 torch hub 缓存阻塞的验证与解除

## 来源

### 来源1: RoMaV2 静态代码
- 文件:
  - `third_party/RoMaV2/src/romav2/features.py`
  - `third_party/RoMaV2/src/romav2/romav2.py`
- 要点:
  - `romav2.pt` 通过 `torch.hub.load_state_dict_from_url(...)` 读取
  - DINOv3 仓库代码通过 `torch.hub.load(repo_or_dir="facebookresearch/dinov3:adc254450203739c8149213a7a69d8d905b4fcfa", ...)` 读取

### 来源2: torch.hub 本地实现
- 命令:
  - `pixi run python` + `inspect.getsource(torch.hub._get_cache_or_reload)`
- 要点:
  - 只要本地存在目录 `/root/.cache/torch/hub/facebookresearch_dinov3_adc254450203739c8149213a7a69d8d905b4fcfa`, `torch.hub` 就会直接走缓存
  - 下载时临时 zip 名是 `<commit>.zip`,但真正决定是否复用缓存的是 repo 目录名

### 来源3: 动态网络探针与最小初始化验证
- 关键命令:
  - `curl -I -L https://ghproxy.net/https://github.com/facebookresearch/dinov3/archive/adc254450203739c8149213a7a69d8d905b4fcfa.zip`
  - `curl -L ... -o /tmp/dinov3_adc254450203739c8149213a7a69d8d905b4fcfa.zip`
  - `RoMaV2(RoMaV2.Cfg(compile=False))`
  - `lpips.LPIPS(net='vgg')`
- 要点:
  - 当前 shell 仍残留坏代理:
    - `http_proxy=http://127.0.0.1:7897`
    - `https_proxy=http://127.0.0.1:7897`
    - `all_proxy=socks5://127.0.0.1:7897`
  - 直连 GitHub 并不稳定,用户提供的 `7890` 代理在这条 git/TLS 探针上也出现 `gnutls_handshake() failed`
  - `ghproxy.net` 能成功返回并下载 DINOv3 zip
  - 下载到的 zip 大小约 `9.9M`,解压根目录为 `dinov3-adc254450203739c8149213a7a69d8d905b4fcfa/`
  - 手动解压并重命名后,最小初始化输出:
    - `Using cache found in /root/.cache/torch/hub/facebookresearch_dinov3_adc254450203739c8149213a7a69d8d905b4fcfa`
    - `roma_model_ok RoMaV2`
    - `Loading model from: .../lpips/weights/v0.1/vgg.pth`
    - `lpips_ok LPIPS`

## 综合发现

### 现象
- 当前默认全量路径在补齐 `romav2.pt` / `vgg16-397923af.pth` 之后,新的首阻塞确实转移到了 DINOv3 仓库代码的 torch hub 缓存。

### 已验证结论
- `romav2.pt` 和 `vgg16` 已不再是首个缺失项。
- 只要本地补齐 `facebookresearch_dinov3_<commit>` 目录, `RoMaV2` 初始化就可以完全走本地缓存。
- 当前机器上可行的旁路是 `ghproxy.net` 下载 DINOv3 zip,而不是继续赌 GitHub 直连或 `7890` 代理。
## [2026-03-21 22:42:30] [Session ID: codex-20260321-223500] 笔记: 默认全量路径在 RoMa sampling 阶段触发 CUDA OOM

## 来源

### 来源1: 默认全量路径真实运行日志
- 文件: `/tmp/video_to_world_xhc_bai_run_reconstruction_full_default_20260321_2238.log`
- 关键命令:
  - `pixi run python run_reconstruction.py --config.root-path /tmp/video_to_world_joint_scene_xhc_bai_fast_run_full_default_20260321_2238 --config.mode fast`
- 关键动态输出:
  - 默认 Stage 1 成功初始化 RoMaV2,并打印:
    - `Using cache found in /root/.cache/torch/hub/facebookresearch_dinov3_adc254450203739c8149213a7a69d8d905b4fcfa`
    - `RoMa matcher initialized successfully`
  - 运行推进到第 9 帧附近时失败,堆栈落在:
    - `third_party/RoMaV2/src/romav2/romav2.py:529`
    - `scores = (-(torch.cdist(x, x) ** 2) / (2 * std**2)).exp()`
  - CUDA 错误原文核心信息:
    - `torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 764.00 MiB`
    - `GPU 0 has a total capacity of 47.37 GiB of which 442.88 MiB is free`
    - `42.40 GiB is allocated by PyTorch, and 3.24 GiB is reserved by PyTorch but unallocated`

## 综合发现

### 现象
- 默认全量路径已经越过了所有此前的在线下载阻塞。
- 现在新的首阻塞是 RoMa v2 采样阶段的显存爆炸,而不是缓存或网络问题。

### 当前假设
- 主假设:
  - `compute_roma_matches_for_frame -> self.model.sample(preds, num_samples)` 的 `num_samples` 对当前 50 帧 fast 配置偏大,导致 `kde()` 内部的 `torch.cdist(x, x)` 形成过大的 N×N 显存开销。
- 备选解释:
  - 也可能不是单纯 `num_samples` 过大,而是前面几帧累计的 RoMa / ICP 图结构没有及时释放,导致到第 9 帧时显存逐步堆高后才被 `cdist` 击穿。

### 下一步最小验证
- 先读 `configs/stage1_align.py` 和 `models/roma_matcher.py`,确认默认 `num_samples` / `certainty_threshold` / 缓存策略。
- 再判断是否已有正式配置开关可以降低 RoMa sampling 的显存占用。
- 若存在正式参数,优先做最小配置验证,而不是直接改代码。
## [2026-03-21 23:33:30] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 笔记: RoMa 显存管理修法的本地短验证已通过

## 来源

### 来源1: 新增单测与语法检查
- 关键命令:
  - `python3 -m py_compile models/roma_matcher.py losses/correspondence.py frame_to_model_icp.py tests/test_roma_memory_offload.py`
  - `timeout 300s pixi run python -m unittest tests.test_roma_memory_offload`
- 要点:
  - `py_compile` 已通过
  - `Ran 2 tests in 0.238s`
  - `OK`

## 综合发现

### 现象
- 原先单测失败不是逻辑错误,而是断言把 `cuda` 与 `cuda:0` 这种等价 device 写法误判成不相等。

### 已验证结论
- 把断言改为比较 `device.type` 之后,本地语义验证链已全部通过。
- 当前可以继续进入真实 Stage 1 长跑,验证这版修法是否真的改善 RoMa OOM。
## [2026-03-21 23:05:30] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 笔记: 默认 RoMa 路径 OOM 的更深动态证据与 matcher 生命周期假设

## 来源

### 来源1: fresh root 上的真实 Stage 1 重跑
- 日志:
  - `/tmp/video_to_world_xhc_bai_frame_to_model_icp_romacpuoffload_20260321_2334.log`
- 关键现象:
  - 已越过此前的 frame 9 / frame 12
  - 继续推进到 frame 15 才再次在 `self.model.sample(...)->kde()->torch.cdist` OOM
  - 失败时错误仍是 `Tried to allocate 764.00 MiB`

### 来源2: frame 15 的最小动态探针
- 日志:
  - `/tmp/video_to_world_xhc_bai_roma_frame15_probe_20260321_2350.log`
- 关键命令:
  - 单独初始化 `RoMaMatcherWrapper`
  - 只对 frame 15 的 15 个 reference pair 顺序调用 `match_images`
- 关键输出:
  - 15 个 pair 全部能成功跑完
  - 但 `torch.cuda.memory_allocated()` 在每个 pair 后大约线性上升约 1 GiB
  - 第 15 个 pair 后达到约 `16.07 GiB`

### 来源3: 释放判别实验
- 关键命令:
  - 单 pair 后 `gc.collect()` / `torch.cuda.empty_cache()`
  - 单 pair 后 `del matcher`
- 关键输出:
  - `gc.collect()` 后 `memory_allocated()` 没有回落
  - `del matcher` 后显存会部分回落

## 综合发现

### 现象
- 现在的 OOM 已经不是“单个 pair 自己就会炸”。
- 更像是同一个 RoMaV2 matcher 实例在跨帧处理新 pair 时,显存持续累积。

### 当前主假设
- 主假设:
  - 需要把 RoMaV2 matcher 的生命周期缩短,至少按帧重建一次,把累计泄漏截断在当前帧内。
- 备选解释:
  - RoMaV2 内部推理路径仍有未完全释放的大中间张量,按帧重建只是工作级绕行,不是根治。

### 已采取处置
- `third_party/RoMaV2/src/romav2/romav2.py`
  - 给 `forward()` 增加 `keep_intermediate` 参数
  - `match()` 走瘦身推理路径
- `frame_to_model_icp.py`
  - 在每帧 RoMa matching 结束后,对 CUDA + RoMaV2 场景按帧重建 matcher
## [2026-03-21 23:21:30] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 笔记: memtrace 证明新算 RoMa pair 的泄漏会跨出 matcher 生命周期,主流程改走“独立进程预热 cache”

## 来源

### 来源1: 带显存探针的真实 Stage 1 日志
- 文件:
  - `/tmp/video_to_world_xhc_bai_frame_to_model_icp_memtrace_20260321_2316.log`
- 关键事实:
  - frame 15~18 命中 cache 时:
    - `before_roma ≈ 1.35 GiB`
    - `after_roma ≈ 1.35 GiB`
  - frame 19 首次新算时:
    - `before_roma = 1.35 GiB`
    - `after_roma = 20.26 GiB`
  - frame 20 再次新算时:
    - `before_roma = 20.26 GiB`
    - `after_roma = 40.17 GiB`
  - 说明泄漏在 RoMa 结束后仍留在主进程里,并继续污染下一帧。

### 来源2: cache 覆盖检查
- 当前 cache 已覆盖到 `src=20`
- 剩余未覆盖帧:
  - `21..49`

### 来源3: frame 21 独立进程试跑
- 关键输出:
  - `frame_done 21 pairs 20 new_pairs 20`
  - 子进程内显存虽升到约 `21.61 GiB`,但进程退出后会整体回收

## 综合发现

### 已验证结论
- matcher 刷新本身不能阻止泄漏跨出当前函数并污染主流程。
- 但“每帧一个新进程”可以天然切断泄漏生命周期。
- 对当前测试运行,最稳路线是:
  - 先用独立进程预热剩余 RoMa cache
  - 再让主流程只吃 cache 运行
## [2026-03-21 23:43:30] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 笔记: 全量 RoMa cache 命中后,默认 Stage 1 已真实跑通

## 来源

### 来源1: 真实 Stage 1 全量 cache 命中运行
- 日志:
  - `/tmp/video_to_world_xhc_bai_frame_to_model_icp_allcache_20260321_2334.log`
- 输出目录:
  - `/tmp/video_to_world_joint_scene_xhc_bai_fast_run_full_default_20260321_2238/frame_to_model_icp_50_2_offset0_allcache_20260321_2334`
- 关键事实:
  - 帧进度真实完成到 `49/49`
  - 尾部日志出现:
    - `Saved RoMa match history ...`
    - `Saved model frame segments and pixel indices ...`
    - `Saved convention metadata and original extrinsics ...`

### 来源2: CUDA 显存探针
- 关键事实:
  - 在 cache 命中的中后段,持续看到:
    - `before_roma ≈ 1.36 GiB`
    - `after_roma ≈ 1.36 GiB`
  - 说明主流程现在不再被 RoMa 新算 pair 的泄漏污染。

## 综合发现

### 已验证结论
- “先用独立进程补齐剩余 RoMa cache,再让主流程只读 cache” 这条路线已经被真实 Stage 1 证明可行。
- 当前默认 RoMa 路径不需要再关闭功能或降 `roma_num_samples`,也能真实完成 Stage 1。

## [2026-03-22 00:16:43] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 笔记: 默认后半程测试运行的两个真实阻塞已修复并完成入口级验证

## 来源

### 来源1: `run_reconstruction.py` 的 dry-run 与真实运行日志
- `run_reconstruction.py --config.gs.num-iters 150 --config.dry-run` 现在真实打印:
  - `--config.num-iters 150`
- 最终无 error 的入口级日志:
  - `/tmp/video_to_world_xhc_bai_run_reconstruction_postoomfix_20260322_001016.log`

### 来源2: 真实 GS smoke 产物
- 1 iter 入口级 smoke 成功目录:
  - `/tmp/video_to_world_joint_scene_xhc_bai_fast_run_full_default_20260321_2238/frame_to_model_icp_50_2_offset0_allcache_20260321_2334/gs_3dgs_lpips_postoomfix_20260322_001016`
- 关键产物:
  - `checkpoint_000000.pt`
  - `model_final.pt`
  - `splats_3dgs.ply`
  - `gs_video_eval/render_input_poses.mp4`

### 来源3: 静态代码阅读
- `run_reconstruction.py` 之前把 GS 轮数写成:
  - `num_iters=gs_iters_by_renderer.get(renderer, gs_cfg_base.num_iters)`
- `eval_gs.py` 之前默认强依赖:
  - `<root_path>/gs_video/0000_extend_transforms.json`
- `train_gs.py` 之前在 `subprocess.run(eval_gs)` 前没有任何显存释放动作

## 综合发现

### 现象 -> 结论 1
- 现象:
  - 明确传入 `--config.gs.num-iters 150`, 真实日志却仍进入 `GS training (3dgs): ... /10000`
- 已验证结论:
  - 根因是 `run_reconstruction.py` 的 fast/extensive mode 预设无条件覆盖了用户显式传入的 `gs.num_iters`
  - 现已修成“只有当用户没覆盖时才套 mode 默认值”

### 现象 -> 结论 2
- 现象:
  - joint scene root 没有 `gs_video/0000_extend_transforms.json`, `eval_gs` 会直接 `FileNotFoundError`
- 已验证结论:
  - 这不是 GS 训练失败,而是 `eval_gs` 对可选资产缺失时缺少降级策略
  - 现已修成: 缺失 `gs_video` transforms 时自动降级为只渲染 input / optimised poses

### 现象 -> 结论 3
- 现象:
  - 手动单独运行 `eval_gs` 成功
  - 但 `train_gs` 内 auto eval 会 OOM, 报错显示父训练进程仍占约 `24.87 GiB` 显存
- 已验证结论:
  - 根因是父训练进程在拉起 GPU 评估子进程前,没有先释放自己的 CUDA 大对象
  - 现已修成: `train_gs` 在 auto eval 前显式 `del` 大对象 + `gc.collect()` + `torch.cuda.empty_cache()`

### 最终验证结论
- 默认 Stage 1: 已真实跑通
- 默认后半程: 已证明能进入 Stage 2 和默认 LPIPS 的 Stage 3.2
- 修复后入口级 smoke: 已通过, 且最终日志中:
  - `Automatic eval failed` = 0
  - `Traceback` = 0
  - `[ERROR]` = 0
## [2026-03-22 01:26:11] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 笔记: 缺失 `0000_extend_transforms.json` 的可重建性验证

## 来源

### 来源1: `third_party/depth-anything-3/src/depth_anything_3/model/utils/gs_renderer.py`
- 要点:
  - `extend` 不是单纯 circular / wander 轨迹。
  - 真实逻辑是: 先对多帧输入相机做插值,再平滑,最后在中段插入 `wander` 和 `dolly_zoom` 两段轨迹。

### 来源2: `third_party/depth-anything-3/src/depth_anything_3/utils/camera_trj_helpers.py`
- 要点:
  - `render_wander_path()` 生成的是围绕参考位姿的周期性偏移轨迹。
  - `render_dolly_zoom_path()` 会沿相机 Z 方向推进,同时缩放焦距。

### 来源3: 当前 scene `exports/npz/results.npz`
- 要点:
  - 包含 `extrinsics: (600, 3, 4)`、`intrinsics: (600, 3, 3)`、`depth: (600, 280, 504)`。
  - 这些数据足够在不重跑 DA3 的前提下重建 `extend` 轨迹。

## 综合发现

### 结论
- 用户口中的 "Camera moves in a clockwise circular path" 更接近 `wander` 的视觉效果,但当前缺失文件名是 `0000_extend_transforms.json`,它对应的是 DA3 的 `extend` 长轨迹。
- 该轨迹可以直接基于当前 `results.npz` 里的位姿和内参重建,不依赖 GS 模型本体。
- 本轮已生成:
  - `/tmp/video_to_world_joint_scene_xhc_bai_fast_run_full_default_20260321_2238/gs_video/0000_extend_transforms.json`
- 生成结果已通过两类动态验证:
  - `load_nerf_transforms_json()` 成功载入 `(722, 4, 4)` 轨迹
  - `eval_gs` 使用该文件成功渲染 3 帧 `gs_video` 并输出 `render_gs_video.mp4`

## [2026-03-22 12:08:30] [Session ID: eab9d6c3-318b-4c00-96b4-b400f09605f6] 笔记: 旧流程切换为新 multiview extensive 的操作基线

## 来源

### 来源1: 用户最新指令
- 要点:
  - 需要停止当前 extensive 运行。
  - 新命令使用 `run_multiview_reconstruction.py`。
  - 新 scene root 固定为 `output/video_to_world/joint_scene_xhc_bai`。
  - 需要显式设置 `--preprocess-max-frames 60` 与 `--preprocess-max-stride 2`。
  - 对齐参数固定为 `num-frames=50`, `stride=8`, `offset=0`。
  - 模式为 `extensive`。

## 综合发现

### 执行注意点
- 停旧进程是必要前置动作,否则会与新任务竞争 GPU。
- 新任务是联合多视角入口,与先前单 scene root extensive 命令不同。

## [2026-03-22 12:10:25] [Session ID: eab9d6c3-318b-4c00-96b4-b400f09605f6] 笔记: 新 multiview extensive 已进入 Stage 0 首个视角预处理

## 来源

### 来源1: `/tmp/video_to_world_joint_scene_xhc_bai_extensive_20260322_121020.log`
- 要点:
  - 已打印 `Stage 0: preprocess_multiview.py`
  - 已打印 `view=0 scene=xhc-bai_97e474c6`
  - 正在执行 `preprocess_video.py`
  - `ffmpeg` 已开始向 `per_view/view_0/frames/%06d.png` 输出帧

## 综合发现

### 启动正确性
- 新 `scene_root` 已被真实采用,不是旧命令残留。
- `preprocess-max-frames=60` 与 `preprocess-max-stride=2` 已传递到 Stage 0。

## [2026-03-22 12:12:40] [Session ID: eab9d6c3-318b-4c00-96b4-b400f09605f6] 笔记: multiview 首次尝试失败点与修正方案

## 来源

### 来源1: `/tmp/video_to_world_joint_scene_xhc_bai_extensive_20260322_121020.log`
- 要点:
  - Stage 0 六个视角都已完成 DA3 preprocessing。
  - 联合输出 JSON 已打印 `total_frames: 360`。
  - 失败点发生在 `run_reconstruction.py` 被调用之后。
  - 实际报错为 `Unrecognized options: --config.alignment.num-frames ...`

### 来源2: `pixi run python run_reconstruction.py --help`
- 要点:
  - 正确参数名为:
    - `--config.stage1.alignment.num-frames`
    - `--config.stage1.alignment.stride`
    - `--config.stage1.alignment.offset`

## 综合发现

### 失败性质
- 这是 CLI 参数路径错误,不是 Stage 1/2/3 算法错误。
- 已成功产出的 Stage 0 结果可以直接复用。

## [2026-03-22 12:13:55] [Session ID: eab9d6c3-318b-4c00-96b4-b400f09605f6] 笔记: 当前环境缺失 torch_kdtree,续跑需切 cpu_kdtree

## 来源

### 来源1: `pixi run python -c 'import torch_kdtree'` 等价探针
- 要点:
  - 返回 `TORCH_KDTREE=missing`
  - 具体异常为 `ModuleNotFoundError`

## 综合发现

### Stage 2 运行条件
- 当前 extensive 若不显式设置 `--config.stage2.knn-backend cpu_kdtree`,在 Stage 2 会重现已知缺依赖失败。

## [2026-03-22 12:17:45] [Session ID: eab9d6c3-318b-4c00-96b4-b400f09605f6] 笔记: Stage 1 已进入 ICP 主循环且 cpu_kdtree 正常工作

## 来源

### 来源1: `/tmp/video_to_world_joint_scene_xhc_bai_extensive_stage123_cpu_kdtree_20260322_121430.log`
- 要点:
  - `Saving point clouds: 360/360`
  - `Computed valid pixel indices for 45 frames`
  - `Rigid ICP f00001` 与 `Non-rigid ICP f00001` 已完成
  - `Rigid ICP f00002` 与 `Non-rigid ICP f00002` 已完成
  - 当前已进入 `Rigid ICP f00003`
  - 每帧总耗时约 8 秒量级

## 综合发现

### Stage 1 真实状态
- 当前流程不是卡死,而是在按 `44` 个目标帧推进 Stage 1。
- `cpu_kdtree` 对当前环境是可用的正式绕过方案。

## [2026-03-22 12:34:35] [Session ID: eab9d6c3-318b-4c00-96b4-b400f09605f6] 笔记: 当前真实进度已到 Stage 3.1 inverse deformation Epoch 6/30

## 来源

### 来源1: `/tmp/video_to_world_joint_scene_xhc_bai_extensive_stage123_cpu_kdtree_20260322_121430.log`
- 要点:
  - 日志中已出现:
    - `Stage 1: Iterative Alignment`
    - `Stage 2: Global Optimization`
    - `Stage 3.1: Inverse Deformation Training`
  - 最新训练标记已到:
    - `Training: 5/30`
    - `Epoch 6/30`

### 来源2: 进程与 GPU 探针
- 要点:
  - 当前 compute app 是 `train_inverse_deformation`
  - 显存约 `4.4 GiB`
  - GPU 总占用约 `4.8 GiB`

## 综合发现

### 当前阶段判断
- 现在已经越过 Stage 1 和 Stage 2。
- 当前真正运行的是 Stage 3.1,还没有切到 2DGS / 3DGS。
