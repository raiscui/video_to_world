# 错误修复记录: git 发布支线

## [2026-03-21 23:57:50] [Session ID: 2435180] 问题: 发布前验证被 lint 与失效代理阻塞

### 现象
- `pixi run ruff check .` 首次失败在 `algos/non_rigid_icp.py`。
- `git fetch origin --prune` 首次失败并指向 `127.0.0.1:7897`。

### 假设
- lint 失败来自已经不再使用的旧局部变量。
- Git 失败来自当前 shell 残留的失效 loopback 代理,不是远程仓库本身离线。

### 验证
- 静态证据:
  - 阅读 `algos/non_rigid_icp.py` 报错附近代码后,确认 `roma_loss_val` 和 `color_icp_val` 后续没有被消费。
  - 打印环境变量后确认存在:
    - `http_proxy=http://127.0.0.1:7897`
    - `https_proxy=http://127.0.0.1:7897`
    - `all_proxy=socks5://127.0.0.1:7897`
- 动态证据:
  - 删除两行冗余赋值后,`pixi run ruff check .` 通过。
  - 在单次命令里 `env -u ...` 清掉代理变量后:
    - `git ls-remote origin HEAD` 成功返回 `94fb051...`
    - `git fetch origin --prune` 成功

### 原因
- 已验证结论:
  - lint 阻塞来自两行未使用变量。
  - 远程 Git 阻塞来自当前会话中的坏 loopback 代理。

### 修复
- 删除 `algos/non_rigid_icp.py` 中 2 行无用变量赋值。
- 所有远程 Git 命令改为在单次命令内临时去掉代理变量执行。

### 验证结果
- `pixi run test` 通过。
- `pixi run ruff check .` 通过。
- `git push origin main` 已在去代理环境下成功完成。

## [2026-03-22 02:00:30] [Session ID: 2479889] 问题: 最后一次发布时,去代理后的 HTTPS push 仍被 HTTP/2 传输错误打断

### 现象
- 在已经去掉 `127.0.0.1:7897` 代理的前提下,`git push origin main` 失败。
- 报错为: `Error in the HTTP2 framing layer`。
- 同一时刻,`git ls-remote origin refs/heads/main` 仍然可以成功访问远程。

### 假设
- 主假设:
  - 这是 GitHub HTTPS 连接上的瞬时 HTTP/2 传输问题。
- 备选解释:
  - 也可能是本地网络对 HTTP/2 的某些连接复用或 framing 处理不稳定。

### 验证
- 动态证据:
  - 去代理环境下 `git ls-remote origin refs/heads/main` 成功,返回旧远程头 `465421d...`。
  - 仅对本次 push 增加 `-c http.version=HTTP/1.1` 后,`git push origin main` 成功。
  - 随后再次 `git ls-remote origin refs/heads/main`,返回新远程头 `9ff571ce99cd5692ccc504dc550644c7c9412ab7`。

### 原因
- 已验证结论:
  - 问题不在 Git 认证,也不在仓库权限。
  - 首次失败点落在 HTTP/2 传输层,切换到 HTTP/1.1 即可绕过。

### 修复
- 不修改全局 Git 配置。
- 仅在本次命令里使用:
  - `git -c http.version=HTTP/1.1 push origin main`

### 验证结果
- 推送成功。
- 远程 `main` 已更新到 `9ff571ce99cd5692ccc504dc550644c7c9412ab7`。
