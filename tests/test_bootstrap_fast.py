from __future__ import annotations

import json
from pathlib import Path
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest

from redmond_server import bootstrap
from redmond_server.game.server.conf import _database

from tests.bootstrap_test_utils import (
    cleanup_process,
    create_game_dir,
    load_doctor,
    load_runtime_state,
    PYTHON_BIN,
    PYTHONPATH_DIR,
)


class BootstrapFastTest(unittest.TestCase):
    def test_default_database_settings_use_explicit_sqlite_path(self) -> None:
        game_dir = create_game_dir()

        settings = _database.build_database_settings(game_dir=game_dir)
        metadata = _database.describe_database_config(game_dir=game_dir)

        self.assertEqual(
            settings["default"]["ENGINE"],
            "django.db.backends.sqlite3",
        )
        self.assertEqual(
            settings["default"]["NAME"],
            str(game_dir / "server" / "evennia.db3"),
        )
        self.assertEqual(metadata["engine"], "sqlite")
        self.assertEqual(metadata["source"], "sqlite_default")
        self.assertEqual(
            metadata["sqlite_path"],
            str(game_dir / "server" / "evennia.db3"),
        )

    def test_postgres_url_builds_database_settings(self) -> None:
        settings = _database.build_database_settings(
            raw_url="postgres://user:pass@db.example:15432/redmond",
        )
        metadata = _database.describe_database_config(
            raw_url="postgresql://user@db.example/redmond",
        )

        self.assertEqual(
            settings["default"]["ENGINE"],
            "django.db.backends.postgresql",
        )
        self.assertEqual(settings["default"]["USER"], "user")
        self.assertEqual(settings["default"]["PASSWORD"], "pass")
        self.assertEqual(settings["default"]["HOST"], "db.example")
        self.assertEqual(settings["default"]["PORT"], 15432)
        self.assertEqual(settings["default"]["NAME"], "redmond")
        self.assertEqual(metadata["engine"], "postgresql")
        self.assertEqual(metadata["source"], "env_url")
        self.assertEqual(metadata["host"], "db.example")
        self.assertEqual(metadata["port"], 5432)
        self.assertEqual(metadata["database_name"], "redmond")
        self.assertIsNone(metadata["sqlite_path"])

    def test_invalid_database_url_scheme_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            Exception,
            "postgres:// or postgresql://",
        ):
            _database.parse_database_url("mysql://user@host/redmond")

    def test_database_url_requires_username(self) -> None:
        with self.assertRaisesRegex(Exception, "include a username"):
            _database.parse_database_url("postgres://db.example/redmond")

    def test_database_url_requires_hostname(self) -> None:
        with self.assertRaisesRegex(Exception, "include a hostname"):
            _database.parse_database_url("postgres://user@/redmond")

    def test_database_url_requires_database_name(self) -> None:
        with self.assertRaisesRegex(Exception, "database name"):
            _database.parse_database_url("postgres://user@db.example")

    def test_database_url_rejects_query_parameters(self) -> None:
        with self.assertRaisesRegex(
            Exception,
            "query parameters are not supported",
        ):
            _database.parse_database_url(
                "postgres://user@db.example/redmond?sslmode=require"
            )

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

    def test_runtime_state_command_reports_missing_runtime(self) -> None:
        game_dir = create_game_dir()

        runtime = load_runtime_state(game_dir)

        self.assertEqual(runtime["running_process_count"], 0)
        self.assertEqual(runtime["stale_pidfile_count"], 0)
        self.assertFalse(runtime["runtime_marker_present"])
        pidfiles = runtime["pidfiles"]
        assert isinstance(pidfiles, dict)
        server_pid = pidfiles["server.pid"]
        assert isinstance(server_pid, dict)
        self.assertFalse(server_pid["exists"])

    def test_runtime_state_command_reports_running_pidfile(self) -> None:
        game_dir = create_game_dir()
        proc = subprocess.Popen(["sleep", "300"], text=True)
        self.addCleanup(cleanup_process, proc)
        pidfile = game_dir / "server" / "server.pid"
        pidfile.write_text(f"{proc.pid}\n", encoding="ascii")

        runtime = load_runtime_state(game_dir)

        pidfiles = runtime["pidfiles"]
        assert isinstance(pidfiles, dict)
        server_pid = pidfiles["server.pid"]
        assert isinstance(server_pid, dict)
        self.assertTrue(server_pid["exists"])
        self.assertTrue(server_pid["process_running"])
        self.assertEqual(server_pid["pid"], proc.pid)
        self.assertEqual(runtime["running_process_count"], 1)
        self.assertTrue(runtime["runtime_marker_present"])

    def test_runtime_state_command_reports_flag_presence(self) -> None:
        game_dir = create_game_dir()
        flag_path = game_dir / "server" / "server.restart"
        flag_path.write_text("", encoding="ascii")

        runtime = load_runtime_state(game_dir)

        flags = runtime["restart_or_stop_flags"]
        assert isinstance(flags, dict)
        self.assertTrue(flags["server.restart"])
        self.assertTrue(runtime["runtime_marker_present"])

    def test_doctor_reports_missing_database_without_crashing(self) -> None:
        game_dir = create_game_dir()
        bootstrap.ensure_secret_settings(game_dir)

        doctor = bootstrap.diagnostic_state(game_dir)

        self.assertFalse(doctor["db_exists"])
        self.assertEqual(doctor["database"]["engine"], "sqlite")
        self.assertTrue(doctor["secret_settings_exists"])
        self.assertIn("database_error", doctor)

    def test_doctor_reports_postgres_metadata_without_secrets(self) -> None:
        game_dir = create_game_dir()
        bootstrap.ensure_secret_settings(game_dir)

        doctor = load_doctor(
            game_dir,
            env={
                "REDMOND_DATABASE_URL": (
                    "postgres://user:super-secret@127.0.0.1:1/redmond"
                ),
            },
        )

        self.assertIsNone(doctor["db_exists"])
        self.assertEqual(doctor["database"]["engine"], "postgresql")
        self.assertEqual(doctor["database"]["source"], "env_url")
        self.assertEqual(doctor["database"]["host"], "127.0.0.1")
        self.assertEqual(doctor["database"]["port"], 1)
        self.assertEqual(doctor["database"]["database_name"], "redmond")
        self.assertNotIn("super-secret", doctor["database_error"])

    def test_status_local_reports_doctor_json_without_evennia_cli(self) -> None:
        game_dir = create_game_dir()
        bootstrap.ensure_secret_settings(game_dir)
        env = os.environ.copy()
        env["PYTHONPATH"] = PYTHONPATH_DIR
        env["REDMOND_GAME_DIR"] = str(game_dir)

        result = subprocess.run(
            ["./scripts/status_local.sh"],
            cwd="/home/isaac/dev/redmond/product",
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )

        payload = json.loads(result.stdout)
        self.assertFalse(payload["db_exists"])
        self.assertEqual(payload["database"]["engine"], "sqlite")
        self.assertTrue(payload["secret_settings_exists"])
        self.assertIn("database_error", payload)

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
        env["PYTHONPATH"] = PYTHONPATH_DIR
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
                "source product/scripts/common.sh && runtime_markers_present",
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
