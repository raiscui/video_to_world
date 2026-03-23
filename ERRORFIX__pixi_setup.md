## [2026-03-22 21:12:24] [Session ID: codex-20260322-211224] 问题: `tinycudann` 安装后导入仍报 `CXXABI_1.3.15` 缺失

### 现象
- `pixi run setup` 能跑到尾部,但单独执行 `pixi run python -c 'import tinycudann'` 会报:
  - `/usr/lib/x86_64-linux-gnu/libstdc++.so.6: version 'CXXABI_1.3.15' not found`
- 只要在进程启动前手动导出:
  - `LD_LIBRARY_PATH=$PWD/.pixi/envs/default/lib:$PWD/.pixi/envs/default/lib64:$LD_LIBRARY_PATH`
  - 同一导入立刻成功。

### 原因
- `tinycudann` 扩展虽然已经带有包含 Pixi lib 目录的 `RPATH`,但这不足以保证整个 Python 进程优先使用 Pixi 自带的 `libstdc++.so.6`。
- 在 `pixi run python` 进程更早阶段,系统旧版 `libstdc++.so.6` 可能已经被装入。等到 `tinycudann` 扩展加载时,动态链接器继续复用旧库,于是触发 `CXXABI_1.3.15` 缺失。

### 修复
- 在 `pixi.toml` 新增:
  - `[activation.env]`
  - `LD_LIBRARY_PATH = "$CONDA_PREFIX/lib:$CONDA_PREFIX/lib64:$LD_LIBRARY_PATH"`
- 在 `scripts/install_tinycudann.sh` 里,把 `CONDA_PREFIX/lib` 与 `CONDA_PREFIX/lib64` 显式加入:
  - `LIBRARY_PATH`
  - `LD_LIBRARY_PATH`
  - `rpath_flags`
- 同时保留之前对 `RoMaV2` 的 codeload archive 下载修复,确保完整 `pixi run setup` 不回退。

### 验证
- `timeout 120s pixi run python -m unittest tests/test_pixi_manifest.py tests/test_install_gsplat_script.py tests/test_setup_romav2_script.py`
  - `OK`
- 带代理执行 `timeout 1800s pixi run setup`
  - 通过
- 带代理执行联合导入:
  - `romav2=ok`
  - `romatch=ok`
  - `gsplat=ok`
  - `tinycudann=ok`

### 复盘提醒
- 以后遇到“扩展 `.so` 自带 `RPATH` 但运行时仍吃到系统旧库”的问题,不要急着继续改扩展本身。
- 先检查是不是进程级环境在更早阶段就把错误版本的共享库装进来了,尤其是 `pixi run` / `conda run` / 自定义 launcher 这类场景。
