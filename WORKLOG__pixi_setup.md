## [2026-03-22 21:12:24] [Session ID: codex-20260322-211224] 任务名称: 修复 Pixi setup 在代理环境下的依赖安装与运行时导入

### 任务内容
- 调整 `setup-romav2` 的源码获取方式,让它在用户指定的 loopback 代理下改走 `codeload.github.com` 归档下载。
- 修复 `tinycudann` 在 Pixi 环境里的运行时库优先级问题,避免导入时误用系统旧版 `libstdc++.so.6`。
- 补充清单测试,把 `pixi.toml` 的运行时环境约束和 `install_tinycudann.sh` 的路径顺序锁住。

### 完成过程
- 先用动态验证确认: `LD_LIBRARY_PATH` 只要把 `.pixi/envs/default/lib` 放到最前面, `tinycudann` 就能立即成功导入。
- 再用 `readelf` / `ldd` / `strings` 对照扩展的 `RPATH` 和系统 `libstdc++` 版本,确认真正缺的是 Pixi 进程启动时的全局运行时库优先级。
- 在 `pixi.toml` 新增 `[activation.env]` 的 `LD_LIBRARY_PATH`,并在 `scripts/install_tinycudann.sh` 里显式把 Pixi runtime lib 目录加入构建期 `LIBRARY_PATH`、`LD_LIBRARY_PATH` 与 `rpath`。
- 带用户给定代理重新执行 `pixi run setup`,随后联合导入 `romav2`、`romatch`、`gsplat`、`tinycudann`,全部通过。

### 总结感悟
- 这次最容易误判的点是: 扩展文件已经有 `RPATH`,但进程级别还是可能先装入系统旧库,所以只盯扩展自身并不够。
- 对 Pixi 这类环境管理器,安装期和运行期要分开看。安装成功不代表后续 `pixi run python` 的运行时库优先级就一定正确。
