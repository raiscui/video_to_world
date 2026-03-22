# 错误修复记录

## [2026-03-22 12:48:09] [Session ID: 645377ac-8a48-4336-a3f3-dad38dca8dd8] 问题: `pixi run install-torch-kdtree` 在真正构建前就因 `CUDA_HOME` 未导出而立即退出

### 现象
- 用户执行安装命令后,立即得到:
  - `CUDA_HOME is not set. Please export CUDA_HOME=/usr/local/cuda first.`
- 失败发生在 clone / submodule / pip build 之前。

### 原因
- `pixi.toml` 中的旧任务只检查 shell 里的 `CUDA_HOME` 环境变量。
- 但当前机器虽然未导出该变量,实际却存在 `/usr/local/cuda`,而且 `torch.utils.cpp_extension.CUDA_HOME` 也能识别到它。
- 因此原失败属于任务脚本的环境探测缺失,不是“机器没有 CUDA toolkit”。

### 修复
- 新增 `scripts/install_torch_kdtree.sh`。
- 通过 `detect_cuda_home()` 自动探测 CUDA 根目录。
- 自动补齐 `PATH`、`CPATH`、`CPLUS_INCLUDE_PATH`、`LIBRARY_PATH`、`LD_LIBRARY_PATH`。
- 显式导出 `CUDACXX` 与 `CMAKE_CUDA_COMPILER` 指向 `${CUDA_HOME}/bin/nvcc`。
- 将 `pixi.toml` 里的任务改成调用该脚本。

### 验证
- `pixi run python -m unittest tests.test_pixi_manifest`
- `pixi run install-torch-kdtree`
- `pixi run python -c 'import torch_kdtree; ...'`
- 结果:
  - manifest 测试通过
  - 安装成功
  - 运行时导入成功
