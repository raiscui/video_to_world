# 研究笔记

## [2026-03-22 12:42:35] [Session ID: codex-20260322-124235] 笔记: `RoMaV2` 下载链路的最小验证

### 来源
- 当前工作区动态命令:
  - `git ls-remote https://github.com/Parskatt/RoMaV2 HEAD`
  - 去掉代理后的同一条 `git ls-remote`
- 当前 `pixi.toml` 中的 `setup-romav2` 任务定义

### 现象
- 代理环境下:
  - `git ls-remote https://github.com/Parskatt/RoMaV2 HEAD`
  - 约 5 秒返回 `fatal: unable to access ... gnutls_handshake() failed: The TLS connection was non-properly terminated.`
- 去代理环境下:
  - 同一命令 20 秒超时,没有在短窗口内拿到 `HEAD`

### 静态证据
- 当前 `setup-romav2` 仍然是内联任务,核心下载步骤是:
  - `git clone https://github.com/Parskatt/RoMaV2 third_party/RoMaV2`
- 任务在 clone 前只做了 `clear_loopback_proxy_vars`,没有像 `DepthAnything-3` 那样提供“本地仓库优先”或“替代下载源”。

### 初步结论
- 目前只能把“`git clone` 路径不稳”记为候选假设。
- 还缺一层关键证据:
  - 当前工作区是不是已经有可复用的 `third_party/RoMaV2`
  - 当前 Pixi 环境是不是已经具备足以让 `setup` 通过的安装状态
- 下一步先做工作区与环境现状核对,而不是直接改脚本。

## [2026-03-22 12:46:30] [Session ID: codex-20260322-124235] 笔记: `setup-romav2` 的根因已由动态证据收敛

### 来源
- 当前工作区动态命令:
  - `PIXI_KEEP_LOOPBACK_PROXY=1 pixi run setup`
  - `pixi run python -u - <<'PY' ... importlib.import_module("romav2")`
  - `pixi run python -u - <<'PY' ... importlib.import_module("romatch")`
  - `env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy git ls-remote https://github.com/Parskatt/RoMaV2 HEAD`
  - `env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy curl -I -L https://codeload.github.com/Parskatt/RoMaV2/tar.gz/refs/heads/main`

### 现象
- 当前工作区没有 `third_party/RoMaV2`
- `romav2` 模块不存在,但 `romatch` 可导入
- `pixi run setup` 的前四步都通过,最后只在 `setup-romav2` 的 clone 阶段失败

### 关键输出
- `git clone https://github.com/Parskatt/RoMaV2 third_party/RoMaV2`
- `fatal: unable to access 'https://github.com/Parskatt/RoMaV2/': TLS connect error: error:0A000126:SSL routines::unexpected eof while reading`
- 去代理后的 `git ls-remote` 返回:
  - `7151f3846ad0c89c213afb6803966484a6dd76e0	HEAD`
- 去代理后的 `codeload` 头请求返回:
  - `HTTP/2 200`

### 结论
- 这次已经不是候选假设,而是有静态和动态双证据支撑的结论:
  - `setup-romav2` 失败点就是代理下的 GitHub clone
  - 不是 `romatch` 缺包
  - 不是 `setup` 其他任务回退
- 新补证据:
  - 去代理后的 `git clone --depth 1 ...` 虽然不再 TLS EOF,但在实际验证里长时间挂起
  - `git apply change.patch` 已在普通目录上最小验证通过,不依赖 Git 仓库元数据
  - `ROMAV2_ARCHIVE_CACHE_DIR` 里已出现一个 `12` 字节的伪归档文件,`file` 结果是 `ASCII text`,不是 gzip
  - 这会让 `curl --continue-at -` 从错误偏移恢复,表现成“看起来在续传,其实一直 0 B/s”
- 用户随后要求显式使用:
  - `https_proxy=http://127.0.0.1:7897`
  - `http_proxy=http://127.0.0.1:7897`
  - `all_proxy=socks5://127.0.0.1:7897`
- 用这组代理重新验证后:
  - `curl -I -L https://codeload.github.com/Parskatt/RoMaV2/tar.gz/refs/heads/main`
  - 返回 `HTTP/1.1 200 Connection established` 后继续拿到 `HTTP/2 200`
- 这说明:
  - 之前“archive 也必须去代理”的结论已经不成立
  - 当前更准确的表述应改成:
    - `git clone` 不稳
    - `codeload archive + 用户指定代理` 可以走通
- 新增的安装级证据:
  - 代理下载完成后,`pip install -e` 不再报网络问题
  - 新的首错变成:
    - `Could not find a version that satisfies the requirement dataclasses>=0.8`
  - 现场文件 `third_party/RoMaV2/pyproject.toml` 仍然保留:
    - `"dataclasses>=0.8"`
  - 这与脚本打印的 `RoMaV2 patch already applied` 互相矛盾,说明原先基于 `git apply --reverse --check` 的判断不可靠
- 因此下一步实现更新为:
  - 继续使用 `codeload archive`
  - 但下载时沿用用户显式导出的代理变量
  - 解包后直接显式把 `dataclasses>=0.8` 改成 `dataclasses`
  - 再继续 editable install

## [2026-03-22 21:12:24] [Session ID: codex-20260322-211224] 笔记: `tinycudann` 失败点从安装期收敛到 Pixi 运行时库优先级

### 来源
- 动态验证命令:
  - `env LD_LIBRARY_PATH="$PWD/.pixi/envs/default/lib:$PWD/.pixi/envs/default/lib64:${LD_LIBRARY_PATH:-}" pixi run python -u - <<'PY'`
  - `import tinycudann`
- 静态检查命令:
  - `readelf -d .pixi/envs/default/lib/python3.10/site-packages/tinycudann_bindings/_86_C.cpython-310-x86_64-linux-gnu.so`
  - `ldd .pixi/envs/default/lib/python3.10/site-packages/tinycudann_bindings/_86_C.cpython-310-x86_64-linux-gnu.so`
  - `strings .pixi/envs/default/lib/libstdc++.so.6`
  - `strings /usr/lib/x86_64-linux-gnu/libstdc++.so.6`
- 参考资料:
  - Pixi 官方文档 `activation.env`

### 现象
- 直接执行 `pixi run python -c 'import tinycudann'` 会报:
  - `/usr/lib/x86_64-linux-gnu/libstdc++.so.6: version 'CXXABI_1.3.15' not found`
- 但只要在进程启动前补上:
  - `LD_LIBRARY_PATH=$PWD/.pixi/envs/default/lib:$PWD/.pixi/envs/default/lib64:...`
  - 同一导入立即成功。

### 静态证据
- `tinycudann` 扩展已经带有 `RPATH`,其中包含:
  - `.pixi/envs/default/lib`
  - `.pixi/envs/default/targets/x86_64-linux/lib`
  - 多个 `site-packages/nvidia/*/lib`
- `ldd` 直接看扩展文件时,`libstdc++.so.6` 已能解析到:
  - `.pixi/envs/default/lib/libstdc++.so.6`
- 但系统库 `/usr/lib/x86_64-linux-gnu/libstdc++.so.6` 最高只有 `CXXABI_1.3.13`
- Pixi 环境内的 `.pixi/envs/default/lib/libstdc++.so.6` 包含 `CXXABI_1.3.14`

### 结论
- 之前“只要把 Pixi lib 路径补进扩展 `rpath` 就能彻底解决”的假设不够完整。
- 更准确的结论是:
  - 扩展自身的 `RPATH` 已经基本到位
  - 真正缺的是 `pixi run` 进程启动时的全局运行时库优先级
  - 进程更早阶段已经把系统旧版 `libstdc++.so.6` 装入,后续加载 `tinycudann` 扩展时就继续复用了旧库
- 因此修复需要落在两层:
  - `pixi.toml` 里给所有 Pixi 命令统一注入 `LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$CONDA_PREFIX/lib64:...`
  - `install_tinycudann.sh` 里也显式把 Pixi runtime lib 目录放到构建期 `LD_LIBRARY_PATH` / `rpath` 前部,避免安装与运行口径分裂
