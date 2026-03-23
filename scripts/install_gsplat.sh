#!/usr/bin/env bash

set -euo pipefail

# ==============================
# gsplat 安装脚本
# ==============================

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

source "${repo_root}/scripts/pixi_task_helpers.sh"
clear_loopback_proxy_vars

# 避免 git 在没有网络或权限时进入交互等待。
# 这样失败会更快暴露成可读错误,而不是长时间卡住。
export GIT_TERMINAL_PROMPT=0

target_repo="${repo_root}/third_party/gsplat"
target_commit="937e29912570c372bed6747a5c9bf85fed877bae"
glm_submodule_path="gsplat/cuda/csrc/third_party/glm"
glm_header="${target_repo}/${glm_submodule_path}/glm/gtc/type_ptr.hpp"
glm_local_dir="${GSPLAT_GLM_LOCAL_DIR:-}"

run_timed_command() {
  local description="$1"
  shift

  set +e
  timeout 180s "$@"
  local exit_code=$?
  set -e

  if [[ "${exit_code}" -ne 0 ]]; then
    printf 'gsplat 安装失败: %s (exit=%s)\n' "${description}" "${exit_code}" >&2
    return "${exit_code}"
  fi
}

ensure_gsplat_repo() {
  mkdir -p "${repo_root}/third_party"

  # 优先复用本地 checkout。
  # 只有仓库根本不存在时,才需要重新 clone。
  if [[ ! -d "${target_repo}/.git" ]]; then
    run_timed_command \
      "clone gsplat 主仓库" \
      git clone https://github.com/nerfstudio-project/gsplat.git "${target_repo}"
  fi

  # 如果目标 commit 本地已存在,就不要强行 fetch。
  # 这样在离线或 GitHub 暂时不可达时也能复用已有 checkout。
  if git_repo_has_commit "${target_repo}" "${target_commit}"; then
    echo "gsplat target commit already available locally"
  else
    run_timed_command \
      "fetch gsplat tags" \
      git -C "${target_repo}" fetch --tags --force
  fi

  git -C "${target_repo}" checkout "${target_commit}"
}

repair_broken_glm_submodule() {
  local module_git_dir="${target_repo}/.git/modules/${glm_submodule_path}"

  # 当目录里只有 `.git` 文件、没有真正头文件时,这是坏掉的子模块状态。
  # 这时直接 `submodule update` 往往不会自愈,需要先清掉旧残留。
  if git -C "${target_repo}/${glm_submodule_path}" rev-parse --verify HEAD >/dev/null 2>&1; then
    echo "glm submodule HEAD exists, but headers are still missing; forcing a clean re-sync"
  else
    echo "Detected broken glm submodule checkout, resetting it before retry"
  fi

  git -C "${target_repo}" submodule deinit -f -- "${glm_submodule_path}" >/dev/null 2>&1 || true
  rm -rf "${target_repo}/${glm_submodule_path}" "${module_git_dir}"
  git -C "${target_repo}" submodule sync --recursive -- "${glm_submodule_path}" >/dev/null 2>&1 || true
}

find_local_glm_source() {
  local candidate_root=""
  local candidate_header=""

  # 允许用户在 `.envrc` 中显式指定本地 glm 源目录。
  # 目录本身应当直接包含 `glm/gtc/type_ptr.hpp` 这类头文件树。
  if [[ -n "${glm_local_dir}" ]]; then
    if [[ -f "${glm_local_dir}/glm/gtc/type_ptr.hpp" ]]; then
      printf '%s\n' "${glm_local_dir}"
      return 0
    fi

    printf 'GSPLAT_GLM_LOCAL_DIR 已设置,但未找到头文件: %s/glm/gtc/type_ptr.hpp\n' "${glm_local_dir}" >&2
  fi

  while IFS= read -r candidate_header; do
    candidate_root="${candidate_header%/glm/gtc/type_ptr.hpp}"

    if [[ "${candidate_root}" == "${target_repo}/${glm_submodule_path}" ]]; then
      continue
    fi

    if [[ -f "${candidate_root}/glm/gtc/type_ptr.hpp" ]]; then
      printf '%s\n' "${candidate_root}"
      return 0
    fi
  done < <(
    find /workspace -path '*/site-packages/gsplat/cuda/csrc/third_party/glm/glm/gtc/type_ptr.hpp' 2>/dev/null
    find /workspace -path '*/third_party/glm/glm/gtc/type_ptr.hpp' 2>/dev/null
    find /usr/include /usr/local/include /opt -path '*/glm/gtc/type_ptr.hpp' 2>/dev/null
  )

  return 1
}

populate_glm_from_local_source() {
  local local_glm_root="$1"

  echo "Using local glm headers from ${local_glm_root}"
  rm -rf "${target_repo}/${glm_submodule_path}"
  mkdir -p "${target_repo}/${glm_submodule_path}"
  cp -a "${local_glm_root}/glm" "${target_repo}/${glm_submodule_path}/"
}

ensure_glm_headers() {
  local local_glm_root=""

  # 真正构建前先看头文件是否存在。
  # 这样能把错误停在“依赖不完整”这一层,而不是拖到后面的 ninja 编译。
  if [[ -f "${glm_header}" ]]; then
    echo "glm headers already present"
    return 0
  fi

  repair_broken_glm_submodule

  # 先尝试复用本地现成 glm 源。
  # 对网络不稳定或 GitHub 子模块仓库访问受限的机器,这条路径会更稳。
  if local_glm_root="$(find_local_glm_source)"; then
    populate_glm_from_local_source "${local_glm_root}"
  else
    run_timed_command \
      "初始化 gsplat 的 glm 子模块" \
      git -C "${target_repo}" submodule update --init --recursive -- "${glm_submodule_path}"
  fi

  if [[ -f "${glm_header}" ]]; then
    echo "glm headers restored successfully"
    return 0
  fi

  printf 'gsplat 安装失败: 缺少必需头文件 %s\n' "${glm_header}" >&2
  printf '这通常表示 glm 子模块没有成功拉取完成,且当前机器也没有可复用的本地 glm 头文件源。\n' >&2
  exit 1
}

prepare_cuda_build_env() {
  local detected_cuda_home=""
  local detected_nvcc_path=""
  local include_roots=""
  local library_roots=""

  detected_cuda_home="$(detect_cuda_home || true)"
  detected_nvcc_path="$(cuda_home_nvcc_path "${detected_cuda_home}" || true)"
  if [[ -z "${detected_cuda_home}" || -z "${detected_nvcc_path}" ]]; then
    printf 'gsplat 安装失败: 无法定位包含 nvcc 的 CUDA_HOME。\n' >&2
    printf '请先确保 pixi 环境或系统环境里存在可执行的 nvcc,再继续编译 gsplat。\n' >&2
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

  include_roots="$(join_colon_paths "${CUDA_HOME}/include" "${CUDA_HOME}/targets/x86_64-linux/include")"
  library_roots="$(join_colon_paths "${CUDA_HOME}/lib64" "${CUDA_HOME}/targets/x86_64-linux/lib")"

  printf 'gsplat CUDA build env prepared:\n' >&2
  printf '  CUDA_HOME=%s\n' "${CUDA_HOME}" >&2
  printf '  CUDACXX=%s\n' "${CUDACXX}" >&2
  printf '  include roots=%s\n' "${include_roots:-<none>}" >&2
  printf '  library roots=%s\n' "${library_roots:-<none>}" >&2
}

main() {
  ensure_gsplat_repo
  ensure_glm_headers
  prepare_cuda_build_env
  python -m pip install --no-build-isolation "${target_repo}"
}

main "$@"
