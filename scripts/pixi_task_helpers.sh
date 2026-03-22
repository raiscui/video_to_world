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

# 把多个目录按 PATH 风格拼成冒号分隔字符串。
# 这里只保留真实存在的目录,避免往环境变量里塞坏路径。
join_colon_paths() {
  local result=""
  local entry=""

  for entry in "$@"; do
    if [[ -z "${entry}" || ! -d "${entry}" ]]; then
      continue
    fi

    if [[ -z "${result}" ]]; then
      result="${entry}"
    else
      result="${result}:${entry}"
    fi
  done

  printf '%s' "${result}"
}

# 把一组目录前置到 PATH / CPATH / LD_LIBRARY_PATH 这类变量前面。
# 这样当前任务优先命中我们刚探测到的 CUDA 工具链路径。
prepend_path_entries() {
  local var_name="$1"
  shift
  local joined=""

  joined="$(join_colon_paths "$@")"
  if [[ -z "${joined}" ]]; then
    return 0
  fi

  if [[ -n "${!var_name:-}" ]]; then
    printf -v "${var_name}" '%s:%s' "${joined}" "${!var_name}"
  else
    printf -v "${var_name}" '%s' "${joined}"
  fi

  export "${var_name}"
}

# 统一探测本机 CUDA toolkit 根目录。
# 顺序保持和仓库现有 tiny-cuda-nn 安装逻辑一致:
# 1. 用户显式导出的 CUDA_HOME
# 2. 最常见的 /usr/local/cuda
# 3. PyTorch 能识别到的 CUDA_HOME
detect_cuda_home() {
  if [[ -n "${CUDA_HOME:-}" && -d "${CUDA_HOME}" ]]; then
    printf '%s\n' "${CUDA_HOME}"
    return 0
  fi

  if [[ -d /usr/local/cuda ]]; then
    printf '/usr/local/cuda\n'
    return 0
  fi

  python - <<'PY'
try:
    from torch.utils.cpp_extension import CUDA_HOME
except Exception:
    CUDA_HOME = None

if CUDA_HOME:
    print(CUDA_HOME)
PY
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
