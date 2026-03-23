from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


class InstallGsplatScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.install_script = self.repo_root / "scripts" / "install_gsplat.sh"
        self.helper_script = self.repo_root / "scripts" / "pixi_task_helpers.sh"

    def test_repair_broken_glm_submodule_before_pip_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_repo = Path(tmpdir)
            python_log = self._prepare_fake_repo(temp_repo)

            env = self._build_env(temp_repo, python_log)
            env["FAKE_GIT_BROKEN_SUBMODULE"] = "1"
            env["FAKE_GIT_CREATE_GLM_HEADER"] = "1"

            result = subprocess.run(
                ["bash", "scripts/install_gsplat.sh"],
                cwd=temp_repo,
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Detected broken glm submodule checkout", result.stdout)
            self.assertIn("glm headers restored successfully", result.stdout)
            self.assertIn("gsplat CUDA build env prepared", result.stderr)
            self.assertIn("CUDACXX=", result.stderr)

            glm_header = (
                temp_repo
                / "third_party"
                / "gsplat"
                / "gsplat"
                / "cuda"
                / "csrc"
                / "third_party"
                / "glm"
                / "glm"
                / "gtc"
                / "type_ptr.hpp"
            )
            self.assertTrue(glm_header.is_file())

            install_args = python_log.read_text(encoding="utf-8")
            self.assertIn("-m pip install --no-build-isolation", install_args)
            self.assertIn(str(temp_repo / "third_party" / "gsplat"), install_args)

    def test_fail_early_when_glm_header_still_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_repo = Path(tmpdir)
            python_log = self._prepare_fake_repo(temp_repo)

            env = self._build_env(temp_repo, python_log)
            env["FAKE_GIT_BROKEN_SUBMODULE"] = "1"
            env["FAKE_GIT_CREATE_GLM_HEADER"] = "0"

            result = subprocess.run(
                ["bash", "scripts/install_gsplat.sh"],
                cwd=temp_repo,
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("gsplat 安装失败: 缺少必需头文件", result.stderr)
            self.assertIn("当前机器也没有可复用的本地 glm 头文件源", result.stderr)
            self.assertEqual(python_log.read_text(encoding="utf-8"), "")

    def test_fallback_to_local_glm_source_when_submodule_update_times_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_repo = Path(tmpdir)
            python_log = self._prepare_fake_repo(temp_repo)

            local_glm_root = temp_repo / "local_glm_bundle"
            (local_glm_root / "glm" / "gtc").mkdir(parents=True, exist_ok=True)
            (local_glm_root / "glm" / "gtc" / "type_ptr.hpp").write_text("// fake glm header\n", encoding="utf-8")

            env = self._build_env(temp_repo, python_log)
            env["FAKE_GIT_BROKEN_SUBMODULE"] = "1"
            env["FAKE_GIT_UPDATE_EXIT"] = "124"
            env["GSPLAT_GLM_LOCAL_DIR"] = str(local_glm_root)

            result = subprocess.run(
                ["bash", "scripts/install_gsplat.sh"],
                cwd=temp_repo,
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"Using local glm headers from {local_glm_root}", result.stdout)
            self.assertIn("glm headers restored successfully", result.stdout)
            self.assertIn("-m pip install --no-build-isolation", python_log.read_text(encoding="utf-8"))

    def _prepare_fake_repo(self, temp_repo: Path) -> Path:
        scripts_dir = temp_repo / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(self.install_script, scripts_dir / "install_gsplat.sh")
        shutil.copy2(self.helper_script, scripts_dir / "pixi_task_helpers.sh")
        os.chmod(scripts_dir / "install_gsplat.sh", stat.S_IRWXU)
        os.chmod(scripts_dir / "pixi_task_helpers.sh", stat.S_IRWXU)

        # 伪造一个已经存在的 gsplat checkout,这样脚本会走“复用本地仓库”的路径。
        (temp_repo / "third_party" / "gsplat" / ".git").mkdir(parents=True, exist_ok=True)

        fake_bin = temp_repo / "fake_bin"
        fake_bin.mkdir(parents=True, exist_ok=True)
        fake_conda_prefix = temp_repo / "fake_conda_prefix"
        (fake_conda_prefix / "bin").mkdir(parents=True, exist_ok=True)

        self._write_fake_timeout(fake_bin / "timeout")
        self._write_fake_git(fake_bin / "git")
        self._write_fake_find(fake_bin / "find")
        self._write_fake_nvcc(fake_conda_prefix / "bin" / "nvcc")

        python_log = temp_repo / "fake_python.log"
        python_log.write_text("", encoding="utf-8")
        self._write_fake_python(fake_bin / "python")

        return python_log

    def _build_env(self, temp_repo: Path, python_log: Path) -> dict[str, str]:
        env = os.environ.copy()
        env["PATH"] = f"{temp_repo / 'fake_bin'}:{env['PATH']}"
        env["FAKE_PYTHON_LOG"] = str(python_log)
        env["CONDA_PREFIX"] = str(temp_repo / "fake_conda_prefix")
        env.pop("HTTP_PROXY", None)
        env.pop("HTTPS_PROXY", None)
        env.pop("ALL_PROXY", None)
        env.pop("http_proxy", None)
        env.pop("https_proxy", None)
        env.pop("all_proxy", None)
        return env

    def _write_fake_timeout(self, path: Path) -> None:
        path.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                shift
                exec "$@"
                """
            ),
            encoding="utf-8",
        )
        os.chmod(path, stat.S_IRWXU)

    def _write_fake_git(self, path: Path) -> None:
        path.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail

                repo="$PWD"
                if [[ "${1:-}" == "-C" ]]; then
                  repo="$2"
                  shift 2
                fi

                if [[ "${1:-}" == "cat-file" ]]; then
                  exit 0
                fi

                if [[ "${1:-}" == "checkout" ]]; then
                  exit 0
                fi

                if [[ "${1:-}" == "fetch" ]]; then
                  exit 0
                fi

                if [[ "${1:-}" == "clone" ]]; then
                  mkdir -p "$3/.git"
                  exit 0
                fi

                if [[ "${1:-}" == "rev-parse" ]]; then
                  if [[ "${FAKE_GIT_BROKEN_SUBMODULE:-0}" == "1" ]]; then
                    echo "fatal: detached HEAD missing" >&2
                    exit 128
                  fi
                  echo "33b4a621a697a305bc3a7610d290677b96beb181"
                  exit 0
                fi

                if [[ "${1:-}" == "submodule" ]]; then
                  shift
                  case "${1:-}" in
                    deinit|sync)
                      exit 0
                      ;;
                    update)
                      if [[ -n "${FAKE_GIT_UPDATE_EXIT:-}" ]]; then
                        exit "${FAKE_GIT_UPDATE_EXIT}"
                      fi
                      submodule_path="${@: -1}"
                      if [[ "${FAKE_GIT_CREATE_GLM_HEADER:-1}" == "1" ]]; then
                        mkdir -p "$repo/$submodule_path/glm/gtc"
                        : > "$repo/$submodule_path/glm/gtc/type_ptr.hpp"
                      fi
                      exit 0
                      ;;
                  esac
                fi

                echo "unexpected fake git invocation: repo=$repo args=$*" >&2
                exit 1
                """
            ),
            encoding="utf-8",
        )
        os.chmod(path, stat.S_IRWXU)

    def _write_fake_python(self, path: Path) -> None:
        path.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail
                printf '%s\\n' "$*" >> "${FAKE_PYTHON_LOG:?}"
                exit 0
                """
            ),
            encoding="utf-8",
        )
        os.chmod(path, stat.S_IRWXU)

    def _write_fake_find(self, path: Path) -> None:
        path.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                exit 0
                """
            ),
            encoding="utf-8",
        )
        os.chmod(path, stat.S_IRWXU)

    def _write_fake_nvcc(self, path: Path) -> None:
        path.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                exit 0
                """
            ),
            encoding="utf-8",
        )
        os.chmod(path, stat.S_IRWXU)


if __name__ == "__main__":
    unittest.main()
