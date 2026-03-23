#!/usr/bin/env bash

set -euo pipefail

# ==============================
# tiny-cuda-nn 安装脚本
# ==============================

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

source "${repo_root}/scripts/pixi_task_helpers.sh"
clear_loopback_proxy_vars

# 避免 Git 在网络异常时进入交互等待。
# 这样失败会尽快变成可见错误,不会让 `pixi run setup` 长时间沉默卡住。
export GIT_TERMINAL_PROMPT=0

target_repo="${TINYCUDANN_LOCAL_REPO:-/tmp/video_to_world-tiny-cuda-nn}"
target_binding_dir="${target_repo}/bindings/torch"
archive_cache_dir="${TINYCUDANN_ARCHIVE_CACHE_DIR:-/tmp/video_to_world-tinycudann-archives}"

run_timed_command() {
  local timeout_seconds="$1"
  local description="$2"
  shift
  shift

  set +e
  timeout "${timeout_seconds}" "$@"
  local exit_code=$?
  set -e

  if [[ "${exit_code}" -ne 0 ]]; then
    printf 'tiny-cuda-nn 安装失败: %s (exit=%s, timeout=%ss)\n' "${description}" "${exit_code}" "${timeout_seconds}" >&2
    return "${exit_code}"
  fi
}

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

prepend_linker_flags() {
  local var_name="$1"
  shift
  local flags="$*"

  if [[ -z "${flags}" ]]; then
    return 0
  fi

  if [[ -n "${!var_name:-}" ]]; then
    printf -v "${var_name}" '%s %s' "${flags}" "${!var_name}"
  else
    printf -v "${var_name}" '%s' "${flags}"
  fi

  export "${var_name}"
}

collect_pixi_nvidia_paths() {
  local path_kind="$1"

  python - "${path_kind}" <<'PY'
import site
import sys
from pathlib import Path

path_kind = sys.argv[1]
roots: list[str] = []

try:
    roots.extend(site.getsitepackages())
except Exception:
    pass

try:
    user_site = site.getusersitepackages()
except Exception:
    user_site = None

if user_site:
    roots.append(user_site)

seen: set[str] = set()
for base in roots:
    nvidia_root = Path(base) / "nvidia"
    if not nvidia_root.is_dir():
        continue

    for child in sorted(nvidia_root.iterdir()):
        if not child.is_dir() or child.name == "__pycache__":
            continue

        candidate = child / path_kind
        if candidate.is_dir():
            resolved = str(candidate.resolve())
            if resolved not in seen:
                seen.add(resolved)
                print(resolved)
PY
}

create_nvidia_link_shims() {
  local shim_dir="$1"
  shift
  local lib_dir=""
  local lib_path=""
  local lib_name=""
  local plain_name=""

  rm -rf "${shim_dir}"
  mkdir -p "${shim_dir}"

  # NVIDIA 的 PyPI wheel 常常只带 `libfoo.so.12` 这种带版本号文件。
  # 链接器处理 `-lfoo` 时需要 `libfoo.so`,所以这里生成一层临时别名。
  shopt -s nullglob
  for lib_dir in "$@"; do
    if [[ ! -d "${lib_dir}" ]]; then
      continue
    fi

    for lib_path in "${lib_dir}"/lib*.so.*; do
      lib_name="$(basename "${lib_path}")"
      plain_name="${lib_name%%.so.*}.so"

      if [[ -z "${plain_name}" || -e "${shim_dir}/${plain_name}" ]]; then
        continue
      fi

      ln -s "${lib_path}" "${shim_dir}/${plain_name}"
    done
  done
  shopt -u nullglob
}

build_rpath_flags() {
  local dir=""

  for dir in "$@"; do
    if [[ -d "${dir}" ]]; then
      printf '%s ' "-Wl,-rpath,${dir}"
    fi
  done
}

github_codeload_url() {
  local repo_url="$1"
  local commit="$2"
  local normalized="${repo_url%.git}"

  if [[ "${normalized}" =~ ^https://github\.com/([^/]+)/([^/]+)$ ]]; then
    printf 'https://codeload.github.com/%s/%s/tar.gz/%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${commit}"
    return 0
  fi

  printf 'tiny-cuda-nn 安装失败: 无法从子模块 URL 推导 codeload 地址: %s\n' "${repo_url}" >&2
  exit 1
}

submodule_commit() {
  local submodule_path="$1"

  git -C "${target_repo}" ls-tree HEAD "${submodule_path}" | awk '{print $3}'
}

submodule_url() {
  local submodule_path="$1"

  git -C "${target_repo}" config --file .gitmodules --get "submodule.${submodule_path}.url"
}

extract_submodule_archive() {
  local archive_path="$1"
  local target_dir="$2"
  local marker_relpath="$3"
  local module_git_dir="$4"
  local tar_exit=0

  rm -rf "${target_dir}" "${module_git_dir}"
  mkdir -p "${target_dir}"

  set +e
  tar -xzf "${archive_path}" -C "${target_dir}" --strip-components=1 >/dev/null 2>&1
  tar_exit=$?
  set -e

  if [[ "${tar_exit}" -ne 0 ]]; then
    printf 'tiny-cuda-nn 提示: 归档解压未完全成功,继续检查关键文件是否已到位: %s\n' "${archive_path}" >&2
  fi

  [[ -f "${target_dir}/${marker_relpath}" ]]
}

populate_submodule_from_tarball() {
  local submodule_path="$1"
  local marker_relpath="$2"
  local commit=""
  local repo_url=""
  local codeload_url=""
  local archive_path=""
  local archive_name=""
  local module_git_dir=""
  local target_dir="${target_repo}/${submodule_path}"

  if [[ -f "${target_dir}/${marker_relpath}" ]]; then
    echo "tiny-cuda-nn dependency already present: ${submodule_path}"
    return 0
  fi

  commit="$(submodule_commit "${submodule_path}")"
  repo_url="$(submodule_url "${submodule_path}")"

  if [[ -z "${commit}" || -z "${repo_url}" ]]; then
    printf 'tiny-cuda-nn 安装失败: 无法解析子模块信息 %s\n' "${submodule_path}" >&2
    exit 1
  fi

  codeload_url="$(github_codeload_url "${repo_url}" "${commit}")"
  archive_name="${submodule_path##*/}-${commit}.tar.gz"
  mkdir -p "${archive_cache_dir}"
  archive_path="${archive_cache_dir}/${archive_name}"
  module_git_dir="${target_repo}/.git/modules/${submodule_path}"

  # 先尝试复用已有归档。
  # 对 cutlass 这类大依赖,即使归档不是 100% 完整,只要关键头文件已经到位就足够继续构建。
  if [[ -f "${archive_path}" ]]; then
    if extract_submodule_archive "${archive_path}" "${target_dir}" "${marker_relpath}" "${module_git_dir}"; then
      echo "tiny-cuda-nn dependency restored from cached archive: ${submodule_path}"
      return 0
    fi

    printf 'tiny-cuda-nn 提示: 现有归档仍不足以恢复 %s,将重新下载\n' "${submodule_path}" >&2
    rm -f "${archive_path}"
  fi

  run_timed_command \
    900 \
    "下载 ${submodule_path} 的 tarball" \
    curl --http1.1 --continue-at - --retry 5 --retry-delay 2 --retry-all-errors -L --fail -o "${archive_path}" "${codeload_url}"

  if ! extract_submodule_archive "${archive_path}" "${target_dir}" "${marker_relpath}" "${module_git_dir}"; then
    printf 'tiny-cuda-nn 安装失败: tarball 解压后仍缺少文件 %s/%s\n' "${target_dir}" "${marker_relpath}" >&2
    exit 1
  fi
}

ensure_tinycudann_repo() {
  mkdir -p "$(dirname "${target_repo}")"

  # 目录存在但不是 Git 仓库时,大概率是上次中断留下的半成品。
  # 这种状态继续复用通常只会把错误拖到更后面。
  if [[ -e "${target_repo}" && ! -d "${target_repo}/.git" ]]; then
    echo "Detected incomplete tiny-cuda-nn checkout, recreating it"
    rm -rf "${target_repo}"
  fi

  # 某些机器在仓库工作树内 checkout 这个依赖会异常慢。
  # 如果缓存目录里已经留下“只有 .git、没有源码文件”的半成品,直接重建更稳。
  if [[ -d "${target_repo}/.git" && ! -f "${target_binding_dir}/setup.py" ]]; then
    echo "Detected incomplete tiny-cuda-nn worktree, recreating it"
    rm -rf "${target_repo}"
  fi

  # 优先复用已存在的本地 clone。
  # 这能避开 `pip install git+...` 每次都重新拉源码带来的不稳定性。
  if [[ ! -d "${target_repo}/.git" ]]; then
    run_timed_command \
      180 \
      "clone tiny-cuda-nn 主仓库" \
      git clone https://github.com/NVlabs/tiny-cuda-nn/ "${target_repo}"
  else
    echo "tiny-cuda-nn local checkout already available at ${target_repo}"
  fi
}

ensure_tinycudann_dependencies() {
  # `bindings/torch/setup.py` 会直接引用仓库根目录下的 `dependencies/*` 源文件。
  # 当前机器上 Git 子模块 clone 很不稳定,所以这里直接按锁定 commit 下载源码 tarball。
  populate_submodule_from_tarball "dependencies/cmrc" "CMakeRC.cmake"
  populate_submodule_from_tarball "dependencies/cutlass" "include/cutlass/cutlass.h"
  populate_submodule_from_tarball "dependencies/fmt" "include/fmt/core.h"
}

prepare_cuda_build_env() {
  local detected_cuda_home=""
  local detected_nvcc_path=""
  local link_shim_dir="/tmp/video_to_world-tinycudann-link-shims"
  local rpath_flags=""
  local lib_flags=""
  local include_flags=""
  local system_include_dirs=()
  local system_lib_dirs=()
  local pixi_runtime_lib_dirs=()
  local nvidia_include_dirs=()
  local nvidia_lib_dirs=()

  detected_cuda_home="$(detect_cuda_home)"
  detected_nvcc_path="$(cuda_home_nvcc_path "${detected_cuda_home}" || true)"
  if [[ -z "${detected_cuda_home}" || ! -d "${detected_cuda_home}" || -z "${detected_nvcc_path}" ]]; then
    printf 'tiny-cuda-nn 安装失败: 无法定位 CUDA_HOME,当前机器缺少可用 CUDA toolkit\n' >&2
    exit 1
  fi

  export CUDA_HOME="${detected_cuda_home}"
  export CUDACXX="${detected_nvcc_path}"
  prepend_path_entries PATH "$(dirname "${detected_nvcc_path}")" "${CUDA_HOME}/bin"
  sanitize_torch_cuda_arch_env

  # 这台机器的系统 CUDA 只带了基础 runtime 头。
  # 其余像 cublas / cusparse / nvrtc 等头文件来自 pixi 环境里的 NVIDIA wheel。
  system_include_dirs=(
    "${CUDA_HOME}/include"
    "${CUDA_HOME}/targets/x86_64-linux/include"
  )
  system_lib_dirs=(
    "${CUDA_HOME}/lib64"
    "${CUDA_HOME}/targets/x86_64-linux/lib"
  )

  mapfile -t nvidia_include_dirs < <(collect_pixi_nvidia_paths include)
  mapfile -t nvidia_lib_dirs < <(collect_pixi_nvidia_paths lib)

  # 这里显式把 Pixi 环境自己的 `libstdc++` 放进构建期搜索路径最前面。
  # 仅靠扩展文件里的 `RPATH` 不够稳,因为 Python 进程可能更早已经装入系统旧版 `libstdc++.so.6`。
  if [[ -n "${CONDA_PREFIX:-}" ]]; then
    pixi_runtime_lib_dirs=(
      "${CONDA_PREFIX}/lib"
      "${CONDA_PREFIX}/lib64"
    )
  fi

  prepend_path_entries CPATH "${system_include_dirs[@]}" "${nvidia_include_dirs[@]}"
  prepend_path_entries CPLUS_INCLUDE_PATH "${system_include_dirs[@]}" "${nvidia_include_dirs[@]}"

  create_nvidia_link_shims "${link_shim_dir}" "${nvidia_lib_dirs[@]}"
  prepend_path_entries LIBRARY_PATH "${link_shim_dir}" "${pixi_runtime_lib_dirs[@]}" "${system_lib_dirs[@]}" "${nvidia_lib_dirs[@]}"
  prepend_path_entries LD_LIBRARY_PATH "${pixi_runtime_lib_dirs[@]}" "${link_shim_dir}" "${system_lib_dirs[@]}" "${nvidia_lib_dirs[@]}"

  rpath_flags="$(build_rpath_flags "${pixi_runtime_lib_dirs[@]}" "${system_lib_dirs[@]}" "${nvidia_lib_dirs[@]}")"
  lib_flags="$(join_colon_paths "${link_shim_dir}" "${pixi_runtime_lib_dirs[@]}" "${system_lib_dirs[@]}" "${nvidia_lib_dirs[@]}")"
  include_flags="$(join_colon_paths "${system_include_dirs[@]}" "${nvidia_include_dirs[@]}")"

  # `CUDAExtension` 仍会把自己的 `-I/usr/local/cuda/include` 和 `-L/usr/local/cuda/lib64` 带进去。
  # 这里额外补环境变量,把 pixi 里拆分出来的 NVIDIA 头文件与共享库也合并进来。
  prepend_linker_flags LDFLAGS "-L${link_shim_dir} ${rpath_flags}"

  printf 'tiny-cuda-nn CUDA build env prepared:\n' >&2
  printf '  CUDA_HOME=%s\n' "${CUDA_HOME}" >&2
  printf '  CUDACXX=%s\n' "${CUDACXX}" >&2
  printf '  include roots=%s\n' "${include_flags}" >&2
  printf '  library roots=%s\n' "${lib_flags}" >&2
}

install_tinycudann_bindings() {
  if [[ ! -f "${target_binding_dir}/setup.py" ]]; then
    printf 'tiny-cuda-nn 安装失败: 缺少 torch bindings 安装入口 %s/setup.py\n' "${target_binding_dir}" >&2
    exit 1
  fi

  prepare_cuda_build_env
  python -m pip install --no-build-isolation "${target_binding_dir}"
}

main() {
  ensure_tinycudann_repo
  ensure_tinycudann_dependencies
  install_tinycudann_bindings
}

main "$@"
