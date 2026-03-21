# 研究笔记: git 发布支线

## [2026-03-21 23:57:48] [Session ID: 2435180] 笔记: 本次发布前的验证结论

### 来源
- 本地命令:
  - `timeout 600s pixi run test`
  - `pixi run ruff check .`
  - `env -u http_proxy -u https_proxy -u all_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY git ls-remote origin HEAD`
  - `timeout 30s env -u http_proxy -u https_proxy -u all_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY git fetch origin --prune`

### 要点
- `pixi run test` 已通过,共 16 个测试。
- 初次 `pixi run ruff check .` 失败在 `algos/non_rigid_icp.py` 的两个未使用变量。
- 删除两行冗余赋值后,`pixi run ruff check .` 已通过。
- 远程 GitHub 仓库并未失联。
- 真正的网络阻塞来自当前 shell 中残留的失效 loopback 代理:
  - `http_proxy=http://127.0.0.1:7897`
  - `https_proxy=http://127.0.0.1:7897`
  - `all_proxy=socks5://127.0.0.1:7897`
- 在单次命令里临时清掉这些代理变量后:
  - `git ls-remote origin HEAD` 返回 `94fb051...`
  - `git fetch origin --prune` 成功

### 综合判断
- 本次可以安全提交。
- 提交与推送阶段应继续沿用“单次命令去代理”的方式,避免污染用户全局环境。
