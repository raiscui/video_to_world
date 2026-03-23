from __future__ import annotations

import re
import unittest
from pathlib import Path


class PixiManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.manifest_path = self.repo_root / "pixi.toml"
        self.manifest_text = self.manifest_path.read_text(encoding="utf-8")
        self.envrc_path = self.repo_root / ".envrc"
        self.envrc_text = self.envrc_path.read_text(encoding="utf-8")
        self.depth_script_path = self.repo_root / "scripts" / "setup_depth_anything_3.sh"
        self.depth_script_text = self.depth_script_path.read_text(encoding="utf-8")
        self.romav2_script_path = self.repo_root / "scripts" / "setup_romav2.sh"
        self.romav2_script_text = self.romav2_script_path.read_text(encoding="utf-8")
        self.gsplat_script_path = self.repo_root / "scripts" / "install_gsplat.sh"
        self.gsplat_script_text = self.gsplat_script_path.read_text(encoding="utf-8")
        self.tinycudann_script_path = self.repo_root / "scripts" / "install_tinycudann.sh"
        self.tinycudann_script_text = self.tinycudann_script_path.read_text(encoding="utf-8")
        self.torch_kdtree_script_path = self.repo_root / "scripts" / "install_torch_kdtree.sh"
        self.torch_kdtree_script_text = self.torch_kdtree_script_path.read_text(encoding="utf-8")
        self.helper_script_path = self.repo_root / "scripts" / "pixi_task_helpers.sh"
        self.helper_script_text = self.helper_script_path.read_text(encoding="utf-8")

    def test_github_tasks_source_proxy_helper(self) -> None:
        self.assertIn("source \"${repo_root}/scripts/pixi_task_helpers.sh\"", self.gsplat_script_text)
        self.assertIn("clear_loopback_proxy_vars", self.gsplat_script_text)
        self.assertIn("source \"${repo_root}/scripts/pixi_task_helpers.sh\"", self.depth_script_text)
        self.assertIn("clear_loopback_proxy_vars", self.depth_script_text)
        self.assertIn("source \"${repo_root}/scripts/pixi_task_helpers.sh\"", self.romav2_script_text)
        self.assertIn("clear_loopback_proxy_vars", self.romav2_script_text)
        self.assertIn("source \"${repo_root}/scripts/pixi_task_helpers.sh\"", self.tinycudann_script_text)
        self.assertIn("clear_loopback_proxy_vars", self.tinycudann_script_text)
        self.assertIn("source \"${repo_root}/scripts/pixi_task_helpers.sh\"", self.torch_kdtree_script_text)
        self.assertIn("clear_loopback_proxy_vars", self.torch_kdtree_script_text)
        self.assertIn('keep_loopback_proxy="${PIXI_KEEP_LOOPBACK_PROXY:-0}"', self.helper_script_text)
        self.assertIn("loopback_proxy_is_alive()", self.helper_script_text)
        self.assertIn("Keeping reachable loopback proxy vars for this Pixi task", self.helper_script_text)
        self.assertIn("detect_cuda_home()", self.helper_script_text)
        self.assertIn("cuda_home_nvcc_path()", self.helper_script_text)
        self.assertIn('if cuda_home_has_nvcc "${CONDA_PREFIX:-}"', self.helper_script_text)
        self.assertIn("cuda_home_has_nvcc()", self.helper_script_text)
        self.assertIn("sanitize_torch_cuda_arch_env()", self.helper_script_text)
        self.assertIn("Using sanitized TORCH_CUDA_ARCH_LIST=", self.helper_script_text)
        self.assertIn("prepend_path_entries()", self.helper_script_text)

    def test_install_gsplat_uses_script_with_glm_repair(self) -> None:
        task_block = self._extract_task_block("install-gsplat")
        self.assertEqual(task_block.strip(), 'install-gsplat = "bash scripts/install_gsplat.sh"')
        self.assertTrue(self.gsplat_script_path.is_file())
        self.assertIn('target_commit="937e29912570c372bed6747a5c9bf85fed877bae"', self.gsplat_script_text)
        self.assertIn('glm_local_dir="${GSPLAT_GLM_LOCAL_DIR:-}"', self.gsplat_script_text)
        self.assertIn('glm_submodule_path="gsplat/cuda/csrc/third_party/glm"', self.gsplat_script_text)
        self.assertIn('git_repo_has_commit "${target_repo}" "${target_commit}"', self.gsplat_script_text)
        self.assertIn('git clone https://github.com/nerfstudio-project/gsplat.git "${target_repo}"', self.gsplat_script_text)
        self.assertIn('git -C "${target_repo}" submodule deinit -f -- "${glm_submodule_path}"', self.gsplat_script_text)
        self.assertIn('rm -rf "${target_repo}/${glm_submodule_path}" "${module_git_dir}"', self.gsplat_script_text)
        self.assertIn('find_local_glm_source()', self.gsplat_script_text)
        self.assertIn('populate_glm_from_local_source "${local_glm_root}"', self.gsplat_script_text)
        self.assertIn(
            'git -C "${target_repo}" submodule update --init --recursive -- "${glm_submodule_path}"',
            self.gsplat_script_text,
        )
        self.assertIn("prepare_cuda_build_env()", self.gsplat_script_text)
        self.assertIn('detected_cuda_home="$(detect_cuda_home || true)"', self.gsplat_script_text)
        self.assertIn('detected_nvcc_path="$(cuda_home_nvcc_path "${detected_cuda_home}" || true)"', self.gsplat_script_text)
        self.assertIn('export CUDA_HOME="${detected_cuda_home}"', self.gsplat_script_text)
        self.assertIn('export CUDACXX="${detected_nvcc_path}"', self.gsplat_script_text)
        self.assertIn('prepend_path_entries PATH "$(dirname "${detected_nvcc_path}")" "${CUDA_HOME}/bin"', self.gsplat_script_text)
        self.assertIn("sanitize_torch_cuda_arch_env", self.gsplat_script_text)
        self.assertIn('python -m pip install --no-build-isolation "${target_repo}"', self.gsplat_script_text)

    def test_setup_depth_anything_3_prefers_existing_commit_or_local_mirror(self) -> None:
        task_block = self._extract_task_block("setup-depth-anything-3")
        self.assertEqual(task_block.strip(), 'setup-depth-anything-3 = "bash scripts/setup_depth_anything_3.sh"')
        self.assertTrue(self.depth_script_path.is_file())
        self.assertIn('target_commit="2c21ea849ceec7b469a3e62ea0c0e270afc3281a"', self.depth_script_text)
        self.assertIn('local_repo="${DEPTH_ANYTHING_3_LOCAL_REPO:-/workspace/depth-anything-3}"', self.depth_script_text)
        self.assertIn('git_repo_has_commit "${target_repo}" "${target_commit}"', self.depth_script_text)
        self.assertIn('git_repo_has_commit "${local_repo}" "${target_commit}"', self.depth_script_text)
        self.assertIn('git clone "${local_repo}" "${target_repo}"', self.depth_script_text)

    def test_setup_romav2_uses_direct_clone_script(self) -> None:
        task_block = self._extract_task_block("setup-romav2")
        self.assertEqual(task_block.strip(), 'setup-romav2 = "bash scripts/setup_romav2.sh"')
        self.assertTrue(self.romav2_script_path.is_file())
        self.assertIn('target_repo="${repo_root}/third_party/RoMaV2"', self.romav2_script_text)
        self.assertIn('archive_cache_dir="${ROMAV2_ARCHIVE_CACHE_DIR:-/tmp/video_to_world-romav2-archives}"', self.romav2_script_text)
        self.assertIn('archive_path="${archive_cache_dir}/RoMaV2-main.tar.gz"', self.romav2_script_text)
        self.assertIn('codeload_url="https://codeload.github.com/Parskatt/RoMaV2/tar.gz/refs/heads/main"', self.romav2_script_text)
        self.assertIn("archive_cache_has_gzip_magic()", self.romav2_script_text)
        self.assertIn('echo "Removing invalid RoMaV2 archive cache: ${archive_path}"', self.romav2_script_text)
        self.assertIn("normalize_dataclasses_requirement()", self.romav2_script_text)
        self.assertIn("""grep -Fq '"dataclasses>=0.8"' "${pyproject_path}" """.strip(), self.romav2_script_text)
        self.assertIn("""sed -i 's/"dataclasses>=0\\.8"/"dataclasses"/g' "${pyproject_path}" """.strip(), self.romav2_script_text)
        self.assertIn('run_timed_command \\', self.romav2_script_text)
        self.assertIn('"download RoMaV2 源码归档"', self.romav2_script_text)
        self.assertIn(
            'curl --http1.1 --continue-at - --retry 5 --retry-delay 2 --retry-all-errors -L --fail -o "${archive_path}" "${codeload_url}"',
            self.romav2_script_text,
        )
        self.assertIn('tar -xzf "${archive_path}" -C "${target_repo}" --strip-components=1', self.romav2_script_text)
        self.assertIn('python -m pip install -e "${target_repo}[fused-local-corr]"', self.romav2_script_text)

    def test_install_tinycudann_uses_local_clone_script(self) -> None:
        task_block = self._extract_task_block("install-tinycudann")
        self.assertEqual(
            task_block.splitlines()[0].strip(),
            'install-tinycudann = { cmd = "bash scripts/install_tinycudann.sh", depends-on = ["pin-build-setuptools"] }',
        )
        self.assertTrue(self.tinycudann_script_path.is_file())
        self.assertIn('target_repo="${TINYCUDANN_LOCAL_REPO:-/tmp/video_to_world-tiny-cuda-nn}"', self.tinycudann_script_text)
        self.assertIn('archive_cache_dir="${TINYCUDANN_ARCHIVE_CACHE_DIR:-/tmp/video_to_world-tinycudann-archives}"', self.tinycudann_script_text)
        self.assertIn('git clone https://github.com/NVlabs/tiny-cuda-nn/ "${target_repo}"', self.tinycudann_script_text)
        self.assertIn('github_codeload_url()', self.tinycudann_script_text)
        self.assertIn('extract_submodule_archive()', self.tinycudann_script_text)
        self.assertIn('populate_submodule_from_tarball "dependencies/cutlass" "include/cutlass/cutlass.h"', self.tinycudann_script_text)
        self.assertIn('populate_submodule_from_tarball "dependencies/fmt" "include/fmt/core.h"', self.tinycudann_script_text)
        self.assertIn('archive_path="${archive_cache_dir}/${archive_name}"', self.tinycudann_script_text)
        self.assertIn('collect_pixi_nvidia_paths()', self.tinycudann_script_text)
        self.assertIn('create_nvidia_link_shims()', self.tinycudann_script_text)
        self.assertIn('link_shim_dir="/tmp/video_to_world-tinycudann-link-shims"', self.tinycudann_script_text)
        self.assertIn('mapfile -t nvidia_include_dirs < <(collect_pixi_nvidia_paths include)', self.tinycudann_script_text)
        self.assertIn('mapfile -t nvidia_lib_dirs < <(collect_pixi_nvidia_paths lib)', self.tinycudann_script_text)
        self.assertIn('local pixi_runtime_lib_dirs=()', self.tinycudann_script_text)
        self.assertIn('if [[ -n "${CONDA_PREFIX:-}" ]]; then', self.tinycudann_script_text)
        self.assertIn('prepend_path_entries CPATH "${system_include_dirs[@]}" "${nvidia_include_dirs[@]}"', self.tinycudann_script_text)
        self.assertIn(
            'prepend_path_entries LIBRARY_PATH "${link_shim_dir}" "${pixi_runtime_lib_dirs[@]}" "${system_lib_dirs[@]}" "${nvidia_lib_dirs[@]}"',
            self.tinycudann_script_text,
        )
        self.assertIn(
            'prepend_path_entries LD_LIBRARY_PATH "${pixi_runtime_lib_dirs[@]}" "${link_shim_dir}" "${system_lib_dirs[@]}" "${nvidia_lib_dirs[@]}"',
            self.tinycudann_script_text,
        )
        self.assertIn(
            'rpath_flags="$(build_rpath_flags "${pixi_runtime_lib_dirs[@]}" "${system_lib_dirs[@]}" "${nvidia_lib_dirs[@]}")"',
            self.tinycudann_script_text,
        )
        self.assertIn('prepend_linker_flags LDFLAGS "-L${link_shim_dir} ${rpath_flags}"', self.tinycudann_script_text)
        self.assertIn('detected_nvcc_path="$(cuda_home_nvcc_path "${detected_cuda_home}" || true)"', self.tinycudann_script_text)
        self.assertIn('export CUDACXX="${detected_nvcc_path}"', self.tinycudann_script_text)
        self.assertIn("sanitize_torch_cuda_arch_env", self.tinycudann_script_text)
        self.assertIn(
            'curl --http1.1 --continue-at - --retry 5 --retry-delay 2 --retry-all-errors -L --fail -o "${archive_path}" "${codeload_url}"',
            self.tinycudann_script_text,
        )
        self.assertIn('prepare_cuda_build_env', self.tinycudann_script_text)
        self.assertIn('python -m pip install --no-build-isolation "${target_binding_dir}"', self.tinycudann_script_text)

    def test_install_torch_kdtree_uses_cuda_detect_script(self) -> None:
        task_block = self._extract_task_block("install-torch-kdtree")
        self.assertEqual(task_block.strip(), 'install-torch-kdtree = "bash scripts/install_torch_kdtree.sh"')
        self.assertTrue(self.torch_kdtree_script_path.is_file())
        self.assertIn('target_repo="${repo_root}/third_party/torch_kdtree"', self.torch_kdtree_script_text)
        self.assertIn("prepare_cuda_build_env()", self.torch_kdtree_script_text)
        self.assertIn('detected_cuda_home="$(detect_cuda_home)"', self.torch_kdtree_script_text)
        self.assertIn('detected_nvcc_path="$(cuda_home_nvcc_path "${detected_cuda_home}" || true)"', self.torch_kdtree_script_text)
        self.assertIn('export CUDA_HOME="${detected_cuda_home}"', self.torch_kdtree_script_text)
        self.assertIn('export CUDACXX="${detected_nvcc_path}"', self.torch_kdtree_script_text)
        self.assertIn('prepend_path_entries PATH "$(dirname "${detected_nvcc_path}")" "${CUDA_HOME}/bin"', self.torch_kdtree_script_text)
        self.assertIn("sanitize_torch_cuda_arch_env", self.torch_kdtree_script_text)
        self.assertIn(
            'run_timed_command \\\n      180 \\\n      "clone torch_kdtree 主仓库" \\',
            self.torch_kdtree_script_text,
        )
        self.assertIn('python -m pip install --no-build-isolation "${target_repo}"', self.torch_kdtree_script_text)

    def test_envrc_documents_depth_anything_local_repo(self) -> None:
        self.assertTrue(self.envrc_path.is_file())
        self.assertIn("DEPTH_ANYTHING_3_LOCAL_REPO", self.envrc_text)
        self.assertIn("/workspace/depth-anything-3", self.envrc_text)
        self.assertIn("GSPLAT_GLM_LOCAL_DIR", self.envrc_text)
        self.assertIn("TINYCUDANN_LOCAL_REPO", self.envrc_text)
        self.assertIn("/tmp/video_to_world-tiny-cuda-nn", self.envrc_text)
        self.assertIn("TINYCUDANN_ARCHIVE_CACHE_DIR", self.envrc_text)
        self.assertIn("/tmp/video_to_world-tinycudann-archives", self.envrc_text)
        self.assertIn("ROMAV2_ARCHIVE_CACHE_DIR", self.envrc_text)
        self.assertIn("/tmp/video_to_world-romav2-archives", self.envrc_text)
        self.assertIn("CUDA_HOME", self.envrc_text)
        self.assertIn("/usr/local/cuda", self.envrc_text)
        self.assertIn("PIXI_KEEP_LOOPBACK_PROXY", self.envrc_text)

    def test_manifest_includes_socksio_for_socks_proxy_downloads(self) -> None:
        self.assertIn("[activation.env]", self.manifest_text)
        self.assertIn('LD_LIBRARY_PATH = "$CONDA_PREFIX/lib:$CONDA_PREFIX/lib64:$LD_LIBRARY_PATH"', self.manifest_text)
        self.assertIn('socksio = "*"', self.manifest_text)
        self.assertIn('cuda-nvcc = "12.8.*"', self.manifest_text)
        self.assertIn("The base `pixi` environment now includes `socksio`", self.repo_root.joinpath("README.md").read_text(encoding="utf-8"))

    def _extract_task_block(self, task_name: str) -> str:
        lines = self.manifest_text.splitlines()
        start_index = None
        in_triple_quote = False
        block_lines: list[str] = []

        for index, line in enumerate(lines):
            if start_index is None:
                if re.match(rf"^{re.escape(task_name)}\s*=", line):
                    start_index = index
                    block_lines.append(line)
                    in_triple_quote = line.count('"""') % 2 == 1
                continue

            if not in_triple_quote and (re.match(r"^[A-Za-z0-9_-]+\s*=", line) or re.match(r"^\[[A-Za-z0-9_.-]+\]", line)):
                break

            if line.count('"""') % 2 == 1:
                in_triple_quote = not in_triple_quote

            block_lines.append(line)

        self.assertIsNotNone(start_index, f"未找到任务定义: {task_name}")
        return "\n".join(block_lines)


if __name__ == "__main__":
    unittest.main()
