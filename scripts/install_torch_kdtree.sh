#!/usr/bin/env bash

set -euo pipefail

# ==============================
# torch_kdtree 安装脚本
# ==============================

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"

source "${repo_root}/scripts/pixi_task_helpers.sh"
clear_loopback_proxy_vars

# 避免网络异常时 Git 进入交互等待。
# 这样失败会停在真实错误上,不会长时间沉默卡住。
export GIT_TERMINAL_PROMPT=0

target_repo="${repo_root}/third_party/torch_kdtree"

run_timed_command() {
  local timeout_seconds="$1"
  local description="$2"
  shift 2

  set +e
  timeout "${timeout_seconds}" "$@"
  local exit_code=$?
  set -e

  if [[ "${exit_code}" -ne 0 ]]; then
    printf 'torch_kdtree 安装失败: %s (exit=%s, timeout=%ss)\n' "${description}" "${exit_code}" "${timeout_seconds}" >&2
    return "${exit_code}"
  fi
}

prepare_cuda_build_env() {
  local detected_cuda_home=""
  local detected_nvcc_path=""

  detected_cuda_home="$(detect_cuda_home)"
  detected_nvcc_path="$(cuda_home_nvcc_path "${detected_cuda_home}" || true)"
  if [[ -z "${detected_cuda_home}" || ! -d "${detected_cuda_home}" || -z "${detected_nvcc_path}" ]]; then
    printf 'torch_kdtree 安装失败: 无法定位 CUDA_HOME,请先在 .envrc 或当前 shell 中设置有效的 CUDA toolkit 根目录\n' >&2
    exit 1
  fi

  export CUDA_HOME="${detected_cuda_home}"
  export CUDACXX="${detected_nvcc_path}"
  prepend_path_entries PATH "$(dirname "${detected_nvcc_path}")" "${CUDA_HOME}/bin"
  prepend_path_entries CPATH "${CUDA_HOME}/include" "${CUDA_HOME}/targets/x86_64-linux/include"
  prepend_path_entries CPLUS_INCLUDE_PATH "${CUDA_HOME}/include" "${CUDA_HOME}/targets/x86_64-linux/include"
  prepend_path_entries LIBRARY_PATH "${CUDA_HOME}/lib64" "${CUDA_HOME}/targets/x86_64-linux/lib"
  prepend_path_entries LD_LIBRARY_PATH "${CUDA_HOME}/lib64" "${CUDA_HOME}/targets/x86_64-linux/lib"
  sanitize_torch_cuda_arch_env

  # CMake / nvcc 有时会只认显式编译器路径。
  # 这里提前导出,避免它们继续受外部 PATH 污染。
  export CMAKE_CUDA_COMPILER="${CUDACXX}"

  printf 'torch_kdtree CUDA 环境已准备:\n' >&2
  printf '  CUDA_HOME=%s\n' "${CUDA_HOME}" >&2
  printf '  CUDACXX=%s\n' "${CUDACXX:-<unset>}" >&2
}

ensure_torch_kdtree_repo() {
  mkdir -p "${repo_root}/third_party"

  if [[ ! -d "${target_repo}/.git" ]]; then
    run_timed_command \
      180 \
      "clone torch_kdtree 主仓库" \
      git clone https://github.com/thomgrand/torch_kdtree "${target_repo}"
  fi

  run_timed_command \
    180 \
    "初始化 torch_kdtree 子模块" \
    git -C "${target_repo}" submodule update --init --recursive
}

main() {
  prepare_cuda_build_env
  ensure_torch_kdtree_repo
  python -m pip install -U cmake ninja
  python -m pip install --no-build-isolation "${target_repo}"
}

main "$@"
