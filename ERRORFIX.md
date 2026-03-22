# 错误修复记录

## [2026-03-20 21:59:46] [Session ID: codex-20260320-215510] 问题: Pixi 复杂任务在运行期解析失败

### 现象
- 用户执行 `setup-depth-anything-3` 时,Pixi 报:
  - `failed to parse shell script`
  - `Unsupported reserved word`
- 报错位置落在 `if [ ! -d ... ]; then` 这样的条件语句。

### 假设
- 主假设:
  - `pixi.toml` 里的多行 task 字符串被 `deno_task_shell` 解析,而它不支持完整的 `if ... then ... fi` 语法。
- 备选解释:
  - 也可能是 task 需要 `interpreter = "bash"` 一类的新字段来声明解释器。

### 验证
- 静态证据:
  - `exa_code` 文档说明 Pixi task 底层是 `deno_task_shell`,只支持有限 shell 语法。
  - 在本机 `pixi 0.65.0` 上测试 `interpreter = "bash"` 会报字段不被识别。
- 动态证据:
  - 最小失败样例 `pixi run broken` 稳定复现同样的 `Unsupported reserved word`
  - 最小成功样例 `pixi run via-array` 在 `bash -lc` 包裹后成功输出 `ok`
  - 仓库内真实执行 `setup-depth-anything-3` 后,错误已不再是解析失败,而是进入 Git 网络连接阶段

### 原因
- 已验证结论:
  - 根因是 Pixi 当前版本的 task 解释器不支持这类复杂条件语句。
  - 不是 `git clone`、补丁路径或 pip 安装本身导致的原始报错。

### 修复
- 将以下任务统一改为 `cmd = ["bash", "-lc", """..."""]`:
  - `setup-depth-anything-3`
  - `setup-romav2`
  - `install-torch-kdtree`
- 在脚本开头补充 `set -euo pipefail`,确保命令链在出错时尽早失败。

### 验证结果
- 通过:
  - `pixi task list`
  - `pixi run -n setup-depth-anything-3`
  - `pixi run -n setup-romav2`
  - `pixi run -n install-torch-kdtree`
  - `timeout 300s pixi run setup-depth-anything-3`
- 当前剩余阻塞:
  - GitHub 访问受当前代理/网络环境影响失败
  - 这不属于本次仓库配置 bug 的同一层问题

## [2026-03-20 23:07:10] [Session ID: codex-20260320-225624] 问题: install-gsplat 在 pip 内部 git clone 时出现 TLS EOF

### 现象
- 用户执行 `install-gsplat` 时,`pip` 内部调用:
  - `git clone --filter=blob:none --quiet https://github.com/nerfstudio-project/gsplat.git`
- 失败报错:
  - `TLS connect error`
  - `error:0A000126:SSL routines::unexpected eof while reading`

### 假设
- 主假设:
  - 当前 shell 里的 loopback 代理变量失效,导致 Git / pip 被导向不可用的本地代理。
- 备选解释:
  - `gsplat` 仓库、`v1.5.3` 标签或 partial clone 行为本身有问题。

### 验证
- 静态证据:
  - `gsplat` 官方 README 支持从 GitHub VCS 安装。
  - pip 官方文档支持从 VCS URL 和本地 project path 安装。
  - `gsplat` 官方 release 显示 `v1.5.3` 对应 commit `937e29912570c372bed6747a5c9bf85fed877bae`。
- 动态证据:
  - 在当前代理环境下运行 `git ls-remote`,报错被导向 `127.0.0.1:7897`
  - 去掉代理后再跑 `git ls-remote`,成功返回 `HEAD`
  - 去掉代理后再跑 `pixi run install-gsplat`,原始 TLS EOF 不再出现
  - 应用修复后带着原环境直接跑 `pixi run install-gsplat`,任务会自动清理 loopback 代理并进入 clone

### 原因
- 已验证结论:
  - 根因是坏的 loopback 代理环境,不是 `gsplat` 仓库或版本本身损坏。

### 修复
- 新增 `scripts/pixi_task_helpers.sh`,提供 `clear_loopback_proxy_vars`。
- 将 `install-gsplat` 改为显式:
  - 清理 loopback 代理
  - clone `third_party/gsplat`
  - checkout 固定 commit
  - 本地 path 安装
- 让其他 GitHub 任务也复用相同 helper:
  - `install-tinycudann`
  - `setup-depth-anything-3`
  - `setup-romav2`
  - `install-torch-kdtree`

### 验证结果
- 通过:
  - `pixi task list`
  - `python3 -m unittest tests/test_pixi_manifest.py`
  - `python3 -m unittest discover -s tests`
  - `timeout 120s pixi run install-gsplat`
- 当前剩余情况:
  - 完整 clone/build 仍需要更长运行窗口
  - 但原始 TLS EOF 已被证据性绕过

## [2026-03-21 00:29:11] [Session ID: codex-20260321-002404] 问题: setup-depth-anything-3 在本地已具备目标 commit 时仍无条件远程 fetch

### 现象
- 用户运行 `setup-depth-anything-3` 时,失败在:
  - `git -C third_party/depth-anything-3 fetch --tags --force`
- 但本地检查显示:
  - `/workspace/depth-anything-3` 已在目标 commit `2c21ea...`
  - `third_party/depth-anything-3` 也已在目标 commit `2c21ea...`

### 假设
- 主假设:
  - 任务里无条件远程 fetch 是不必要的,这正是本次失败的直接触发点。
- 备选解释:
  - 即使改成“本地优先”,复杂逻辑放在 Pixi task 字符串里可能仍会被解析层破坏。

### 验证
- 静态证据:
  - 两个本地仓库都包含目标 commit。
- 动态证据:
  - 第一版把局部变量逻辑直接写进 `pixi.toml` 后,运行报 `empty string is not a valid pathspec`
  - 直接在 shell 手动执行同样脚本则成功
  - 这证明问题不在 Git,而在 Pixi task 字符串的预展开行为
  - 改成独立脚本后再跑:
    - 输出 `DepthAnything-3 target commit already available locally`
    - 输出 `DepthAnything-3 patch already applied`
    - `pip install -e` 最终成功

### 原因
- 已验证结论:
  - 原始失败由“无条件远程 fetch”触发。
  - 第一轮修法不成立的原因是 Pixi 会预展开 task 字符串中的 `$局部变量`。

### 修复
- 新增 `git_repo_has_commit` helper。
- 新增独立脚本 `scripts/setup_depth_anything_3.sh`。
- 将 `setup-depth-anything-3` 改为直接调用该脚本。
- 引入 `.envrc` 默认值:
  - `DEPTH_ANYTHING_3_LOCAL_REPO=/workspace/depth-anything-3`

### 验证结果
- 通过:
  - `python3 -m unittest tests/test_pixi_manifest.py`
  - `python3 -m unittest discover -s tests`
  - `timeout 180s pixi run setup-depth-anything-3`
- 最终状态:
  - 任务已完整成功,不再依赖 GitHub fetch

## [2026-03-21 12:48:58] [Session ID: codex-20260321-123719] 问题: gsplat 的 glm 子模块损坏时,安装任务会拖到 ninja 编译阶段才报错

### 现象
- 用户当前看到的安装失败是:
  - `torch.utils.cpp_extension._run_ninja_build`
  - `RuntimeError: Error compiling objects for extension`
  - `ERROR: Failed building wheel for gsplat`
- 重新抓完整日志后,首个真实失败点其实更早:
  - `Common.h:5:10: fatal error: glm/gtc/type_ptr.hpp: 没有那个文件或目录`

### 假设
- 主假设:
  - `gsplat` 的 `glm` 子模块并没有真正 checkout 完整,只是留下了一个坏的工作树残留。
- 备选解释:
  - 也可能是 `nvcc` / torch / CUDA 版本不兼容,只是碰巧在 `glm` include 这里先炸。

### 验证
- 静态证据:
  - `third_party/gsplat/setup.py` 的 include path 明确依赖:
    - `gsplat/cuda/csrc/third_party/glm`
  - `docs/DEV.md` 明确要求:
    - `git clone --recurse-submodules`
- 动态证据:
  - `find third_party/gsplat/gsplat/cuda/csrc/third_party/glm -maxdepth 3 -type f`
    - 只有 `.git`,没有任何头文件
  - `git -C third_party/gsplat/gsplat/cuda/csrc/third_party/glm rev-parse --verify HEAD`
    - 失败,说明子模块工作树损坏
  - 真实构建日志首个错误稳定落在:
    - `glm/gtc/type_ptr.hpp` 缺失
  - 新脚本短探针:
    - `timeout 8s env -u ... bash scripts/install_gsplat.sh`
    - 已先进入 `glm` 子模块修复路径,没有直接进入原始 `ninja` 报错

### 原因
- 已验证结论:
  - 原始报错的根因不是 `ninja` 本身,也不是第一个暴露出来的 torch/cuda warning。
  - 根因是 `glm` 子模块损坏或缺失,而安装任务缺少真正构建前的关键头文件预检。

### 修复
- 将 `install-gsplat` 从 `pixi.toml` inline task 抽成 `scripts/install_gsplat.sh`。
- 在脚本里加入:
  - pinned commit 的本地优先复用
  - `glm` 头文件存在性检查
  - 损坏子模块的 `deinit + rm -rf + sync + update`
  - 若修复后仍缺头文件,就提前给出明确错误
- 新增测试:
  - `tests/test_install_gsplat_script.py`
  - 更新 `tests/test_pixi_manifest.py`

### 验证结果
- 通过:
  - `bash -n scripts/install_gsplat.sh`
  - `python3 -m unittest tests/test_pixi_manifest.py tests/test_install_gsplat_script.py`
  - `pixi task list`
- 当前剩余情况:
  - 当前机器对 GitHub 访问仍会超时,所以没有完成真实全量安装
  - 但仓库层面的错误链路已经被修正为“提前检测 + 明确失败”,不再把坏子模块伪装成晚期编译错误

## [2026-03-21 14:45:13] [Session ID: codex-20260321-123719] 问题: glm 子模块初始化超时,导致 install-gsplat 仍无法在真实机器上完成

### 现象
- 用户在真实机器上执行:
  - `pixi run install-gsplat`
- 输出停在:
  - `Detected broken glm submodule checkout, resetting it before retry`
  - `正克隆到 '/workspace/video_to_world/third_party/gsplat/gsplat/cuda/csrc/third_party/glm'...`
  - `gsplat 安装失败: 初始化 gsplat 的 glm 子模块 (exit=124)`

### 假设
- 主假设:
  - `g-truc/glm` 仓库在当前机器上访问过慢或不可达,不是简单的 180 秒不够。
- 备选解释:

## [2026-03-22 00:20:00] [Session ID: codex-20260321-234700] 问题: install-tinycudann 在本机 CUDA 与 pixi NVIDIA wheel 混合环境下编译失败

### 现象
- `pixi run setup` 前半段已经通过,真实阻塞收敛到 `install-tinycudann`。
- 早期报错依次表现为:
  - `nvcc: not found`
  - `#error C++17 or later compatible compiler is required to use PyTorch`
  - `fatal error: nvrtc.h: No such file or directory`
  - `fatal error: cusparse.h: No such file or directory`

### 假设
- 主假设:
  - 系统上并不是完全没有 CUDA,而是 tiny-cuda-nn 的构建入口没有看到完整的 CUDA / NVIDIA 开发路径。
- 备选解释:
  - 也可能是系统 CUDA 安装不完整,根本没有所需头文件和库。

### 验证
- 静态证据:
  - `/usr/local/cuda/bin/nvcc` 存在,但默认 `PATH` 里没有它。
  - `torch.utils.cpp_extension.CUDA_HOME` 返回 `/usr/local/cuda`。
  - `nvrtc.h`、`cusparse.h`、`cublas_v2.h` 不在系统 CUDA include 里,而在:
    - `.pixi/envs/default/lib/python3.10/site-packages/nvidia/*/include`
  - `site-packages/nvidia/*/lib` 里大多只有 `libfoo.so.12`,没有 `libfoo.so`。
- 动态证据:
  - 手动补 `PATH` 后,`nvcc not found` 消失,并成功识别 `Detected CUDA version 12.4`
  - 手动补两个 include 目录后,首错推进到 `cublas_v2.h` 缺失
  - 扩展为汇总全部 `nvidia/*/include` 后,首错推进到链接阶段 `cannot find -lnvrtc`
  - 用临时 `libfoo.so -> libfoo.so.12` 别名和 `rpath` 方案后:
    - `pixi run install-tinycudann` 成功
    - `pixi run setup` 成功
    - `pixi run python` 导入 `tinycudann` 成功

### 原因
- 已验证结论:
  - 根因不是 tiny-cuda-nn 源码本身,也不是机器完全没有 CUDA。
  - 根因是当前环境属于“系统 CUDA + PyPI NVIDIA wheels”混合布局:
    - `nvcc` 来自系统 CUDA
    - 多数开发头和共享库来自 `pixi` 环境里的 `nvidia/*`
  - tiny-cuda-nn 的原始 `setup.py` 只依赖 `nvcc` / `CUDA_HOME` 自动推导,无法自动覆盖这套混合布局。

### 修复
- 在 `scripts/install_tinycudann.sh` 中新增:
  - `detect_cuda_home()`
  - `collect_pixi_nvidia_paths()`
  - `create_nvidia_link_shims()`
  - `build_rpath_flags()`
  - `prepare_cuda_build_env()`
- 修复行为包括:
  - 自动把 `/usr/local/cuda/bin` 加回 `PATH`
  - 汇总所有 `site-packages/nvidia/*/include` 到 `CPATH` / `CPLUS_INCLUDE_PATH`
  - 汇总所有 `site-packages/nvidia/*/lib` 到 `LIBRARY_PATH` / `LD_LIBRARY_PATH`
  - 为仅有 `libfoo.so.12` 的目录生成临时 `libfoo.so` 链接别名
  - 通过 `LDFLAGS` 注入 `-L<link_shim_dir>` 与 `-Wl,-rpath,...`
- 同步更新:
  - `tests/test_pixi_manifest.py`

### 验证结果
- 通过:
  - `bash -n scripts/install_tinycudann.sh`
  - `python3 -m unittest tests/test_pixi_manifest.py`
  - `timeout 1800s pixi run install-tinycudann`
  - `timeout 1800s pixi run setup`
  - `pixi run python -c 'import tinycudann as tcnn; print(tcnn.__file__)'`
  - 当前机器其实已经有其他工程或环境里的 `glm` 副本,可以绕过上游访问直接复用。

### 验证
- 静态证据:
  - 本机搜索到多个 `glm/gtc/type_ptr.hpp`,说明已有本地可复用副本。
- 动态证据:
  - `git ls-remote https://github.com/g-truc/glm.git HEAD`
    - 去掉代理后 30 秒仍超时
  - 修改脚本后执行:
    - `timeout 420s env -u ... pixi run install-gsplat`
    - 最终输出:
      - `Successfully built gsplat`
      - `Successfully installed gsplat-1.5.3`
  - 安装后导入验证:
    - `timeout 30s pixi run python - <<'PY' import gsplat; print(gsplat.__version__)`
    - 输出 `1.5.3`

### 原因
- 已验证结论:
  - 真实阻塞来自 `glm` 上游子模块访问不稳定。
  - 当前机器已有本地 `glm` 头文件副本,此前安装任务没有利用这层本地缓存。

### 修复
- 在 `scripts/install_gsplat.sh` 中增加:
  - `GSPLAT_GLM_LOCAL_DIR` 覆盖入口
  - 本地 `glm` 自动搜索
  - 命中后直接复制 `glm/` 头文件树到目标子模块路径
- 更新 `.envrc` 文档。
- 增加对应单测覆盖 fallback 分支。

### 验证结果
- 通过:
  - `bash -n scripts/install_gsplat.sh`
  - `python3 -m unittest tests/test_pixi_manifest.py tests/test_install_gsplat_script.py`
  - `timeout 420s env -u ... pixi run install-gsplat`
  - `timeout 30s pixi run python - <<'PY' import gsplat; print(gsplat.__version__)`
- 最终状态:
  - `gsplat 1.5.3` 已在当前 `pixi` 环境中真实安装成功
## [2026-03-21 22:12:38] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 问题: `source/flashvsr_reference_xhc_bai` 的后半程真实测试运行被 RoMaV2 和 LPIPS 的外部下载拖住

### 现象
- Stage 0 已成功后,`run_reconstruction.py` 在 Stage 1 会尝试下载:
  - `https://github.com/Parskatt/RoMaV2/releases/download/weights/romav2.pt`
- 关闭 RoMa 后继续跑,又在 Stage 3.2 因 LPIPS 触发:
  - `https://download.pytorch.org/models/vgg16-397923af.pth`
- 两条下载链路在当前环境里都过慢,不适合作为“测试运行优先”路径。

### 假设
- 主假设:
  - 这些下载不是代码逻辑错误,而是测试路径上不必要的外部依赖阻塞。
  - 对测试跑而言,可以通过正式参数关闭对应功能,先验证主链路是否能继续执行。
- 备选解释:
  - 即使关掉这两层下载,后续仍可能在训练或评估时出现新的运行时问题。

### 验证
- 静态证据:
  - `run_reconstruction.py --help` 明确存在 `--config.stage1.roma.no-use-roma-matching`
  - `train_gs.py --help` 明确存在 `--config.lpips-weight` 与 `--config.no-auto-eval`
  - `losses/rendering.py` 中 `lpips.LPIPS(net='vgg')` 只在 `lpips_weight > 0` 时初始化
- 动态证据:
  - 关闭 RoMa 后,新的 Stage 1 目录 `frame_to_model_icp_50_2_offset0_nroma_20260321_2201` 真实产出
  - `inverse_deformation` 目录真实存在,且 round-trip validation summary 已打印
  - 直接执行 `train_gs` 并设置 `lpips_weight=0`、`num_iters=100` 后,真实得到:
    - `checkpoint_000099.pt`
    - `model_final.pt`
    - `eval_000099/`
    - `splats_3dgs.ply`

### 原因
- 已验证结论:
  - 当前真正的测试阻塞不是 HF/DA3 了,而是 Stage 1 与 Stage 3.2 的额外外部模型下载。
  - 对测试运行来说,RoMa matching 和 LPIPS 并不是“必须先在线下载成功”才能验证主链路的前置条件。

### 修复 / 处置
- Stage 1:
  - 使用 `--config.stage1.roma.no-use-roma-matching`
  - 使用新的 `--config.stage1.out-suffix _nroma_20260321_2201` 隔离结果
- Stage 3.2:
  - 不再沿用被中断的默认 `gs_3dgs` 目录
  - 直接执行 `train_gs`
  - 设置 `--config.lpips-weight 0`
  - 设置 `--config.num-iters 100`
  - 设置独立 `--config.out-dir .../gs_3dgs_lpips0_test_20260321_2210`

### 验证结果
- 已通过:
  - Stage 1 真实产物落盘
  - Stage 3.1 真实产物落盘
  - Stage 3.2 的短程 3DGS 训练、内置评估、最终模型保存和 PLY 导出

## [2026-03-22 00:16:43] [Session ID: 019d0ead-8f40-77b2-b6a3-2ed88d658c78] 问题: 默认后半程测试运行中的 GS 参数覆盖与 auto eval 连续阻塞

### 现象
- 传入 `--config.gs.num-iters 150` 后,真实日志仍进入 `GS training (3dgs): ... /10000`。
- 修复该问题并完成 150 iter 训练后, `eval_gs` 因缺少 `gs_video/0000_extend_transforms.json` 报 `FileNotFoundError`。
- 修复 transforms 路径后, `train_gs` 内 auto eval 又因 CUDA OOM 失败,但手动独立运行 `eval_gs` 可以成功。

### 假设
- 主假设1:
  - `run_reconstruction.py` 的 mode preset 覆盖了 CLI 显式传入的 GS 轮数字段。
- 主假设2:
  - `eval_gs` 对 joint scene 缺少 `gs_video` transforms 时没有降级路径。
- 主假设3:
  - `train_gs` 在 auto eval 前没有释放父进程显存,导致子进程评估 OOM。

### 验证
- 静态证据:
  - `run_reconstruction.py` 旧代码存在:
    - `num_iters=gs_iters_by_renderer.get(renderer, gs_cfg_base.num_iters)`
  - `eval_gs.py` 默认把 transforms 路径写死到:
    - `<root_path>/gs_video/0000_extend_transforms.json`
  - `train_gs.py` 在 `subprocess.run(eval_gs)` 前没有任何 `gc.collect()` 或 `torch.cuda.empty_cache()`
- 动态证据:
  - dry-run 旧行为确实把 150 覆盖回 10000
  - 150 iter 真实 GS smoke 已落盘 checkpoint / model / ply,说明训练本体正常
  - 手动独立 `eval_gs` 可成功,而 auto eval 的 OOM 日志明确显示父进程仍占约 `24.87 GiB` 显存
  - 最终入口级日志 `/tmp/video_to_world_xhc_bai_run_reconstruction_postoomfix_20260322_001016.log` 中:
    - `Automatic eval failed` = 0
    - `Traceback` = 0
    - `[ERROR]` = 0

### 原因
- 已验证结论:
  - GS 轮数被 mode preset 无条件覆盖,导致 CLI 显式值失效。
  - `eval_gs` 把 `gs_video` transforms 当成硬前置,不适配当前 joint scene。
  - `train_gs` 父训练进程在启动 GPU 子评估进程前未释放 CUDA 大对象,造成跨进程显存竞争。

### 修复 / 处置
- `run_reconstruction.py`
  - 改成仅在 `gs_cfg_base.num_iters` 仍等于默认值时,才注入 mode preset 的 `num_iters`。
- `eval_gs.py`
  - 新增 `_resolve_transforms_path()`
  - 缺失 `gs_video` transforms 时自动关闭 `render_gs_video_path`,降级为 input / optimised pose 渲染
  - 顺手补齐 `intrinsics_gs is not None` 的保护
- `train_gs.py`
  - 在 auto eval 前显式 `del` 训练期大对象
  - 增加 `gc.collect()` 与 `torch.cuda.empty_cache()`
- 新增回归测试:
  - `tests/test_run_reconstruction.py`
  - `tests/test_eval_gs.py`

### 验证结果
- 通过:
  - `python3 -m py_compile run_reconstruction.py train_gs.py eval_gs.py tests/test_run_reconstruction.py tests/test_eval_gs.py`
  - `timeout 300s pixi run python -m unittest tests.test_run_reconstruction tests.test_eval_gs tests.test_roma_memory_offload`
  - `run_reconstruction.py --config.dry-run` 已真实打印 `--config.num-iters 150`
  - 手动 `eval_gs` 已在真实 checkpoint 上跑通
  - 1 iter 入口级 smoke 已在最终日志中消除 auto eval error

## [2026-03-22 12:12:40] [Session ID: eab9d6c3-318b-4c00-96b4-b400f09605f6] 问题: multiview extensive 使用旧的对齐参数字段名导致 Stage 0 后直接失败

### 问题现象
- 命令:
  - `pixi run python run_multiview_reconstruction.py ... --config.alignment.num-frames 50 --config.alignment.stride 8 --config.alignment.offset 0 --config.mode extensive`
- Stage 0 已完整成功。
- 进入 `run_reconstruction.py` 后立即报错 `Unrecognized options`。

### 原因
- `run_multiview_reconstruction.py` 只是透传额外参数。
- 当前 `run_reconstruction.py` 使用的真实字段路径是:
  - `--config.stage1.alignment.num-frames`
  - `--config.stage1.alignment.stride`
  - `--config.stage1.alignment.offset`
- 因此旧写法 `--config.alignment.*` 无法被识别。

### 修复
- 将透传参数改为 `--config.stage1.alignment.*`。
- 对已经完成 Stage 0 的 scene root,直接调用 `run_reconstruction.py` 继续后续阶段,避免重复预处理。

### 验证
- `pixi run python run_reconstruction.py --help` 已显示正确字段。
- Stage 0 已成功生成 `output/video_to_world/joint_scene_xhc_bai/exports/npz/results.npz`,可作为直接续跑输入。
