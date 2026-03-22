# 任务计划: 修复 torch_kdtree 安装任务对 CUDA_HOME 的死板依赖

## [2026-03-22 12:37:06] [Session ID: 645377ac-8a48-4336-a3f3-dad38dca8dd8] [记录类型]: 新建支线任务

### 目标
- 解释并复现 `pixi run install-torch-kdtree` 的失败现象。
- 区分“机器缺少 CUDA toolkit”和“Pixi 任务未自动探测 CUDA_HOME”这两种解释。
- 如证据支持,把安装任务改成与仓库现有 tiny-cuda-nn 安装脚本一致的自动探测风格。
- 用动态验证确认修复后的任务能越过当前报错。

### 现象
- 用户执行 `pixi run install-torch-kdtree` 时,任务立刻退出:
  - `CUDA_HOME is not set. Please export CUDA_HOME=/usr/local/cuda first.`
- 失败发生在真正 clone / build `torch_kdtree` 之前。

### 主假设
- 主假设: 当前机器并不缺 CUDA toolkit,而是 `install-torch-kdtree` 任务只检查环境变量 `CUDA_HOME`,没有像 `install_tinycudann.sh` 那样自动探测 `/usr/local/cuda` 或 `torch.utils.cpp_extension.CUDA_HOME`。

### 最强备选解释
- 备选解释: 即使补上 `CUDA_HOME`,后续仍可能因为 `nvcc` 不在 `PATH`、编译器不匹配、或 `torch_kdtree` 上游源码构建问题而失败。

### 验证计划
- [ ] 读取仓库现有脚本与历史记录,确认是否已有类似问题和可复用实现。
- [ ] 现场探测 `/usr/local/cuda`、`nvcc`、`torch.utils.cpp_extension.CUDA_HOME`。
- [ ] 做最小实验: 仅补环境变量后重新运行安装任务,观察错误是否切换。
- [ ] 若主假设成立,按现有脚本风格修复 `install-torch-kdtree`。
- [ ] 重新验证任务,并更新文档与上下文记录。

### 状态
**目前在阶段1** - 已建立支线任务,正在汇总静态证据并准备做最小实验。

## [2026-03-22 12:40:30] [Session ID: 645377ac-8a48-4336-a3f3-dad38dca8dd8] [记录类型]: 最小实验已完成,主假设得到动态证据支持

### 动态证据
- `/usr/local/cuda` 存在,`/usr/local/cuda/bin/nvcc` 可执行,版本为 `12.4.131`。
- `pixi run python` 中 `torch.utils.cpp_extension.CUDA_HOME` 返回 `/usr/local/cuda`。
- 在 shell 里仅补 `CUDA_HOME=/usr/local/cuda` 与 `PATH=/usr/local/cuda/bin:$PATH` 后,任务已能继续进入:
  - clone `third_party/torch_kdtree`
  - init 子模块 `pybind11`
- 说明原始失败点已经被跨过。

### 阶段更新
- [x] 读取仓库现有脚本与历史记录,确认是否已有类似问题和可复用实现。
- [x] 现场探测 `/usr/local/cuda`、`nvcc`、`torch.utils.cpp_extension.CUDA_HOME`。
- [x] 做最小实验: 仅补环境变量后重新运行安装任务,观察错误是否切换。
- [ ] 若主假设成立,按现有脚本风格修复 `install-torch-kdtree`。
- [ ] 重新验证任务,并更新文档与上下文记录。

### 状态
**目前在阶段2** - 主假设已被动态证据支持,下一步开始把任务改成自动探测 CUDA 环境。

## [2026-03-22 12:48:09] [Session ID: 645377ac-8a48-4336-a3f3-dad38dca8dd8] [记录类型]: 修复与验证完成

### 已完成事项
- [x] 读取仓库现有脚本与历史记录,确认是否已有类似问题和可复用实现。
- [x] 现场探测 `/usr/local/cuda`、`nvcc`、`torch.utils.cpp_extension.CUDA_HOME`。
- [x] 做最小实验: 仅补环境变量后重新运行安装任务,观察错误是否切换。
- [x] 若主假设成立,按现有脚本风格修复 `install-torch-kdtree`。
- [x] 重新验证任务,并更新文档与上下文记录。

### 修复内容
- 新增 `scripts/install_torch_kdtree.sh`,把复杂 bash 从 `pixi.toml` 抽到独立脚本。
- 为 `torch_kdtree` 安装链路补上 CUDA 自动探测与 PATH/include/lib 环境准备。
- 将 `pixi.toml` 中的 `install-torch-kdtree` 改为调用独立脚本。
- 更新 `.envrc` 与 `README.md`,让 `CUDA_HOME` 的默认值与文档口径一致。
- 更新 `tests/test_pixi_manifest.py`,防止 manifest 和脚本回退。

### 验证结论
- `pixi run python -m unittest tests.test_pixi_manifest` 通过。
- `pixi run install-torch-kdtree` 在不手工导出 `CUDA_HOME` 的情况下安装成功。
- `pixi run python` 下已可正常导入 `torch_kdtree`。

### 状态
**目前已完成** - 用户报告的 `CUDA_HOME is not set` 安装失败已经被真实安装成功所验证修复。
