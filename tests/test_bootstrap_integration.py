from __future__ import annotations

import json
import os
import subprocess
import unittest

from tests.bootstrap_test_utils import (
    TEST_PASSWORD_INPUT_ENV,
    account_password_matches,
    PRODUCT_ROOT,
    PYTHON_BIN,
    PYTHONPATH_DIR,
    build_env,
    cleanup_process,
    create_game_dir,
    create_initialized_game_dir,
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
        game_dir = create_initialized_game_dir()
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
        game_dir = create_initialized_game_dir()

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

    def test_init_local_rerun_skips_existing_superuser_prompt(self) -> None:
        game_dir = create_game_dir()
        env = {
            **build_env(game_dir),
            TEST_PASSWORD_INPUT_ENV: "1",
        }
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env=env,
            input_text="pass123\n",
        )

        rerun = run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env=build_env(game_dir),
        )

        self.assertIn("Redmond local bootstrap complete.", rerun.stdout)

    def test_seed_is_idempotent(self) -> None:
        game_dir = create_initialized_game_dir()

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

    def test_sheet_create_sample_bootstrap_command(self) -> None:
        game_dir = create_initialized_game_dir()

        run_command(
            [
                PYTHON_BIN,
                "-c",
                (
                    "from pathlib import Path; "
                    "from redmond_server.bootstrap._env import "
                    "configure_django; "
                    "configure_django(Path(r'"
                    + str(game_dir)
                    + "'), load_evennia=True); "
                    "import evennia; "
                    "from django.conf import settings; "
                    "room = evennia.search_object('#2')[0]; "
                    "evennia.create_object("
                    "typeclass=settings.BASE_CHARACTER_TYPECLASS, "
                    "key='SampleChar', location=room, home=room)"
                ),
            ],
            cwd=PRODUCT_ROOT,
            env={"PYTHONPATH": PYTHONPATH_DIR},
        )

        result = json.loads(
            run_command(
                [
                    PYTHON_BIN,
                    "-m",
                    "redmond_server.bootstrap",
                    "sheet-create-sample",
                    "--character",
                    "SampleChar",
                    "--allow-dev-sample-data",
                    "--game-dir",
                    str(game_dir),
                ],
                cwd=PRODUCT_ROOT,
                env={"PYTHONPATH": PYTHONPATH_DIR},
            ).stdout
        )

        self.assertEqual(result["character_key"], "SampleChar")
        self.assertEqual(result["skill_count"], 2)
        self.assertEqual(result["status"], "created")

    def test_sheet_create_sample_requires_explicit_opt_in(self) -> None:
        game_dir = create_initialized_game_dir()
        result = subprocess.run(
            [
                PYTHON_BIN,
                "-m",
                "redmond_server.bootstrap",
                "sheet-create-sample",
                "--character",
                "SampleChar",
                "--game-dir",
                str(game_dir),
            ],
            cwd=PRODUCT_ROOT,
            env=self.merged_env({"PYTHONPATH": PYTHONPATH_DIR}),
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "refused")
        self.assertIn("allow-dev-sample-data", payload["message"])

    def test_sheet_create_sample_repeat_is_stable_and_non_mutating(
        self,
    ) -> None:
        game_dir = create_initialized_game_dir()
        run_command(
            [
                PYTHON_BIN,
                "-c",
                (
                    "from pathlib import Path; "
                    "from redmond_server.bootstrap._env import "
                    "configure_django; "
                    "configure_django(Path(r'"
                    + str(game_dir)
                    + "'), load_evennia=True); "
                    "import evennia; "
                    "from django.conf import settings; "
                    "room = evennia.search_object('#2')[0]; "
                    "evennia.create_object("
                    "typeclass=settings.BASE_CHARACTER_TYPECLASS, "
                    "key='SampleChar', location=room, home=room)"
                ),
            ],
            cwd=PRODUCT_ROOT,
            env={"PYTHONPATH": PYTHONPATH_DIR},
        )

        create_args = [
            PYTHON_BIN,
            "-m",
            "redmond_server.bootstrap",
            "sheet-create-sample",
            "--character",
            "SampleChar",
            "--allow-dev-sample-data",
            "--game-dir",
            str(game_dir),
        ]
        first = json.loads(
            run_command(
                create_args,
                cwd=PRODUCT_ROOT,
                env={"PYTHONPATH": PYTHONPATH_DIR},
            ).stdout
        )
        second = json.loads(
            run_command(
                create_args,
                cwd=PRODUCT_ROOT,
                env={"PYTHONPATH": PYTHONPATH_DIR},
            ).stdout
        )
        sheet_state = json.loads(
            run_command(
                [
                    PYTHON_BIN,
                    "-c",
                    (
                        "from pathlib import Path; "
                        "import json; "
                        "from redmond_server.bootstrap._env import "
                        "configure_django; "
                        "configure_django(Path(r'"
                        + str(game_dir)
                        + "'), load_evennia=True); "
                        "from sheets.models import CharacterSheet; "
                        "sheet = CharacterSheet.objects.get("
                        "character__db_key='SampleChar'); "
                        "print(json.dumps({"
                        "'sheet_id': sheet.id, "
                        "'alias': sheet.alias, "
                        "'skill_count': sheet.skills.count()"
                        "}))"
                    ),
                ],
                cwd=PRODUCT_ROOT,
                env={"PYTHONPATH": PYTHONPATH_DIR},
            ).stdout
        )

        self.assertEqual(first["status"], "created")
        self.assertEqual(second["status"], "exists")
        self.assertEqual(first["sheet_id"], second["sheet_id"])
        self.assertEqual(sheet_state["sheet_id"], first["sheet_id"])
        self.assertEqual(sheet_state["alias"], "Sample Runner")
        self.assertEqual(sheet_state["skill_count"], 2)

    def test_normal_bootstrap_flows_do_not_create_sample_sheet_implicitly(
        self,
    ) -> None:
        game_dir = create_initialized_game_dir()

        result = json.loads(
            run_command(
                [
                    PYTHON_BIN,
                    "-c",
                    (
                        "from pathlib import Path; "
                        "import json; "
                        "from redmond_server.bootstrap._env import "
                        "configure_django; "
                        "configure_django(Path(r'"
                        + str(game_dir)
                        + "'), load_evennia=True); "
                        "from sheets.models import CharacterSheet; "
                        "print(json.dumps({"
                        "'sheet_count': CharacterSheet.objects.count()"
                        "}))"
                    ),
                ],
                cwd=PRODUCT_ROOT,
                env={"PYTHONPATH": PYTHONPATH_DIR},
            ).stdout
        )
        self.assertEqual(result["sheet_count"], 0)

    def test_reset_local_recreates_state_and_cleans_runtime(self) -> None:
        game_dir = create_initialized_game_dir()
        env = build_env(game_dir)
        overwrite_room_name(game_dir, "Broken Room")

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
        (game_dir / "server" / "server.pid").write_text(
            f"{proc.pid}\n",
            encoding="ascii",
        )
        (game_dir / "server" / "portal.pid").write_text(
            "999999\n",
            encoding="ascii",
        )
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

        self.assertIsNotNone(proc.poll())
        state = load_state(game_dir)
        self.assertEqual(state["ooc_room_key"], "Redmond OOC Hub")
        self.assertEqual(state["legal_help_count"], 1)

        doctor = load_doctor(game_dir)
        runtime = doctor["runtime"]
        assert isinstance(runtime, dict)
        self.assertEqual(runtime["running_process_count"], 0)
        self.assertEqual(runtime["stale_pidfile_count"], 0)
        self.assertFalse(runtime["runtime_marker_present"])
        pidfiles = runtime["pidfiles"]
        assert isinstance(pidfiles, dict)
        for name in ("server.pid", "portal.pid"):
            pidfile = pidfiles[name]
            assert isinstance(pidfile, dict)
            self.assertFalse(pidfile["exists"])
        flags = runtime["restart_or_stop_flags"]
        assert isinstance(flags, dict)
        self.assertFalse(flags["server.restart"])

    def test_doctor_command_reports_postgres_configuration(self) -> None:
        game_dir = create_initialized_game_dir()

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
        database_error = str(doctor["database_error"])
        self.assertNotIn("secret", database_error)
