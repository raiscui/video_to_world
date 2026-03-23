#!/usr/bin/env bash

# ==============================
# Pixi task 通用 helper
# ==============================

# 某些开发机会遗留失效的本地代理变量。
# 这会让 git / pip 访问 GitHub 时被错误导向 127.0.0.1 或 localhost。
loopback_proxy_is_alive() {
  local proxy_value="$1"

  python - "${proxy_value}" <<'PY'
import socket
import sys
from urllib.parse import urlparse

proxy = sys.argv[1]
normalized = proxy if "://" in proxy else f"http://{proxy}"
parsed = urlparse(normalized)

if not parsed.hostname or not parsed.port:
    raise SystemExit(1)

sock = socket.socket()
sock.settimeout(0.75)
try:
    sock.connect((parsed.hostname, parsed.port))
except OSError:
    raise SystemExit(1)
finally:
    sock.close()
PY
}

clear_loopback_proxy_vars() {
  local keep_loopback_proxy="${PIXI_KEEP_LOOPBACK_PROXY:-0}"
  local proxy_var=""
  local proxy_value=""
  local cleared=()
  local kept=()
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
      # 当前机器上的 loopback 代理有时是真活的。
      # 这时不应再沿用“看见 127.0.0.1 就清掉”的旧策略。
      if loopback_proxy_is_alive "${proxy_value}"; then
        kept+=("${proxy_var}=${proxy_value}")
        continue
      fi

      cleared+=("${proxy_var}=${proxy_value}")
      unset "$proxy_var"
    fi
  done

  # 输出一次简短提示,帮助定位“为什么任务里网络行为和外部 shell 不同”。
  if [[ "${#kept[@]}" -gt 0 ]]; then
    printf 'Keeping reachable loopback proxy vars for this Pixi task:\n' >&2
    printf '  %s\n' "${kept[@]}" >&2
  fi

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

# 在不同发行方式下,`nvcc` 可能位于两种常见布局:
# 1. `<cuda_home>/bin/nvcc`
# 2. `<cuda_home>/targets/x86_64-linux/bin/nvcc`
# 这里统一返回当前前缀下真实可执行的 `nvcc` 路径。
cuda_home_nvcc_path() {
  local candidate="${1:-}"

  if [[ -z "${candidate}" ]]; then
    return 1
  fi

  if [[ -x "${candidate}/bin/nvcc" ]]; then
    printf '%s\n' "${candidate}/bin/nvcc"
    return 0
  fi

  if [[ -x "${candidate}/targets/x86_64-linux/bin/nvcc" ]]; then
    printf '%s\n' "${candidate}/targets/x86_64-linux/bin/nvcc"
    return 0
  fi

  return 1
}

# 判断某个 CUDA 前缀下是否真的带有 nvcc。
# 这里不再只看目录存在,因为当前机器上曾出现过
# `CUDA_HOME=/usr/local/cuda` 但 `bin/nvcc` 实际缺失的空壳路径。
cuda_home_has_nvcc() {
  local candidate="${1:-}"

  cuda_home_nvcc_path "${candidate}" >/dev/null 2>&1
}

# 从 `nvcc` 可执行文件路径反推 CUDA 根目录。
# 这里同时兼容系统 CUDA 和 conda/pixi 的 `targets/x86_64-linux/bin/nvcc` 布局。
cuda_home_from_nvcc_path() {
  local nvcc_path="${1:-}"

  if [[ -z "${nvcc_path}" || ! -x "${nvcc_path}" ]]; then
    return 1
  fi

  case "${nvcc_path}" in
    */targets/x86_64-linux/bin/nvcc)
      cd -- "$(dirname -- "${nvcc_path}")/../../.." && pwd
      ;;
    */bin/nvcc)
      cd -- "$(dirname -- "${nvcc_path}")/.." && pwd
      ;;
    *)
      return 1
      ;;
  esac
}

# 统一探测本机 CUDA toolkit 根目录。
# 顺序保持和仓库现有 tiny-cuda-nn 安装逻辑一致:
# 1. 用户显式导出的 CUDA_HOME
# 2. pixi / conda 当前环境前缀
# 3. 最常见的 /usr/local/cuda
# 4. PATH 中真实存在的 nvcc
# 5. PyTorch 能识别到的 CUDA_HOME
detect_cuda_home() {
  local candidate=""
  local nvcc_path=""

  if cuda_home_has_nvcc "${CUDA_HOME:-}"; then
    printf '%s\n' "${CUDA_HOME}"
    return 0
  fi

  if cuda_home_has_nvcc "${CONDA_PREFIX:-}"; then
    printf '%s\n' "${CONDA_PREFIX}"
    return 0
  fi

  if cuda_home_has_nvcc "/usr/local/cuda"; then
    printf '/usr/local/cuda\n'
    return 0
  fi

  nvcc_path="$(command -v nvcc || true)"
  if candidate="$(cuda_home_from_nvcc_path "${nvcc_path}" 2>/dev/null)"; then
    printf '%s\n' "${candidate}"
    return 0
  fi

  candidate="$(python - <<'PY'
try:
    from torch.utils.cpp_extension import CUDA_HOME
except Exception:
    CUDA_HOME = None

if CUDA_HOME:
    print(CUDA_HOME)
PY
)"

  if cuda_home_has_nvcc "${candidate}"; then
    printf '%s\n' "${candidate}"
    return 0
  fi

  return 1
}

# conda-forge 的 `cuda-nvcc` 激活脚本会默认导出一串很宽的
# `TORCH_CUDA_ARCH_LIST` / `CUDAARCHS`,其中可能包含当前 PyTorch
# 还不认识的架构值(例如本机实测出现过 `10.1`)。
# 这里统一把它收敛成“当前可见 GPU + 当前 PyTorch 真正支持”的交集。
compute_visible_torch_cuda_arch_list() {
  python - <<'PY'
import re
import sys

try:
    import torch
except Exception:
    raise SystemExit(1)

if not torch.cuda.is_available() or torch.cuda.device_count() == 0:
    raise SystemExit(1)

supported = set()
for arch in torch.cuda.get_arch_list():
    if not arch.startswith("sm_"):
        continue
    digits = re.findall(r"\d+", arch.split("_", 1)[1])
    if not digits:
        continue
    sm = int(digits[0])
    supported.add(f"{sm // 10}.{sm % 10}")

if not supported:
    raise SystemExit(1)

arch_list: list[str] = []
for index in range(torch.cuda.device_count()):
    capability = torch.cuda.get_device_capability(index)
    arch = f"{capability[0]}.{capability[1]}"
    if arch in supported and arch not in arch_list:
        arch_list.append(arch)

if not arch_list:
    raise SystemExit(1)

arch_list = sorted(arch_list, key=lambda item: tuple(int(part) for part in item.split(".")))
arch_list[-1] += "+PTX"
print(";".join(arch_list))
PY
}

sanitize_torch_cuda_arch_env() {
  local sanitized_arch_list=""

  sanitized_arch_list="$(compute_visible_torch_cuda_arch_list || true)"
  unset CUDAARCHS

  if [[ -n "${sanitized_arch_list}" ]]; then
    export TORCH_CUDA_ARCH_LIST="${sanitized_arch_list}"
    printf 'Using sanitized TORCH_CUDA_ARCH_LIST=%s\n' "${TORCH_CUDA_ARCH_LIST}" >&2
    return 0
  fi

  unset TORCH_CUDA_ARCH_LIST
  printf 'Unable to infer a safe TORCH_CUDA_ARCH_LIST from visible GPUs; leaving it unset\n' >&2
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
