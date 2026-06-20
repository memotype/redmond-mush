from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tarfile
import unittest

from tests.bootstrap_test_utils import (
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
    def test_account_mutations_succeed_when_staff_sync_is_deferred(
        self,
    ) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(["./scripts/init_local.sh"], cwd=PRODUCT_ROOT, env=env)
        fault_env = {
            "PYTHONPATH": PYTHONPATH_DIR,
            "REDMOND_TEST_FAIL_STAFF_SYNC": "1",
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
                    "--password",
                    "alice-pass-1",
                    "--email",
                    "alice@example.com",
                    "--superuser",
                    "--game-dir",
                    str(game_dir),
                ],
                cwd=PRODUCT_ROOT,
                env=fault_env,
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
        run_command(["./scripts/init_local.sh"], cwd=PRODUCT_ROOT, env=env)

        run_command(
            [
                PYTHON_BIN,
                "-m",
                "redmond_server.bootstrap",
                "account-create",
                "--username",
                "alice",
                "--password",
                "alice-pass",
                "--email",
                "alice@example.com",
                "--game-dir",
                str(game_dir),
            ],
            cwd=PRODUCT_ROOT,
            env={"PYTHONPATH": PYTHONPATH_DIR},
        )
        run_command(
            [
                PYTHON_BIN,
                "-m",
                "redmond_server.bootstrap",
                "account-set-password",
                "--username",
                "alice",
                "--password",
                "alice-pass-2",
                "--game-dir",
                str(game_dir),
            ],
            cwd=PRODUCT_ROOT,
            env={"PYTHONPATH": PYTHONPATH_DIR},
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
            env=build_env(game_dir),
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
        run_command(["./scripts/init_local.sh"], cwd=PRODUCT_ROOT, env=env)

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
        run_command(["./scripts/init_local.sh"], cwd=PRODUCT_ROOT, env=env)
        overwrite_room_name(game_dir, "Broken Room")

        run_command(["./scripts/reset_local.sh"], cwd=PRODUCT_ROOT, env=env)

        state = load_state(game_dir)
        self.assertEqual(state["ooc_room_key"], "Redmond OOC Hub")
        self.assertEqual(state["legal_help_count"], 1)

    def test_reset_local_cleans_stale_pidfiles(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(["./scripts/init_local.sh"], cwd=PRODUCT_ROOT, env=env)

        pidfile = game_dir / "server" / "server.pid"
        pidfile.write_text("999999\n", encoding="ascii")
        (game_dir / "server" / "server.restart").write_text(
            "",
            encoding="ascii",
        )

        run_command(["./scripts/reset_local.sh"], cwd=PRODUCT_ROOT, env=env)

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
        run_command(["./scripts/init_local.sh"], cwd=PRODUCT_ROOT, env=env)

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

        run_command(["./scripts/reset_local.sh"], cwd=PRODUCT_ROOT, env=env)

        self.assertIsNotNone(proc.poll())
        doctor = load_doctor(game_dir)
        runtime = doctor["runtime"]
        assert isinstance(runtime, dict)
        self.assertEqual(runtime["running_process_count"], 0)

    def test_backup_and_restore_round_trip(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(["./scripts/init_local.sh"], cwd=PRODUCT_ROOT, env=env)

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
