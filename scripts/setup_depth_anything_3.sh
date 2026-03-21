#!/usr/bin/env bash

set -euo pipefail

# ==============================
# DepthAnything-3 安装脚本
# ==============================

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"

# 这里复用通用 helper。
# 一个负责清掉失效的 loopback 代理,另一个负责判断 commit 是否本地可用。
source "${repo_root}/scripts/pixi_task_helpers.sh"

clear_loopback_proxy_vars

target_commit="2c21ea849ceec7b469a3e62ea0c0e270afc3281a"
local_repo="${DEPTH_ANYTHING_3_LOCAL_REPO:-/workspace/depth-anything-3}"
target_repo="${repo_root}/third_party/depth-anything-3"
patch_path="${repo_root}/patches/da3-export-trajectory.patch"

mkdir -p "${repo_root}/third_party"

# 第一优先级: 当前 third_party 仓库里已经有目标 commit,就直接使用。
if git_repo_has_commit "${target_repo}" "${target_commit}"; then
  echo "DepthAnything-3 target commit already available locally"

# 第二优先级: 用户提供的本地镜像里已有目标 commit,就从本地镜像同步。
elif git_repo_has_commit "${local_repo}" "${target_commit}"; then
  echo "Using local DepthAnything-3 mirror: ${local_repo}"
  if [[ ! -d "${target_repo}/.git" ]]; then
    git clone "${local_repo}" "${target_repo}"
  else
    git -C "${target_repo}" fetch --tags --force "${local_repo}"
  fi

# 第三优先级: 只有本地两边都不满足时,才回退到 GitHub。
else
  if [[ ! -d "${target_repo}/.git" ]]; then
    git clone https://github.com/ByteDance-Seed/depth-anything-3 "${target_repo}"
  fi

  if ! git_repo_has_commit "${target_repo}" "${target_commit}"; then
    git -C "${target_repo}" fetch --tags --force
  fi
fi

git -C "${target_repo}" checkout "${target_commit}"

if git -C "${target_repo}" apply --reverse --check "${patch_path}" >/dev/null 2>&1; then
  echo "DepthAnything-3 patch already applied"
else
  git -C "${target_repo}" apply "${patch_path}"
fi

python -m pip install -e "${target_repo}"
