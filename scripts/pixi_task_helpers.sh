#!/usr/bin/env bash

# ==============================
# Pixi task 通用 helper
# ==============================

# 某些开发机会遗留失效的本地代理变量。
# 这会让 git / pip 访问 GitHub 时被错误导向 127.0.0.1 或 localhost。
clear_loopback_proxy_vars() {
  local keep_loopback_proxy="${PIXI_KEEP_LOOPBACK_PROXY:-0}"
  local proxy_var=""
  local proxy_value=""
  local cleared=()
  local truthy_pattern='^(1|true|yes|on)$'

  # 默认仍然清理失效的 loopback 代理。
  # 但如果用户明确确认本地代理可用,可以用 PIXI_KEEP_LOOPBACK_PROXY=1 保留它们。
  if [[ "${keep_loopback_proxy,,}" =~ ${truthy_pattern} ]]; then
    return 0
  fi

  for proxy_var in HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy; do
    proxy_value="${!proxy_var:-}"
    if [[ -z "$proxy_value" ]]; then
      continue
    fi

    # 只清理回环地址代理,避免误伤真实可用的远端代理配置。
    if [[ "$proxy_value" =~ ^([A-Za-z0-9+.-]+://)?(127\.0\.0\.1|localhost)(:[0-9]+)?(/.*)?$ ]]; then
      cleared+=("${proxy_var}=${proxy_value}")
      unset "$proxy_var"
    fi
  done

  # 输出一次简短提示,帮助定位“为什么任务里网络行为和外部 shell 不同”。
  if [[ "${#cleared[@]}" -gt 0 ]]; then
    printf 'Detected stale loopback proxy vars, bypassing them for this Pixi task:\n' >&2
    printf '  %s\n' "${cleared[@]}" >&2
  fi
}

# 统一判断某个 Git 仓库里是否已经有指定 commit。
# 这样任务在“本地已经满足条件”时,就可以跳过多余的远程 fetch。
git_repo_has_commit() {
  local repo_path="$1"
  local commit="$2"

  if [[ ! -d "$repo_path/.git" ]]; then
    return 1
  fi

  git -C "$repo_path" cat-file -e "${commit}^{commit}" >/dev/null 2>&1
}
