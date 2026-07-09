from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

from tests.bootstrap_test_utils import (
    TEST_PASSWORD_INPUT_ENV,
    WRAPPER_DISABLE_DEFAULT_CONFIG_ENV,
    create_game_dir,
    PYTHON_BIN,
    PYTHONPATH_DIR,
)


class ShellWrappersFastTest(unittest.TestCase):
    def test_mutating_account_script_reloads_running_server(self) -> None:
        game_dir = create_game_dir()
        fake_bin = Path(tempfile.mkdtemp(prefix="redmond-fake-bin-"))
        log_path = fake_bin / "evennia.log"
        evennia_path = fake_bin / "evennia"
        evennia_path.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$*\" >> \"$REDMOND_FAKE_EVENNIA_LOG\"\n",
            encoding="ascii",
        )
        evennia_path.chmod(0o755)

        pidfile = game_dir / "server" / "server.pid"
        pidfile.write_text(f"{os.getpid()}\n", encoding="ascii")

        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}:{env['PATH']}"
        env["PYTHONPATH"] = PYTHONPATH_DIR
        env["REDMOND_FAKE_EVENNIA_LOG"] = str(log_path)
        env["REDMOND_GAME_DIR"] = str(game_dir)
        env["EVENNIA_SUPERUSER_USERNAME"] = "admin"
        env["EVENNIA_SUPERUSER_EMAIL"] = "admin@example.com"
        env[WRAPPER_DISABLE_DEFAULT_CONFIG_ENV] = "1"
        env[TEST_PASSWORD_INPUT_ENV] = "1"

        subprocess.run(
            ["./scripts/init_local.sh"],
            cwd="/home/isaac/dev/redmond/product",
            env=env,
            check=True,
            text=True,
            input="pass123\n",
            capture_output=True,
        )
        subprocess.run(
            [
                "bash",
                "-lc",
                "printf 'alice-pass\\n' | ./scripts/account_create.sh alice",
            ],
            cwd="/home/isaac/dev/redmond/product",
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )

        self.assertEqual(log_path.read_text(encoding="ascii").strip(), "reload")
        shutil.rmtree(fake_bin)

    def test_common_shell_runtime_inspection_uses_bootstrap_command(
        self,
    ) -> None:
        game_dir = create_game_dir()
        fake_bin = Path(tempfile.mkdtemp(prefix="redmond-fake-bin-"))
        log_path = fake_bin / "python.log"
        python_path = fake_bin / "python"
        python_path.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$*\" >> \"$REDMOND_FAKE_PYTHON_LOG\"\n"
            f'exec "{PYTHON_BIN}" "$@"\n',
            encoding="ascii",
        )
        python_path.chmod(0o755)

        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}:{env['PATH']}"
        env["PYTHONPATH"] = PYTHONPATH_DIR
        env["REDMOND_FAKE_PYTHON_LOG"] = str(log_path)
        env["REDMOND_GAME_DIR"] = str(game_dir)

        subprocess.run(
            [
                "bash",
                "-lc",
                (
                    "source product/scripts/common.sh && "
                    "redmond_init && runtime_markers_present"
                ),
            ],
            cwd="/home/isaac/dev/redmond",
            env=env,
            check=False,
            text=True,
            capture_output=True,
        )

        log_lines = log_path.read_text(encoding="ascii").splitlines()
        self.assertIn(
            "-m redmond_server.bootstrap runtime-state --game-dir "
            f"{game_dir}",
            log_lines,
        )
