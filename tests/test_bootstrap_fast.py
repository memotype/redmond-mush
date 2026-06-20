from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest

from redmond_server import bootstrap

from tests.bootstrap_test_utils import create_game_dir


class BootstrapFastTest(unittest.TestCase):
    def test_ensure_secret_settings_creates_local_overrides(self) -> None:
        game_dir = create_game_dir()

        secret_settings = bootstrap.ensure_secret_settings(game_dir)

        self.assertTrue(secret_settings.exists())
        content = secret_settings.read_text(encoding="ascii")
        self.assertIn("TELNET_PORTS = [", content)
        self.assertIn("WEBSERVER_PORTS = [(", content)
        self.assertIn("AMP_PORT = ", content)

    def test_runtime_state_reports_stale_pidfile(self) -> None:
        game_dir = create_game_dir()
        pidfile = game_dir / "server" / "server.pid"
        pidfile.write_text("999999\n", encoding="ascii")

        runtime = bootstrap.runtime_state(game_dir)

        self.assertEqual(runtime["stale_pidfile_count"], 1)
        pidfiles = runtime["pidfiles"]
        assert isinstance(pidfiles, dict)
        server_pid = pidfiles["server.pid"]
        assert isinstance(server_pid, dict)
        self.assertTrue(server_pid["exists"])
        self.assertFalse(server_pid["process_running"])

    def test_doctor_reports_missing_database_without_crashing(self) -> None:
        game_dir = create_game_dir()
        bootstrap.ensure_secret_settings(game_dir)

        doctor = bootstrap.diagnostic_state(game_dir)

        self.assertFalse(doctor["db_exists"])
        self.assertTrue(doctor["secret_settings_exists"])
        self.assertIn("database_error", doctor)

    def test_restore_rejects_unexpected_backup_member(self) -> None:
        game_dir = create_game_dir()
        archive_root = Path(tempfile.mkdtemp(prefix="redmond-archive-"))
        archive_path = archive_root / "bad.tar.gz"
        with tarfile.open(archive_path, "w:gz") as archive:
            payload = game_dir / "unexpected.txt"
            payload.write_text("bad\n", encoding="ascii")
            archive.add(payload, arcname="unexpected.txt")

        with self.assertRaises(RuntimeError):
            bootstrap.restore_backup(game_dir, archive_path)

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
        env["REDMOND_FAKE_EVENNIA_LOG"] = str(log_path)
        env["REDMOND_GAME_DIR"] = str(game_dir)

        subprocess.run(
            [
                "bash",
                "-lc",
                (
                    "source product/scripts/common.sh && "
                    "reload_evennia_runtime_if_running"
                ),
            ],
            cwd="/home/isaac/dev/redmond",
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )

        self.assertEqual(log_path.read_text(encoding="ascii").strip(), "reload")

        shutil.rmtree(fake_bin)
