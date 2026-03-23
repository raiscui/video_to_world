#!/usr/bin/env bash

set -euo pipefail

# ==============================
# RoMaV2 安装脚本
# ==============================

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"

source "${repo_root}/scripts/pixi_task_helpers.sh"
clear_loopback_proxy_vars

# 当前机器上,`git clone` 下载 RoMaV2 不稳定。
# 用户显式提供的 `127.0.0.1:7897` 代理组合已经验证可用于 `codeload` archive。
# 因此这里保留调用方传入的代理环境,改走更稳定、也更容易做断点续传的 codeload archive。
export GIT_TERMINAL_PROMPT=0

target_repo="${repo_root}/third_party/RoMaV2"
archive_cache_dir="${ROMAV2_ARCHIVE_CACHE_DIR:-/tmp/video_to_world-romav2-archives}"
archive_path="${archive_cache_dir}/RoMaV2-main.tar.gz"
codeload_url="https://codeload.github.com/Parskatt/RoMaV2/tar.gz/refs/heads/main"

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
    printf 'RoMaV2 安装失败: %s (exit=%s, timeout=%ss)\n' "${description}" "${exit_code}" "${timeout_seconds}" >&2
    return "${exit_code}"
  fi
}

archive_cache_has_gzip_magic() {
  local candidate="$1"
  local magic=""

  if [[ ! -f "${candidate}" ]]; then
    return 1
  fi

  magic="$(od -An -t x1 -N 2 "${candidate}" 2>/dev/null | tr -d ' \n')"
  [[ "${magic}" == "1f8b" ]]
}

download_romav2_archive_without_proxy() {
  if [[ -f "${target_repo}/pyproject.toml" && -f "${target_repo}/src/romav2/romav2.py" ]]; then
    echo "RoMaV2 source already available locally"
    return 0
  fi

  rm -rf "${target_repo}"
  mkdir -p "${target_repo}" "${archive_cache_dir}" "${repo_root}/third_party"

  if [[ -f "${archive_path}" ]] && ! archive_cache_has_gzip_magic "${archive_path}"; then
    echo "Removing invalid RoMaV2 archive cache: ${archive_path}"
    rm -f "${archive_path}"
  fi

  # archive 下载沿用调用方环境。
  # 当前用户已经显式给出可工作的代理配置,这里不要再强制 `env -u` 把它清掉。
  run_timed_command \
    420 \
    "download RoMaV2 源码归档" \
    curl --http1.1 --continue-at - --retry 5 --retry-delay 2 --retry-all-errors -L --fail -o "${archive_path}" "${codeload_url}"

  run_timed_command \
    60 \
    "extract RoMaV2 源码归档" \
    tar -xzf "${archive_path}" -C "${target_repo}" --strip-components=1

  if [[ ! -f "${target_repo}/pyproject.toml" || ! -f "${target_repo}/src/romav2/romav2.py" ]]; then
    printf 'RoMaV2 安装失败: 归档解压后缺少关键源码文件\n' >&2
    exit 1
  fi
}

normalize_dataclasses_requirement() {
  local pyproject_path="${target_repo}/pyproject.toml"

  if [[ ! -f "${pyproject_path}" ]]; then
    printf 'RoMaV2 安装失败: 缺少 pyproject.toml\n' >&2
    exit 1
  fi

  if grep -Fq '"dataclasses>=0.8"' "${pyproject_path}"; then
    sed -i 's/"dataclasses>=0\.8"/"dataclasses"/g' "${pyproject_path}"
    echo "Normalized RoMaV2 dataclasses dependency for Python 3.10+"
  else
    echo "RoMaV2 dataclasses dependency already normalized"
  fi
}

download_romav2_archive_without_proxy
normalize_dataclasses_requirement

python -m pip install -e "${target_repo}[fused-local-corr]"
