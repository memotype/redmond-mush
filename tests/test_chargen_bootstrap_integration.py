from __future__ import annotations

import json
import os
import subprocess
import unittest

from tests.bootstrap_test_utils import (
    PRODUCT_ROOT,
    PYTHON_BIN,
    PYTHONPATH_DIR,
    TEST_PASSWORD_INPUT_ENV,
    build_env,
    create_game_dir,
    run_command,
)


class ChargenBootstrapIntegrationTest(unittest.TestCase):
    def merged_env(self, extra: dict[str, str]) -> dict[str, str]:
        return {**os.environ, **extra}

    def _seed_character(self, game_dir, name: str, duplicate: bool = False):
        code = (
            "from pathlib import Path; "
            "from redmond_server.bootstrap._env import configure_django; "
            "configure_django(Path(r'"
            + str(game_dir)
            + "'), load_evennia=True); "
            "import evennia; "
            "from django.conf import settings; "
            "room = evennia.search_object('#2')[0]; "
            "evennia.create_object("
            "typeclass=settings.BASE_CHARACTER_TYPECLASS, "
            f"key='{name}', location=room, home=room)"
        )
        if duplicate:
            code += (
                "; evennia.create_object("
                "typeclass=settings.BASE_CHARACTER_TYPECLASS, "
                f"key='{name}', location=room, home=room)"
            )
        run_command(
            [PYTHON_BIN, "-c", code],
            cwd=PRODUCT_ROOT,
            env={"PYTHONPATH": PYTHONPATH_DIR},
        )

    def test_chargen_create_sample_bootstrap_command(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={**env, TEST_PASSWORD_INPUT_ENV: "1"},
            input_text="pass123\n",
        )
        self._seed_character(game_dir, "SampleChar")

        result = json.loads(
            run_command(
                [
                    PYTHON_BIN,
                    "-m",
                    "redmond_server.bootstrap",
                    "chargen-create-sample",
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

        self.assertEqual(result["status"], "created")
        self.assertEqual(result["character_key"], "SampleChar")
        self.assertEqual(result["starting_karma_snapshot"], 50)

    def test_chargen_create_sample_requires_opt_in(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={**env, TEST_PASSWORD_INPUT_ENV: "1"},
            input_text="pass123\n",
        )

        result = subprocess.run(
            [
                PYTHON_BIN,
                "-m",
                "redmond_server.bootstrap",
                "chargen-create-sample",
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

    def test_chargen_create_sample_repeat_is_non_mutating(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={**env, TEST_PASSWORD_INPUT_ENV: "1"},
            input_text="pass123\n",
        )
        self._seed_character(game_dir, "SampleChar")

        args = [
            PYTHON_BIN,
            "-m",
            "redmond_server.bootstrap",
            "chargen-create-sample",
            "--character",
            "SampleChar",
            "--allow-dev-sample-data",
            "--game-dir",
            str(game_dir),
        ]
        first = json.loads(
            run_command(
                args,
                cwd=PRODUCT_ROOT,
                env={"PYTHONPATH": PYTHONPATH_DIR},
            ).stdout
        )
        second = json.loads(
            run_command(
                args,
                cwd=PRODUCT_ROOT,
                env={"PYTHONPATH": PYTHONPATH_DIR},
            ).stdout
        )

        self.assertEqual(first["status"], "created")
        self.assertEqual(second["status"], "exists")
        self.assertEqual(first["session_id"], second["session_id"])

    def test_chargen_create_sample_missing_target_is_structured(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={**env, TEST_PASSWORD_INPUT_ENV: "1"},
            input_text="pass123\n",
        )

        result = subprocess.run(
            [
                PYTHON_BIN,
                "-m",
                "redmond_server.bootstrap",
                "chargen-create-sample",
                "--character",
                "NoSuchCharacter",
                "--allow-dev-sample-data",
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
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["code"], "character_not_found")

    def test_chargen_create_sample_ambiguous_target_is_structured(
        self,
    ) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={**env, TEST_PASSWORD_INPUT_ENV: "1"},
            input_text="pass123\n",
        )
        self._seed_character(game_dir, "SampleChar", duplicate=True)

        result = subprocess.run(
            [
                PYTHON_BIN,
                "-m",
                "redmond_server.bootstrap",
                "chargen-create-sample",
                "--character",
                "SampleChar",
                "--allow-dev-sample-data",
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
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["code"], "character_name_ambiguous")

    def test_chargen_create_sample_explicit_unavailable_profile(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={**env, TEST_PASSWORD_INPUT_ENV: "1"},
            input_text="pass123\n",
        )
        self._seed_character(game_dir, "SampleChar")
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
                    "from chargen.services import "
                    "EnsureChargenRulesProfileInput, "
                    "ensure_chargen_rules_profile; "
                    "ensure_chargen_rules_profile("
                    "EnsureChargenRulesProfileInput("
                    "profile_key='offline_profile', version=1, "
                    "display_name='Offline Profile', "
                    "is_available_for_new_sessions=False, "
                    "is_default_for_new_sessions=False, "
                    "starting_karma=25))"
                ),
            ],
            cwd=PRODUCT_ROOT,
            env={"PYTHONPATH": PYTHONPATH_DIR},
        )

        result = subprocess.run(
            [
                PYTHON_BIN,
                "-m",
                "redmond_server.bootstrap",
                "chargen-create-sample",
                "--character",
                "SampleChar",
                "--profile-key",
                "offline_profile",
                "--version",
                "1",
                "--allow-dev-sample-data",
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
        self.assertEqual(payload["code"], "profile_unavailable")

    def test_bootstrap_does_not_create_chargen_implicitly(self) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={**env, TEST_PASSWORD_INPUT_ENV: "1"},
            input_text="pass123\n",
        )

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
                        "from chargen.models import ChargenSession; "
                        "print(json.dumps({"
                        "'session_count': ChargenSession.objects.count()"
                        "}))"
                    ),
                ],
                cwd=PRODUCT_ROOT,
                env={"PYTHONPATH": PYTHONPATH_DIR},
            ).stdout
        )

        self.assertEqual(result["session_count"], 0)
