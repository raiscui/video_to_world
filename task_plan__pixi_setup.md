# 任务计划: 继续调通 pixi run setup

## [2026-03-22 12:42:35] [Session ID: codex-20260322-124235] [记录类型]: 新建支线计划并承接当前阻塞

### 目标
- 让 `/root/autodl-tmp/home/rais/video_to_world` 中的 `pixi run setup` 可重复执行成功。
- 保留已经验证通过的 `install-gsplat`、`install-tinycudann` 等修复,不要把问题重新引回已通过的阶段。

### 背景承接
- 上一轮已经完成并验证:
  - `setup-depth-anything-3` 通过
  - `install-gsplat` 通过
  - `install-tinycudann` 通过
  - `cuda-nvcc=12.8.*` 已加入 `pixi.toml`
  - 回归测试 `tests/test_install_gsplat_script.py` 与 `tests/test_pixi_manifest.py` 通过
- 当前剩余阻塞集中在 `setup-romav2`。

### 现象
- 已观察到的动态现象:
  - 在带当前 loopback 代理的环境里执行 `git ls-remote https://github.com/Parskatt/RoMaV2 HEAD`,约 5 秒后稳定报:
    - `gnutls_handshake() failed: The TLS connection was non-properly terminated.`
  - 在去掉代理的环境里执行同一命令,20 秒内未返回结果,说明直连也不稳定。
- 这和之前 `DepthAnything-3` / `gsplat` 的网络特征不同:
  - 它们在保留可用代理后能够成功 clone 或安装。
  - `RoMaV2` 当前表现为“代理失败,直连也慢或不稳”。

### 当前主假设
- `setup-romav2` 仍然直接依赖 `git clone https://github.com/Parskatt/RoMaV2 ...`。
- 对这个特定仓库,当前网络环境下 `git` 协议路径不稳,需要改成更稳的获取方式,例如 archive / codeload / 本地镜像优先。

### 最强备选解释
- 也可能不是 clone 方式问题,而是当前工作区已经具备 `third_party/RoMaV2` 与可用 Python 安装,只是 `pixi run setup` 没有重新拿到这份状态。
- 如果动态验证显示当前仓库已存在且 `pip install -e` 可成功,就不应该继续改下载链路。

### 最小验证计划
- 先检查:
  - `third_party/RoMaV2` 是否已经存在有效 Git 仓库
  - 当前 Pixi 环境里是否已经能导入 `romatch` / 本地 RoMaV2 相关包
  - 重新执行一次 `pixi run setup` 时,真实失败点是否仍然是 `setup-romav2`
- 只有在这些验证仍指向 `setup-romav2` 下载链路后,才修改脚本或任务。

### 阶段
- [x] 阶段1: 承接历史结论并隔离到支线上下文
- [x] 阶段2: 复核当前工作区 RoMaV2 与已安装状态
- [ ] 阶段3: 修复 `setup-romav2` 的获取/安装路径
- [ ] 阶段4: 重新执行 `pixi run setup` 并做导入验证
- [ ] 阶段5: 记录交付结果与错误修复经验

### 状态
**目前在阶段3** - 已确认 `third_party/RoMaV2` 缺失、`romav2` 模块未安装,并且 `pixi run setup` 的唯一剩余阻塞确实是 `setup-romav2` 的代理下 `git clone` 失败。

## [2026-03-22 12:46:30] [Session ID: codex-20260322-124235] [记录类型]: 阶段2验证完成,收敛到 `setup-romav2` 的任务级修复

### 新证据
- 工作区状态:
  - `third_party/RoMaV2` 不存在
  - `pixi run python -u - <<'PY' import importlib; importlib.import_module(\"romav2\") PY`
  - 返回 `ModuleNotFoundError: No module named 'romav2'`
  - 同一环境里 `romatch` 可导入,说明 `romatch` 不能替代 `romav2`
- 任务级动态证据:
  - `PIXI_KEEP_LOOPBACK_PROXY=1 pixi run setup` 已完整重现
  - `install-torch-stack`、`setup-depth-anything-3`、`install-gsplat`、`install-tinycudann` 都通过
  - 唯一失败点是:
    - `setup-romav2 -> git clone https://github.com/Parskatt/RoMaV2`
    - 报 `TLS connect error: error:0A000126:SSL routines::unexpected eof while reading`
- 最小替代实验:
  - 去掉代理后 `git ls-remote https://github.com/Parskatt/RoMaV2 HEAD` 可返回:
    - `7151f3846ad0c89c213afb6803966484a6dd76e0`
  - 去掉代理后 `curl -I -L https://codeload.github.com/Parskatt/RoMaV2/tar.gz/refs/heads/main` 立即返回 `HTTP/2 200`

### 结论
- 上一条“也许当前工作区已经有可复用 RoMaV2”的备选解释不成立。
- 当前主假设被动态证据支撑:
  - 失败根因不是 `setup` 其他阶段,而是 `setup-romav2` 继续沿用“保留 loopback 代理的 GitHub clone 路径”。
- 新补充的动态证据又进一步推翻了“只要去代理 git clone 就够”的子假设:
  - `git clone --depth 1 ...` 在去代理后不再 TLS EOF,但会长时间挂住,超过预期窗口仍未完成
  - `git apply` 已验证可以直接作用于非 Git 仓库目录
- 随后用户又明确要求使用:
  - `https_proxy=http://127.0.0.1:7897`
  - `http_proxy=http://127.0.0.1:7897`
  - `all_proxy=socks5://127.0.0.1:7897`
- 按该组合做新的最小验证后:
  - `curl -I -L https://codeload.github.com/Parskatt/RoMaV2/tar.gz/refs/heads/main`
  - 已返回 `HTTP/2 200`
- 因此,上一条“archive 下载也必须绕过代理”的判断被新证据推翻。
- 当前正式修复口径更新为:
  - 把 `setup-romav2` 抽成独立脚本
  - 下载路径切到 `codeload.github.com` archive
  - archive 下载沿用用户显式提供的代理环境
  - 保留坏 cache 清理与 `pip install -e` 逻辑
  - 不再依赖不可靠的 `git apply` 判断,直接显式修正 `pyproject.toml` 里的 `dataclasses>=0.8`

## [2026-03-22 21:12:24] [Session ID: codex-20260322-211224] [记录类型]: 承接 `tinycudann` 运行时验证并转入脚本固化

### 新证据
- 动态验证命令:
  - `env LD_LIBRARY_PATH="$PWD/.pixi/envs/default/lib:$PWD/.pixi/envs/default/lib64:${LD_LIBRARY_PATH:-}" pixi run python -u - <<'PY'`
  - `import tinycudann`
- 结果:
  - 返回 `tinycudann=ok`
- 这说明 `tinycudann` 之前的失败不是安装缺失,而是运行时优先捡到了系统 `/usr/lib/x86_64-linux-gnu/libstdc++.so.6`,没有先用 Pixi 环境里的较新 `libstdc++`。

### 当前计划
- 先检查 `scripts/install_tinycudann.sh` 对 `LD_LIBRARY_PATH`、`rpath`、`LDFLAGS` 的现状。
- 如果静态阅读与动态证据一致,就把 `.pixi/envs/default/lib` 和 `.pixi/envs/default/lib64` 固化进安装脚本,然后重装并做完整导入验证。

### 阶段
- [x] 阶段1: 承接历史结论并隔离到支线上下文
- [x] 阶段2: 复核当前工作区 RoMaV2 与已安装状态
- [x] 阶段3: 修复 `setup-romav2` 的获取/安装路径
- [ ] 阶段4: 修复 `tinycudann` 运行时库路径并重新执行验证
- [ ] 阶段5: 记录交付结果与错误修复经验

### 状态
**目前在阶段4** - 已用动态验证确认 `tinycudann` 需要优先加载 Pixi 环境内的 `libstdc++`,下一步把该行为固化进安装脚本并重新跑验证。

## [2026-03-22 21:12:24] [Session ID: codex-20260322-211224] [记录类型]: 阶段4最小验证通过,转入完整 setup 复跑

### 已验证结果
- `timeout 120s pixi run python -m unittest tests/test_pixi_manifest.py tests/test_install_gsplat_script.py tests/test_setup_romav2_script.py`
  - `Ran 12 tests ... OK`
- `timeout 60s pixi run python -u - <<'PY'`
  - 已打印 `LD_LIBRARY_PATH=/root/.../.pixi/envs/default/lib:/root/.../.pixi/envs/default/lib64:...`
  - 并成功返回 `tinycudann=ok`

### 当前判断
- `pixi.toml` 的 `activation.env` 已生效。
- `tinycudann` 的运行时导入问题已从“候选修复”升级为“有动态证据支撑的已修复状态”。
- 下一步还需要完整重跑一次 `pixi run setup`,确认代理下载链路与安装链路一起没有回退。

### 状态
**目前仍在阶段4** - 最小导入验证和回归测试都已通过,现在进入带代理的完整 `pixi run setup` 复跑。

## [2026-03-22 21:12:24] [Session ID: codex-20260322-211224] [记录类型]: 阶段4与阶段5完成,支线交付收尾

### 最终验证
- `timeout 120s pixi run python -m unittest tests/test_pixi_manifest.py tests/test_install_gsplat_script.py tests/test_setup_romav2_script.py`
  - `Ran 12 tests in 0.433s`
  - `OK`
- 带用户指定代理执行:
  - `timeout 1800s pixi run setup`
  - 已完整通过,包含 `install-tinycudann` 与 `setup-romav2`
- 带用户指定代理执行联合导入:
  - `import romav2`
  - `import romatch`
  - `import gsplat`
  - `import tinycudann`
  - 四者全部返回 `=ok`

### 结论
- 本支线目标已完成:
  - `pixi run setup` 可以在用户指定代理环境下稳定执行完成
  - `tinycudann` 的运行时导入问题已修复
  - `RoMaV2` 的代理下载与安装链路已保持可用

### 阶段
- [x] 阶段1: 承接历史结论并隔离到支线上下文
- [x] 阶段2: 复核当前工作区 RoMaV2 与已安装状态
- [x] 阶段3: 修复 `setup-romav2` 的获取/安装路径
- [x] 阶段4: 修复 `tinycudann` 运行时库路径并重新执行验证
- [x] 阶段5: 记录交付结果与错误修复经验

### 状态
**目前已完成** - `pixi run setup` 与安装后导入验证均已通过,本支线可以交付。
