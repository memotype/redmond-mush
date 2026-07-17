from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import tarfile
from typing import cast
import unittest

from redmond_server import bootstrap

from tests.bootstrap_test_utils import (
    TEST_PASSWORD_INPUT_ENV,
    account_password_matches,
    PRODUCT_ROOT,
    PYTHON_BIN,
    PYTHONPATH_DIR,
    build_env,
    cleanup_process,
    create_game_dir,
    load_accounts,
    load_doctor,
    load_state,
    overwrite_room_name,
    require_int,
    require_list,
    run_command,
)


class BootstrapIntegrationTest(unittest.TestCase):
    def merged_env(self, extra: dict[str, str]) -> dict[str, str]:
        return {**os.environ, **extra}

    def test_account_mutations_succeed_when_staff_sync_is_deferred(
        self,
    ) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )
        fault_env = {
            "PYTHONPATH": PYTHONPATH_DIR,
            "REDMOND_TEST_FAIL_STAFF_SYNC": "1",
            TEST_PASSWORD_INPUT_ENV: "1",
        }

        create_result = json.loads(
            run_command(
                [
                    PYTHON_BIN,
                    "-m",
                    "redmond_server.bootstrap",
                    "account-create",
                    "--username",
                    "alice",
                    "--email",
                    "alice@example.com",
                    "--superuser",
                    "--game-dir",
                    str(game_dir),
                ],
                cwd=PRODUCT_ROOT,
                env=fault_env,
                input_text="alice-pass-1\n",
            ).stdout
        )
        promote_result = json.loads(
            run_command(
                [
                    PYTHON_BIN,
                    "-m",
                    "redmond_server.bootstrap",
                    "account-set-superuser",
                    "--username",
                    "alice",
                    "--value",
                    "false",
                    "--game-dir",
                    str(game_dir),
                ],
                cwd=PRODUCT_ROOT,
                env=fault_env,
            ).stdout
        )

        self.assertTrue(create_result["created"])
        self.assertEqual(create_result["follow_up"]["status"], "deferred")
        self.assertIn("staff-channel sync", create_result["warning"])
        self.assertIn(
            "REDMOND_TEST_FAIL_STAFF_SYNC=1",
            create_result["warning"],
        )
        self.assertFalse(promote_result["is_superuser"])
        self.assertEqual(promote_result["follow_up"]["status"], "deferred")
        self.assertIn("staff-channel sync", promote_result["warning"])
        self.assertIn(
            "REDMOND_TEST_FAIL_STAFF_SYNC=1",
            promote_result["warning"],
        )

        accounts = load_accounts(game_dir)
        alice = next(
            account
            for account in accounts
            if account["username"] == "alice"
        )
        self.assertFalse(alice["is_superuser"])
        self.assertFalse(alice["is_staff"])

    def test_account_management_flow(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )

        run_command(
            [
                PYTHON_BIN,
                "-m",
                "redmond_server.bootstrap",
                "account-create",
                "--username",
                "alice",
                "--email",
                "alice@example.com",
                "--game-dir",
                str(game_dir),
            ],
            cwd=PRODUCT_ROOT,
            env={
                "PYTHONPATH": PYTHONPATH_DIR,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="alice-pass\n",
        )
        run_command(
            [
                PYTHON_BIN,
                "-m",
                "redmond_server.bootstrap",
                "account-set-password",
                "--username",
                "alice",
                "--game-dir",
                str(game_dir),
            ],
            cwd=PRODUCT_ROOT,
            env={
                "PYTHONPATH": PYTHONPATH_DIR,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="alice-pass-2\n",
        )
        run_command(
            [
                PYTHON_BIN,
                "-m",
                "redmond_server.bootstrap",
                "account-set-superuser",
                "--username",
                "alice",
                "--value",
                "true",
                "--game-dir",
                str(game_dir),
            ],
            cwd=PRODUCT_ROOT,
            env={"PYTHONPATH": PYTHONPATH_DIR},
        )

        accounts = load_accounts(game_dir)
        alice = next(
            account
            for account in accounts
            if account["username"] == "alice"
        )
        self.assertEqual(alice["email"], "alice@example.com")
        self.assertTrue(alice["is_staff"])
        self.assertTrue(alice["is_superuser"])
        self.assertTrue(
            account_password_matches(game_dir, "alice", "alice-pass-2")
        )

    def test_init_local_bootstraps_world(self) -> None:
        game_dir = create_game_dir()
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **build_env(game_dir),
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )

        state = load_state(game_dir)
        self.assertTrue(state["db_exists"])
        self.assertTrue(state["secret_settings_exists"])
        self.assertEqual(state["ooc_room_key"], "Redmond OOC Hub")
        self.assertEqual(state["legal_help_count"], 1)
        self.assertIn("Public", require_list(state, "channel_keys"))
        self.assertIn("Staff", require_list(state, "channel_keys"))
        self.assertGreaterEqual(require_int(state, "account_count"), 1)
        self.assertGreaterEqual(require_int(state, "object_count"), 2)

    def test_seed_is_idempotent(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )

        first = load_state(game_dir)
        run_command(
            [
                PYTHON_BIN,
                "-m",
                "redmond_server.bootstrap",
                "seed",
                "--game-dir",
                str(game_dir),
            ],
            cwd=PRODUCT_ROOT,
            env={"PYTHONPATH": PYTHONPATH_DIR},
        )
        second = load_state(game_dir)
        self.assertEqual(first, second)

    def test_reset_local_recreates_clean_state(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )
        overwrite_room_name(game_dir, "Broken Room")

        run_command(
            ["./scripts/reset_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )

        state = load_state(game_dir)
        self.assertEqual(state["ooc_room_key"], "Redmond OOC Hub")
        self.assertEqual(state["legal_help_count"], 1)

    def test_reset_local_cleans_stale_pidfiles(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )

        pidfile = game_dir / "server" / "server.pid"
        pidfile.write_text("999999\n", encoding="ascii")
        (game_dir / "server" / "server.restart").write_text(
            "",
            encoding="ascii",
        )

        run_command(
            ["./scripts/reset_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )

        doctor = load_doctor(game_dir)
        runtime = doctor["runtime"]
        assert isinstance(runtime, dict)
        self.assertEqual(runtime["stale_pidfile_count"], 0)
        pidfiles = runtime["pidfiles"]
        assert isinstance(pidfiles, dict)
        server_pidfile = pidfiles["server.pid"]
        assert isinstance(server_pidfile, dict)
        self.assertFalse(server_pidfile["exists"])

    def test_reset_local_stops_pidfile_processes(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )

        proc = subprocess.Popen(
            [
                "bash",
                "-lc",
                f'exec -a "{game_dir}/server/server.pid" sleep 300',
            ],
            cwd=PRODUCT_ROOT,
            text=True,
        )
        self.addCleanup(cleanup_process, proc)
        pidfile = game_dir / "server" / "server.pid"
        pidfile.write_text(f"{proc.pid}\n", encoding="ascii")

        run_command(
            ["./scripts/reset_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )

        self.assertIsNotNone(proc.poll())
        doctor = load_doctor(game_dir)
        runtime = doctor["runtime"]
        assert isinstance(runtime, dict)
        self.assertEqual(runtime["running_process_count"], 0)

    def test_doctor_command_reports_postgres_configuration(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )

        doctor = load_doctor(
            game_dir,
            env={
                "REDMOND_DATABASE_URL": (
                    "postgres://user:secret@127.0.0.1:1/redmond"
                ),
            },
        )

        self.assertIsNone(doctor["db_exists"])
        database = doctor["database"]
        assert isinstance(database, dict)
        self.assertEqual(database["engine"], "postgresql")
        self.assertEqual(database["source"], "env_url")
        self.assertEqual(database["host"], "127.0.0.1")
        self.assertEqual(database["port"], 1)
        self.assertEqual(database["database_name"], "redmond")
        self.assertIsNone(database["sqlite_path"])
        self.assertIn("database_error", doctor)
        database_error = cast(str, doctor["database_error"])
        self.assertNotIn("secret", database_error)

    def test_backup_status_wrapper_passes_through_bootstrap_json(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        result = run_command(
            ["./scripts/backup_status.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                "REDMOND_DATABASE_URL": (
                    "postgres://user:secret@127.0.0.1:5432/redmond"
                ),
                "REDMOND_PGBACKREST_COMMAND": "missing-pgbackrest-binary",
            },
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["backend"], "postgresql")
        readiness = payload["readiness"]
        assert isinstance(readiness, dict)
        self.assertEqual(readiness["status"], "configured_not_ready")

    def test_backup_list_wrapper_passes_through_pgbackrest_output(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        bootstrap.ensure_secret_settings(game_dir)
        repository_dir = (
            game_dir / "server" / "backups" / "postgresql" / "repository"
        )
        metadata_dir = (
            game_dir / "server" / "backups" / "postgresql" / "manifests"
        )
        repository_dir.mkdir(parents=True)
        metadata_dir.mkdir(parents=True)
        fake_bin = Path(tempfile.mkdtemp(prefix="redmond-fake-bin-"))
        pgbackrest_path = fake_bin / "pgbackrest"
        pgbackrest_path.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' "
            "'[{\"name\":\"redmond\",\"status\":{\"code\":0,"
            "\"message\":\"ok\"},\"backup\":[{\"label\":\"demo-full\","
            "\"type\":\"full\",\"reference\":[],\"error\":false,"
            "\"timestamp\":{\"start\":10,\"stop\":20}}]}]'\n",
            encoding="ascii",
        )
        pgbackrest_path.chmod(0o755)

        result = run_command(
            ["./scripts/backup_list.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                "REDMOND_DATABASE_URL": (
                    "postgres://user:secret@127.0.0.1:5432/redmond"
                ),
                "REDMOND_PGBACKREST_COMMAND": str(pgbackrest_path),
            },
        )

        payload = json.loads(result.stdout)
        restore_points = payload["restore_points"]
        assert isinstance(restore_points, list)
        self.assertEqual(restore_points[0]["label"], "demo-full")
        self.assertEqual(restore_points[0]["type"], "full")

    def test_backup_list_wrapper_reports_failure_states(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        result = subprocess.run(
            ["./scripts/backup_list.sh"],
            cwd=PRODUCT_ROOT,
            env=self.merged_env(
                {
                    **env,
                    "REDMOND_DATABASE_URL": (
                        "postgres://user:secret@127.0.0.1:5432/redmond"
                    ),
                    "REDMOND_PGBACKREST_COMMAND": (
                        "missing-pgbackrest-binary"
                    ),
                }
            ),
            check=False,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("pgBackRest command not found", result.stderr)

    def test_backup_create_wrapper_passes_through_bootstrap_json(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        bootstrap.ensure_secret_settings(game_dir)
        repository_dir = (
            game_dir / "server" / "backups" / "postgresql" / "repository"
        )
        repository_dir.mkdir(parents=True)
        fake_bin = Path(tempfile.mkdtemp(prefix="redmond-fake-bin-"))
        pgbackrest_path = fake_bin / "pgbackrest"
        pgbackrest_path.write_text(
            "#!/usr/bin/env bash\nexit 0\n",
            encoding="ascii",
        )
        pgbackrest_path.chmod(0o755)

        result = run_command(
            ["./scripts/backup_create.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                "REDMOND_DATABASE_URL": (
                    "postgres://user:secret@127.0.0.1:5432/redmond"
                ),
                "REDMOND_PGBACKREST_COMMAND": str(pgbackrest_path),
            },
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["backend"], "postgresql")
        self.assertEqual(payload["backup_type"], "full")
        self.assertEqual(
            payload["repository_dir"],
            str(repository_dir),
        )
        metadata_path = Path(str(payload["metadata_path"]))
        self.assertTrue(metadata_path.is_file())
        metadata_payload = json.loads(
            metadata_path.read_text(encoding="ascii")
        )
        self.assertEqual(metadata_payload["backup_type"], "full")

    def test_backup_create_wrapper_reports_missing_pgbackrest(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        bootstrap.ensure_secret_settings(game_dir)
        repository_dir = (
            game_dir / "server" / "backups" / "postgresql" / "repository"
        )
        repository_dir.mkdir(parents=True)

        result = subprocess.run(
            ["./scripts/backup_create.sh"],
            cwd=PRODUCT_ROOT,
            env=self.merged_env(
                {
                    **env,
                    "REDMOND_DATABASE_URL": (
                        "postgres://user:secret@127.0.0.1:5432/redmond"
                    ),
                    "REDMOND_PGBACKREST_COMMAND": (
                        "missing-pgbackrest-binary"
                    ),
                }
            ),
            check=False,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("pgBackRest command not found", result.stderr)

    def test_backup_create_wrapper_rejects_sqlite_configuration(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)

        result = subprocess.run(
            ["./scripts/backup_create.sh"],
            cwd=PRODUCT_ROOT,
            env=self.merged_env(env),
            check=False,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PostgreSQL backup creation", result.stderr)

    def test_backup_and_restore_round_trip(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )

        backup_result = run_command(
            ["./scripts/backup_local.sh"],
            cwd=PRODUCT_ROOT,
            env=env,
        )
        archive_line = backup_result.stdout.strip().split(": ", maxsplit=1)[-1]
        archive_path = Path(archive_line)
        self.assertTrue(archive_path.exists())
        with tarfile.open(archive_path, "r:gz") as archive:
            members = sorted(member.name for member in archive.getmembers())
        self.assertIn("server/evennia.db3", members)
        self.assertIn("server/conf/secret_settings.py", members)

        overwrite_room_name(game_dir, "Mutated Room")
        run_command(
            ["./scripts/restore_local.sh", str(archive_path)],
            cwd=PRODUCT_ROOT,
            env=env,
        )

        state = load_state(game_dir)
        self.assertEqual(state["ooc_room_key"], "Redmond OOC Hub")

    def test_backup_local_rejects_postgres_configuration(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )

        result = subprocess.run(
            ["./scripts/backup_local.sh"],
            cwd=PRODUCT_ROOT,
            env=self.merged_env(
                {
                **env,
                "REDMOND_DATABASE_URL": (
                    "postgres://user:secret@127.0.0.1:5432/redmond"
                ),
                }
            ),
            check=False,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SQLite-local recovery commands", result.stderr)

    def test_backup_local_fails_without_recreating_secret_settings(
        self,
    ) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )
        secret_settings = game_dir / "server" / "conf" / "secret_settings.py"
        secret_settings.unlink()

        result = subprocess.run(
            ["./scripts/backup_local.sh"],
            cwd=PRODUCT_ROOT,
            env=self.merged_env(env),
            check=False,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("server/conf/secret_settings.py", result.stderr)
        self.assertFalse(secret_settings.exists())

    def test_restore_local_rejects_postgres_configuration(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )
        backup_result = run_command(
            ["./scripts/backup_local.sh"],
            cwd=PRODUCT_ROOT,
            env=env,
        )
        archive_path = Path(
            backup_result.stdout.strip().split(": ", maxsplit=1)[-1]
        )

        result = subprocess.run(
            ["./scripts/restore_local.sh", str(archive_path)],
            cwd=PRODUCT_ROOT,
            env=self.merged_env(
                {
                **env,
                "REDMOND_DATABASE_URL": (
                    "postgres://user:secret@127.0.0.1:5432/redmond"
                ),
                }
            ),
            check=False,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SQLite-local recovery commands", result.stderr)

    def test_restore_local_rejects_postgres_before_stop_side_effects(
        self,
    ) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )
        backup_result = run_command(
            ["./scripts/backup_local.sh"],
            cwd=PRODUCT_ROOT,
            env=env,
        )
        archive_path = Path(
            backup_result.stdout.strip().split(": ", maxsplit=1)[-1]
        )

        proc = subprocess.Popen(
            [
                "bash",
                "-lc",
                f'exec -a "{game_dir}/server/server.pid" sleep 300',
            ],
            cwd=PRODUCT_ROOT,
            text=True,
        )
        self.addCleanup(cleanup_process, proc)
        pidfile = game_dir / "server" / "server.pid"
        pidfile.write_text(f"{proc.pid}\n", encoding="ascii")

        result = subprocess.run(
            ["./scripts/restore_local.sh", str(archive_path)],
            cwd=PRODUCT_ROOT,
            env=self.merged_env(
                {
                    **env,
                    "REDMOND_DATABASE_URL": (
                        "postgres://user:secret@127.0.0.1:5432/redmond"
                    ),
                }
            ),
            check=False,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SQLite-local recovery commands", result.stderr)
        self.assertIsNone(proc.poll())
        self.assertTrue(pidfile.exists())

    def test_reset_local_rejects_postgres_configuration_before_delete(
        self,
    ) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )
        sqlite_path = game_dir / "server" / "evennia.db3"
        self.assertTrue(sqlite_path.exists())

        result = subprocess.run(
            ["./scripts/reset_local.sh"],
            cwd=PRODUCT_ROOT,
            env=self.merged_env(
                {
                **env,
                "REDMOND_DATABASE_URL": (
                    "postgres://user:secret@127.0.0.1:5432/redmond"
                ),
                }
            ),
            check=False,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SQLite-local recovery commands", result.stderr)
        self.assertTrue(sqlite_path.exists())

    def test_restore_local_invalid_archive_keeps_live_state(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )
        sqlite_path = game_dir / "server" / "evennia.db3"
        secret_settings = game_dir / "server" / "conf" / "secret_settings.py"
        live_db = sqlite_path.read_bytes()
        live_secret = secret_settings.read_text(encoding="ascii")
        archive_root = Path(tempfile.mkdtemp(prefix="redmond-archive-"))
        archive_path = archive_root / "bad.tar.gz"
        payload = archive_root / "unexpected.txt"
        payload.write_text("bad\n", encoding="ascii")
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(payload, arcname="unexpected.txt")

        result = subprocess.run(
            ["./scripts/restore_local.sh", str(archive_path)],
            cwd=PRODUCT_ROOT,
            env=self.merged_env(env),
            check=False,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unexpected backup member", result.stderr)
        self.assertEqual(sqlite_path.read_bytes(), live_db)
        self.assertEqual(
            secret_settings.read_text(encoding="ascii"),
            live_secret,
        )
