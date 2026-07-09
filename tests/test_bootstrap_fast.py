from __future__ import annotations

import json
import io
from pathlib import Path
import os
import stat
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

from redmond_server import bootstrap
from redmond_server.bootstrap import _backup
from redmond_server.bootstrap import _backup_contract
from redmond_server.bootstrap._passwords import (
    TEST_PASSWORD_INPUT_ENV,
    read_password,
)
from redmond_server.game.server.conf import _backup as backup_conf
from redmond_server.game.server.conf import _database

from tests.bootstrap_test_utils import (
    TEST_PASSWORD_INPUT_ENV as HELPER_TEST_PASSWORD_INPUT_ENV,
    WRAPPER_DISABLE_DEFAULT_CONFIG_ENV,
    cleanup_process,
    create_game_dir,
    load_doctor,
    load_backup_status,
    load_runtime_state,
    PYTHON_BIN,
    PYTHONPATH_DIR,
)


class BootstrapFastTest(unittest.TestCase):
    def assert_owner_only_mode(self, path: Path) -> None:
        self.assertEqual(
            stat.S_IMODE(path.stat().st_mode),
            stat.S_IRUSR | stat.S_IWUSR,
        )

    def test_password_reader_uses_stdin_in_explicit_test_mode(self) -> None:
        stdin = io.StringIO("pass123\n")
        with mock.patch.dict(
            os.environ,
            {TEST_PASSWORD_INPUT_ENV: "1"},
            clear=False,
        ):
            self.assertEqual(
                read_password(
                    "Password: ",
                    confirm=True,
                    stdin=stdin,
                    is_tty=False,
                ),
                "pass123",
            )

    def test_password_reader_requires_tty_outside_test_mode(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(TEST_PASSWORD_INPUT_ENV, None)
            with self.assertRaisesRegex(
                RuntimeError,
                "interactive terminal",
            ):
                read_password(
                    "Password: ",
                    confirm=False,
                    stdin=io.StringIO("pass123\n"),
                    is_tty=False,
                )

    def test_password_reader_rejects_missing_stdin_in_test_mode(self) -> None:
        with mock.patch.dict(
            os.environ,
            {TEST_PASSWORD_INPUT_ENV: "1"},
            clear=False,
        ):
            with self.assertRaisesRegex(RuntimeError, "stdin"):
                read_password(
                    "Password: ",
                    confirm=False,
                    stdin=io.StringIO(""),
                    is_tty=False,
                )

    def test_password_reader_requires_matching_confirmation(self) -> None:
        prompts = iter(["pass123", "pass124"])

        def fake_getpass(_prompt: str) -> str:
            return next(prompts)

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(TEST_PASSWORD_INPUT_ENV, None)
            with self.assertRaisesRegex(RuntimeError, "did not match"):
                read_password(
                    "Password: ",
                    confirm=True,
                    is_tty=True,
                    getpass_func=fake_getpass,
                )

    def test_cli_rejects_non_tty_stdin_without_test_mode(self) -> None:
        game_dir = create_game_dir()
        env = os.environ.copy()
        env["PYTHONPATH"] = PYTHONPATH_DIR
        env["REDMOND_GAME_DIR"] = str(game_dir)
        env["EVENNIA_SUPERUSER_USERNAME"] = "admin"
        env["EVENNIA_SUPERUSER_EMAIL"] = "admin@example.com"
        env[WRAPPER_DISABLE_DEFAULT_CONFIG_ENV] = "1"
        env[HELPER_TEST_PASSWORD_INPUT_ENV] = "1"

        subprocess.run(
            ["./scripts/init_local.sh"],
            cwd="/home/isaac/dev/redmond/product",
            env=env,
            check=True,
            text=True,
            input="pass123\n",
            capture_output=True,
        )

        env.pop(HELPER_TEST_PASSWORD_INPUT_ENV, None)
        result = subprocess.run(
            [
                PYTHON_BIN,
                "-m",
                "redmond_server.bootstrap",
                "account-verify-password",
                "--username",
                "admin",
                "--game-dir",
                str(game_dir),
            ],
            cwd="/home/isaac/dev/redmond/product",
            env=env,
            check=False,
            text=True,
            input="pass123\n",
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("interactive terminal", result.stderr)
        self.assertIn("REDMOND_TEST_PASSWORD_INPUT=1", result.stderr)

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

    def test_backup_contract_uses_default_paths_under_game_dir(self) -> None:
        game_dir = create_game_dir()

        contract = backup_conf.describe_backup_contract(game_dir=game_dir)

        self.assertEqual(contract["backend"], "sqlite_local")
        self.assertEqual(
            contract["backup_root"],
            str(game_dir / "server" / "backups"),
        )
        self.assertEqual(contract["backup_root_source"], "default")
        self.assertEqual(
            contract["repository_dir"],
            str(
                game_dir
                / "server"
                / "backups"
                / "postgresql"
                / "repository"
            ),
        )
        self.assertEqual(
            contract["metadata_dir"],
            str(
                game_dir
                / "server"
                / "backups"
                / "postgresql"
                / "manifests"
            ),
        )
        self.assertEqual(contract["pgbackrest_command"], "pgbackrest")
        self.assertEqual(contract["pgbackrest_stanza"], "redmond")

    def test_backup_contract_honors_env_overrides(self) -> None:
        game_dir = create_game_dir()
        override_root = Path(tempfile.mkdtemp(prefix="redmond-backup-root-"))

        with mock.patch.dict(
            os.environ,
            {
                "REDMOND_BACKUP_DIR": str(override_root),
                "REDMOND_PGBACKREST_COMMAND": "/usr/local/bin/pgbackrest",
                "REDMOND_PGBACKREST_STANZA": "shadowrun",
            },
            clear=False,
        ):
            contract = backup_conf.describe_backup_contract(game_dir=game_dir)

        self.assertEqual(contract["backup_root"], str(override_root))
        self.assertEqual(contract["backup_root_source"], "env_override")
        self.assertEqual(
            contract["repository_dir"],
            str(override_root / "postgresql" / "repository"),
        )
        self.assertEqual(
            contract["metadata_dir"],
            str(override_root / "postgresql" / "manifests"),
        )
        self.assertEqual(
            contract["pgbackrest_command"],
            "/usr/local/bin/pgbackrest",
        )
        self.assertEqual(
            contract["pgbackrest_command_source"],
            "env_override",
        )
        self.assertEqual(contract["pgbackrest_stanza"], "shadowrun")
        self.assertEqual(
            contract["pgbackrest_stanza_source"],
            "env_override",
        )

    def test_backup_contract_rejects_persistent_paths_outside_game_dir(
        self,
    ) -> None:
        game_dir = create_game_dir()

        contract = backup_conf.describe_backup_contract(
            game_dir=game_dir,
            manifest_entries=("../outside.txt",),
        )

        persistent_files = contract["persistent_files"]
        assert isinstance(persistent_files, list)
        self.assertFalse(persistent_files[0]["valid"])
        self.assertEqual(
            persistent_files[0]["reason"],
            "path escapes the game dir",
        )

    def test_ensure_secret_settings_creates_local_overrides(self) -> None:
        game_dir = create_game_dir()

        secret_settings = bootstrap.ensure_secret_settings(game_dir)

        self.assertTrue(secret_settings.exists())
        content = secret_settings.read_text(encoding="ascii")
        self.assertIn("TELNET_PORTS = [", content)
        self.assertIn("WEBSERVER_PORTS = [(", content)
        self.assertIn("AMP_PORT = ", content)
        self.assert_owner_only_mode(secret_settings)

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
        env[WRAPPER_DISABLE_DEFAULT_CONFIG_ENV] = "1"

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

    def test_backup_status_reports_sqlite_mode_not_applicable(self) -> None:
        game_dir = create_game_dir()

        payload = load_backup_status(game_dir)

        self.assertEqual(payload["backend"], "sqlite_local")
        readiness = payload["readiness"]
        assert isinstance(readiness, dict)
        self.assertFalse(readiness["postgresql_inspection_eligible"])
        self.assertFalse(readiness["ready_for_read_only_listing"])
        self.assertEqual(readiness["status"], "not_applicable")

    def test_backup_status_reports_postgres_readiness(self) -> None:
        game_dir = create_game_dir()
        bootstrap.ensure_secret_settings(game_dir)
        repository_dir = (
            game_dir / "server" / "backups" / "postgresql" / "repository"
        )
        metadata_dir = (
            game_dir / "server" / "backups" / "postgresql" / "manifests"
        )
        repository_dir.mkdir(parents=True)
        metadata_dir.mkdir(parents=True)

        payload = load_backup_status(
            game_dir,
            env={
                "REDMOND_DATABASE_URL": (
                    "postgres://user:pass@db.example:5432/redmond"
                ),
                "REDMOND_PGBACKREST_COMMAND": "sh",
            },
        )

        self.assertEqual(payload["backend"], "postgresql")
        readiness = payload["readiness"]
        assert isinstance(readiness, dict)
        self.assertTrue(readiness["postgresql_inspection_eligible"])
        self.assertTrue(readiness["repository_dir_exists"])
        self.assertTrue(readiness["metadata_dir_exists"])
        self.assertTrue(readiness["persistent_paths_ready"])
        self.assertTrue(readiness["ready_for_read_only_listing"])
        self.assertEqual(readiness["status"], "ready_for_read_only_listing")

    def test_backup_status_reports_missing_pgbackrest_as_unready(self) -> None:
        game_dir = create_game_dir()
        bootstrap.ensure_secret_settings(game_dir)

        payload = load_backup_status(
            game_dir,
            env={
                "REDMOND_DATABASE_URL": (
                    "postgres://user:pass@db.example:5432/redmond"
                ),
                "REDMOND_PGBACKREST_COMMAND": "missing-pgbackrest-binary",
            },
        )

        readiness = payload["readiness"]
        assert isinstance(readiness, dict)
        self.assertFalse(readiness["ready_for_read_only_listing"])
        self.assertEqual(readiness["status"], "configured_not_ready")
        pgbackrest = payload["pgbackrest"]
        assert isinstance(pgbackrest, dict)
        self.assertFalse(pgbackrest["available"])

    def test_backup_status_reports_missing_persistent_files(self) -> None:
        game_dir = create_game_dir()

        payload = load_backup_status(
            game_dir,
            env={
                "REDMOND_DATABASE_URL": (
                    "postgres://user:pass@db.example:5432/redmond"
                ),
                "REDMOND_PGBACKREST_COMMAND": "sh",
            },
        )

        readiness = payload["readiness"]
        assert isinstance(readiness, dict)
        self.assertFalse(readiness["persistent_paths_ready"])
        config = payload["config"]
        assert isinstance(config, dict)
        persistent_files = config["persistent_files"]
        assert isinstance(persistent_files, list)
        self.assertEqual(persistent_files[0]["reason"], "missing file")

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

    def test_backup_list_rejects_sqlite_mode(self) -> None:
        game_dir = create_game_dir()

        with self.assertRaisesRegex(
            RuntimeError,
            "PostgreSQL backup listing",
        ):
            _backup_contract.backup_list(game_dir)

    def test_backup_list_normalizes_pgbackrest_info_output(self) -> None:
        game_dir = create_game_dir()
        payload = [
            {
                "backup": [
                    {
                        "archive": {
                            "start": "000000010000000000000001",
                            "stop": "000000010000000000000002",
                        },
                        "database": {
                            "id": 7,
                            "repo-key": 11,
                        },
                        "error": False,
                        "label": "20260707-010101F",
                        "reference": [],
                        "timestamp": {
                            "start": 100,
                            "stop": 110,
                        },
                        "type": "full",
                    }
                ],
                "name": "redmond",
                "status": {
                    "code": 0,
                    "message": "ok",
                },
            }
        ]

        with mock.patch.dict(
            os.environ,
            {
                "REDMOND_DATABASE_URL": (
                    "postgres://user:pass@db.example:5432/redmond"
                )
            },
            clear=False,
        ):
            with mock.patch.object(
                _backup_contract,
                "_run_pgbackrest_info",
                return_value=payload,
            ):
                result = _backup_contract.backup_list(game_dir)

        self.assertEqual(result["backend"], "postgresql")
        self.assertEqual(result["stanza"], "redmond")
        restore_points = result["restore_points"]
        assert isinstance(restore_points, list)
        self.assertEqual(restore_points[0]["label"], "20260707-010101F")
        self.assertEqual(restore_points[0]["type"], "full")
        self.assertEqual(restore_points[0]["database_id"], 7)
        self.assertEqual(restore_points[0]["database_repo_key"], 11)
        stanza_status = result["stanza_status"]
        assert isinstance(stanza_status, dict)
        self.assertEqual(stanza_status["code"], 0)
        self.assertEqual(stanza_status["message"], "ok")

    def test_backup_list_raises_on_invalid_json_output(self) -> None:
        repository_dir = Path(tempfile.mkdtemp(prefix="redmond-pg-repo-"))

        with self.assertRaisesRegex(RuntimeError, "invalid JSON"):
            with mock.patch.object(
                subprocess,
                "run",
                return_value=subprocess.CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout="not-json\n",
                    stderr="",
                ),
            ):
                _backup_contract._run_pgbackrest_info(
                    command="pgbackrest",
                    repository_dir=repository_dir,
                    stanza="redmond",
                )

    def test_backup_list_raises_on_pgbackrest_failure(self) -> None:
        repository_dir = Path(tempfile.mkdtemp(prefix="redmond-pg-repo-"))

        with self.assertRaisesRegex(RuntimeError, "permission denied"):
            with mock.patch.object(
                subprocess,
                "run",
                return_value=subprocess.CompletedProcess(
                    args=[],
                    returncode=2,
                    stdout="",
                    stderr="permission denied\n",
                ),
            ):
                _backup_contract._run_pgbackrest_info(
                    command="pgbackrest",
                    repository_dir=repository_dir,
                    stanza="redmond",
                )

    def test_backup_rejects_postgres_configuration(self) -> None:
        game_dir = create_game_dir()
        bootstrap.ensure_secret_settings(game_dir)
        (game_dir / "server" / "evennia.db3").write_text(
            "sqlite\n",
            encoding="ascii",
        )
        backup_dir = game_dir / "server" / "backups"

        with mock.patch.dict(
            os.environ,
            {
                "REDMOND_DATABASE_URL": (
                    "postgres://user:pass@db.example:5432/redmond"
                )
            },
            clear=False,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "SQLite-local recovery commands",
            ):
                bootstrap.create_backup(game_dir, backup_dir)

    def test_backup_requires_existing_sqlite_database(self) -> None:
        game_dir = create_game_dir()
        bootstrap.ensure_secret_settings(game_dir)
        backup_dir = game_dir / "server" / "backups"

        with self.assertRaisesRegex(
            RuntimeError,
            "server/evennia.db3",
        ):
            bootstrap.create_backup(game_dir, backup_dir)

    def test_backup_requires_existing_secret_settings(self) -> None:
        game_dir = create_game_dir()
        (game_dir / "server" / "evennia.db3").write_text(
            "sqlite\n",
            encoding="ascii",
        )
        backup_dir = game_dir / "server" / "backups"

        with self.assertRaisesRegex(
            RuntimeError,
            "server/conf/secret_settings.py",
        ):
            bootstrap.create_backup(game_dir, backup_dir)

    def test_backup_hardens_backup_directory_and_archive_modes(self) -> None:
        game_dir = create_game_dir()
        secret_settings = bootstrap.ensure_secret_settings(game_dir)
        sqlite_path = game_dir / "server" / "evennia.db3"
        sqlite_path.write_text("sqlite\n", encoding="ascii")
        backup_dir = game_dir / "server" / "backups"

        archive_path = bootstrap.create_backup(game_dir, backup_dir)

        self.assertEqual(
            stat.S_IMODE(backup_dir.stat().st_mode),
            stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR,
        )
        self.assert_owner_only_mode(archive_path)
        self.assert_owner_only_mode(secret_settings)

    def test_restore_rejects_postgres_configuration(self) -> None:
        game_dir = create_game_dir()
        archive_root = Path(tempfile.mkdtemp(prefix="redmond-archive-"))
        archive_path = archive_root / "backup.tar.gz"
        with tarfile.open(archive_path, "w:gz") as archive:
            for member_name, content in (
                ("server/evennia.db3", "sqlite\n"),
                ("server/conf/secret_settings.py", "SECRET_KEY='x'\n"),
            ):
                payload = archive_root / Path(member_name).name
                payload.write_text(content, encoding="ascii")
                archive.add(payload, arcname=member_name)

        with mock.patch.dict(
            os.environ,
            {
                "REDMOND_DATABASE_URL": (
                    "postgres://user:pass@db.example:5432/redmond"
                )
            },
            clear=False,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "SQLite-local recovery commands",
            ):
                bootstrap.restore_backup(game_dir, archive_path)

    def test_restore_rejects_missing_required_member(self) -> None:
        game_dir = create_game_dir()
        archive_root = Path(tempfile.mkdtemp(prefix="redmond-archive-"))
        archive_path = archive_root / "bad.tar.gz"
        payload = archive_root / "evennia.db3"
        payload.write_text("sqlite\n", encoding="ascii")
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(payload, arcname="server/evennia.db3")

        with self.assertRaisesRegex(RuntimeError, "missing required members"):
            bootstrap.restore_backup(game_dir, archive_path)

    def test_restore_leaves_live_files_untouched_when_validation_fails(
        self,
    ) -> None:
        game_dir = create_game_dir()
        sqlite_path = game_dir / "server" / "evennia.db3"
        secret_settings = game_dir / "server" / "conf" / "secret_settings.py"
        sqlite_path.write_text("live-db\n", encoding="ascii")
        secret_settings.write_text("live-secret\n", encoding="ascii")
        archive_root = Path(tempfile.mkdtemp(prefix="redmond-archive-"))
        archive_path = archive_root / "bad.tar.gz"
        payload = archive_root / "unexpected.txt"
        payload.write_text("bad\n", encoding="ascii")
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(payload, arcname="unexpected.txt")

        with self.assertRaises(RuntimeError):
            bootstrap.restore_backup(game_dir, archive_path)

        self.assertEqual(
            sqlite_path.read_text(encoding="ascii"),
            "live-db\n",
        )
        self.assertEqual(
            secret_settings.read_text(encoding="ascii"),
            "live-secret\n",
        )

    def test_restore_hardens_secret_settings_mode(self) -> None:
        game_dir = create_game_dir()
        sqlite_path = game_dir / "server" / "evennia.db3"
        secret_settings = game_dir / "server" / "conf" / "secret_settings.py"
        sqlite_path.write_text("live-db\n", encoding="ascii")
        secret_settings.write_text("live-secret\n", encoding="ascii")
        secret_settings.chmod(0o644)
        archive_root = Path(tempfile.mkdtemp(prefix="redmond-archive-"))
        archive_path = archive_root / "good.tar.gz"
        archived_sqlite = archive_root / "evennia.db3"
        archived_secret = archive_root / "secret_settings.py"
        archived_sqlite.write_text("restored-db\n", encoding="ascii")
        archived_secret.write_text("restored-secret\n", encoding="ascii")
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(archived_sqlite, arcname="server/evennia.db3")
            archive.add(
                archived_secret,
                arcname="server/conf/secret_settings.py",
            )

        bootstrap.restore_backup(game_dir, archive_path)

        self.assertEqual(
            secret_settings.read_text(encoding="ascii"),
            "restored-secret\n",
        )
        self.assert_owner_only_mode(secret_settings)

    def test_restore_stages_archive_on_game_dir_filesystem(self) -> None:
        game_dir = create_game_dir()
        archive_root = Path(tempfile.mkdtemp(prefix="redmond-archive-"))
        archive_path = archive_root / "good.tar.gz"
        archived_sqlite = archive_root / "evennia.db3"
        archived_secret = archive_root / "secret_settings.py"
        archived_sqlite.write_text("restored-db\n", encoding="ascii")
        archived_secret.write_text("restored-secret\n", encoding="ascii")
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(archived_sqlite, arcname="server/evennia.db3")
            archive.add(
                archived_secret,
                arcname="server/conf/secret_settings.py",
            )

        captured_kwargs: dict[str, object] = {}
        real_temp_dir = tempfile.TemporaryDirectory

        def capture_temp_dir(*args, **kwargs):
            captured_kwargs.update(kwargs)
            return real_temp_dir(*args, **kwargs)

        with mock.patch.object(
            _backup.tempfile,
            "TemporaryDirectory",
            side_effect=capture_temp_dir,
        ):
            bootstrap.restore_backup(game_dir, archive_path)

        self.assertEqual(captured_kwargs["dir"], game_dir)
        self.assertEqual(captured_kwargs["prefix"], "redmond-restore-")
