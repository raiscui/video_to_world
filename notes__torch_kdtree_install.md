# 笔记: torch_kdtree 安装排查

## [2026-03-22 12:37:06] [Session ID: 645377ac-8a48-4336-a3f3-dad38dca8dd8] 笔记: 首轮静态证据

## 来源

### 来源1: `pixi.toml`
- 要点:
  - `install-torch-kdtree` 目前是 inline bash task。
  - 它只做 `if [ -z "${CUDA_HOME:-}" ]; then exit 1; fi`。
  - 它不会自动探测 `/usr/local/cuda` 或 PyTorch 识别到的 CUDA 路径。

### 来源2: `scripts/install_tinycudann.sh`
- 要点:
  - 已存在 `detect_cuda_home()`。
  - 逻辑顺序是: 先看环境变量,再看 `/usr/local/cuda`,最后看 `torch.utils.cpp_extension.CUDA_HOME`。
  - 这说明仓库内部已经有更稳的 CUDA 路径探测范式。

### 来源3: 本机动态探针
- 要点:
  - `/usr/local/cuda` 存在。
  - shell 当前 `CUDA_HOME` 未导出。
  - `pixi run python` 中 `torch.utils.cpp_extension.CUDA_HOME` 返回 `/usr/local/cuda`。
  - `nvcc` 当前不在 shell `PATH` 中,但这还不足以证明 toolkit 缺失,因为 `/usr/local/cuda/bin` 还未加入 PATH。

## 综合发现
- 当前更像“任务缺少自动探测”,而不是“机器没有 CUDA”。
- 但仍需通过“补齐最小环境后重跑一次”来验证错误是否切换。

## [2026-03-22 12:40:30] [Session ID: 645377ac-8a48-4336-a3f3-dad38dca8dd8] 笔记: 最小可证伪实验结果

## 来源

### 来源1: 现场命令
- 命令:
  - `env CUDA_HOME=/usr/local/cuda PATH=/usr/local/cuda/bin:$PATH pixi run install-torch-kdtree`
- 观察到的关键输出:
  - 不再出现 `CUDA_HOME is not set...`。
  - 已进入 `git clone https://github.com/thomgrand/torch_kdtree ...`。
  - 已继续初始化 `pybind11` 子模块。
  - 180 秒超时前未看到新的同步错误输出。

## 综合发现
- 这条实验已经足以推翻“当前失败就是因为机器没有 CUDA toolkit”。
- 当前已验证结论更接近:
  - 原报错的直接根因是任务脚本只认环境变量 `CUDA_HOME`,没有自动探测当前机器上可用的 CUDA 安装。
- 仍待验证:
  - 构建链路是否还会在更后面遇到新的上游编译问题。

## [2026-03-22 12:48:09] [Session ID: 645377ac-8a48-4336-a3f3-dad38dca8dd8] 笔记: 修复后的动态验证结果

## 来源

### 来源1: 单元测试
- 命令:
  - `pixi run python -m unittest tests.test_pixi_manifest`
- 结果:
  - `Ran 7 tests ... OK`

### 来源2: 实际安装验证
- 命令:
  - `pixi run install-torch-kdtree`
- 关键输出:
  - `torch_kdtree CUDA 环境已准备:`
  - `CUDA_HOME=/usr/local/cuda`
  - `CUDACXX=/usr/local/cuda/bin/nvcc`
  - `Successfully built torch_kdtree`
  - `Successfully installed torch_kdtree-1.0`

### 来源3: 运行时导入探针
- 命令:
  - `pixi run python -c 'import torch_kdtree; ...'`
- 结果:
  - `module = .../site-packages/torch_kdtree/__init__.py`
  - `has build_kd_tree = True`

## 综合发现
- 修复后的任务已经不再依赖用户手工导出 `CUDA_HOME`。
- 当前机器上,从仓库根目录直接执行 `pixi run install-torch-kdtree` 已完整成功。
- 原用户报错已被实际安装成功这一动态证据彻底关闭。
