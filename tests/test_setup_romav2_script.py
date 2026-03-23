from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


class SetupRoMaV2ScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.setup_script = self.repo_root / "scripts" / "setup_romav2.sh"
        self.helper_script = self.repo_root / "scripts" / "pixi_task_helpers.sh"

    def test_archive_download_keeps_explicit_proxy_variables(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_repo = Path(tmpdir)
            python_log = self._prepare_fake_repo(temp_repo)

            env = self._build_env(temp_repo, python_log)
            env["HTTP_PROXY"] = "http://127.0.0.1:7897"
            env["HTTPS_PROXY"] = "http://127.0.0.1:7897"
            env["ALL_PROXY"] = "socks5://127.0.0.1:7897"
            env["http_proxy"] = "http://127.0.0.1:7897"
            env["https_proxy"] = "http://127.0.0.1:7897"
            env["all_proxy"] = "socks5://127.0.0.1:7897"

            result = subprocess.run(
                ["bash", "scripts/setup_romav2.sh"],
                cwd=temp_repo,
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)

            curl_log = (temp_repo / "fake_curl.log").read_text(encoding="utf-8")
            self.assertIn("HTTP_PROXY=http://127.0.0.1:7897|HTTPS_PROXY=http://127.0.0.1:7897|ALL_PROXY=socks5://127.0.0.1:7897", curl_log)
            self.assertIn("http_proxy=http://127.0.0.1:7897|https_proxy=http://127.0.0.1:7897|all_proxy=socks5://127.0.0.1:7897", curl_log)
            self.assertIn("codeload.github.com/Parskatt/RoMaV2/tar.gz/refs/heads/main", curl_log)

            python_args = python_log.read_text(encoding="utf-8")
            self.assertIn('-m pip install -e', python_args)
            self.assertIn(str(temp_repo / "third_party" / "RoMaV2[fused-local-corr]"), python_args)
            pyproject_text = (temp_repo / "third_party" / "RoMaV2" / "pyproject.toml").read_text(encoding="utf-8")
            self.assertIn('"dataclasses"', pyproject_text)
            self.assertNotIn('"dataclasses>=0.8"', pyproject_text)

    def _prepare_fake_repo(self, temp_repo: Path) -> Path:
        scripts_dir = temp_repo / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(self.setup_script, scripts_dir / "setup_romav2.sh")
        shutil.copy2(self.helper_script, scripts_dir / "pixi_task_helpers.sh")
        os.chmod(scripts_dir / "setup_romav2.sh", stat.S_IRWXU)
        os.chmod(scripts_dir / "pixi_task_helpers.sh", stat.S_IRWXU)

        (temp_repo / "patches").mkdir(parents=True, exist_ok=True)
        (temp_repo / "patches" / "romav2-dataclasses.patch").write_text(
            textwrap.dedent(
                """\
                diff --git a/pyproject.toml b/pyproject.toml
                --- a/pyproject.toml
                +++ b/pyproject.toml
                @@ -1,4 +1,4 @@
                -name = "romav2"
                +name = "romav2"
                """
            ),
            encoding="utf-8",
        )

        fake_bin = temp_repo / "fake_bin"
        fake_bin.mkdir(parents=True, exist_ok=True)

        self._write_fake_timeout(fake_bin / "timeout")
        self._write_fake_curl(fake_bin / "curl")
        self._write_fake_tar(fake_bin / "tar")
        self._write_fake_python(fake_bin / "python")

        python_log = temp_repo / "fake_python.log"
        python_log.write_text("", encoding="utf-8")
        (temp_repo / "fake_curl.log").write_text("", encoding="utf-8")

        return python_log

    def _build_env(self, temp_repo: Path, python_log: Path) -> dict[str, str]:
        env = os.environ.copy()
        env["PATH"] = f"{temp_repo / 'fake_bin'}:{env['PATH']}"
        env["FAKE_PYTHON_LOG"] = str(python_log)
        env["FAKE_CURL_LOG"] = str(temp_repo / "fake_curl.log")
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

    def _write_fake_curl(self, path: Path) -> None:
        path.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail

                printf 'HTTP_PROXY=%s|HTTPS_PROXY=%s|ALL_PROXY=%s|http_proxy=%s|https_proxy=%s|all_proxy=%s|args=%s\\n' \
                  "${HTTP_PROXY:-<unset>}" \
                  "${HTTPS_PROXY:-<unset>}" \
                  "${ALL_PROXY:-<unset>}" \
                  "${http_proxy:-<unset>}" \
                  "${https_proxy:-<unset>}" \
                  "${all_proxy:-<unset>}" \
                  "$*" >> "${FAKE_CURL_LOG:?}"

                out=""
                while (($#)); do
                  if [[ "$1" == "-o" ]]; then
                    out="$2"
                    shift 2
                    continue
                  fi
                  shift
                done

                printf 'fake archive' > "${out}"
                """
            ),
            encoding="utf-8",
        )
        os.chmod(path, stat.S_IRWXU)

    def _write_fake_tar(self, path: Path) -> None:
        path.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -euo pipefail

                target_dir=""
                while (($#)); do
                  if [[ "$1" == "-C" ]]; then
                    target_dir="$2"
                    shift 2
                    continue
                  fi
                  shift
                done

                mkdir -p "${target_dir}/src/romav2"
                cat > "${target_dir}/pyproject.toml" <<'EOF'
                [project]
                name = "romav2"
                dependencies = [
                    "dataclasses>=0.8",
                ]
                EOF
                : > "${target_dir}/src/romav2/romav2.py"
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


if __name__ == "__main__":
    unittest.main()
