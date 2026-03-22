# 洞察记录

## [2026-03-22 12:48:09] [Session ID: 645377ac-8a48-4336-a3f3-dad38dca8dd8] 主题: CUDA 相关 Pixi 安装任务不应把“未导出 CUDA_HOME”误报成“没有 CUDA”

### 发现来源
- `torch_kdtree` 安装失败排查与修复。

### 核心问题
- 在 CUDA 扩展安装场景里,用户 shell 没有导出 `CUDA_HOME`,不等于机器没有可用 CUDA toolkit。
- 如果任务只检查环境变量,就会把“入口环境不完整”误报成“系统依赖缺失”。

### 为什么重要
- 这种误报会把排查方向直接带偏。
- 用户会先去怀疑驱动、CUDA 安装、PyTorch 版本,但真实问题只是任务入口没做自动探测。

### 当前结论
- 更稳的通用做法是:
  - 先看 `CUDA_HOME`
  - 再看 `/usr/local/cuda`
  - 再看 `torch.utils.cpp_extension.CUDA_HOME`
  - 成功后主动补齐 `PATH/include/lib` 环境
- 只有这三步都失败,才把问题升级成“机器缺少可用 CUDA toolkit”。

### 后续讨论入口
- 后续新增任何 CUDA 源码编译任务时,优先复用这套探测顺序,不要再把 `CUDA_HOME` 写成唯一入口前提。
