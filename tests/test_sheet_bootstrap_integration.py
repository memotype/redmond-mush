from __future__ import annotations

import json
import subprocess
import unittest

from tests.bootstrap_test_utils import (
    PRODUCT_ROOT,
    PYTHON_BIN,
    PYTHONPATH_DIR,
    create_initialized_game_dir,
    run_command,
)


class SheetBootstrapIntegrationTest(unittest.TestCase):
    def merged_env(self, extra: dict[str, str]) -> dict[str, str]:
        import os

        return {**os.environ, **extra}

    def test_clean_install_rejects_direct_sheet_create_without_status(
        self,
    ) -> None:
        game_dir = create_initialized_game_dir()

        result = subprocess.run(
            [
                PYTHON_BIN,
                "-c",
                (
                    "from pathlib import Path\n"
                    "from decimal import Decimal\n"
                    "from redmond_server.bootstrap._env import "
                    "configure_django\n"
                    "configure_django(Path(r'"
                    + str(game_dir)
                    + "'), load_evennia=True)\n"
                    "import evennia\n"
                    "from django.conf import settings\n"
                    "from django.db import IntegrityError, transaction\n"
                    "from sheets.models import CharacterSheet\n"
                    "room = evennia.search_object('#2')[0]\n"
                    "character = evennia.create_object(\n"
                    "    typeclass=settings.BASE_CHARACTER_TYPECLASS,\n"
                    "    key='SheetStatusCheck',\n"
                    "    location=room,\n"
                    "    home=room,\n"
                    ")\n"
                    "try:\n"
                    "    with transaction.atomic():\n"
                    "        CharacterSheet.objects.create(\n"
                    "            character=character,\n"
                    "            alias='Ghost',\n"
                    "            pronouns='they/them',\n"
                    "            metatype='Human',\n"
                    "            archetype_label='Runner',\n"
                    "            short_concept='Observant scout',\n"
                    "            backstory='Stored approved backstory.',\n"
                    "            body=3,\n"
                    "            agility=4,\n"
                    "            reaction=4,\n"
                    "            strength=2,\n"
                    "            willpower=3,\n"
                    "            logic=3,\n"
                    "            intuition=4,\n"
                    "            charisma=2,\n"
                    "            edge=2,\n"
                    "            essence=Decimal('5.50'),\n"
                    "            magic=0,\n"
                    "            resonance=0,\n"
                    "        )\n"
                    "except IntegrityError:\n"
                    "    print('rejected')\n"
                ),
            ],
            cwd=PRODUCT_ROOT,
            env=self.merged_env({"PYTHONPATH": PYTHONPATH_DIR}),
            check=False,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "rejected")
        self.assertEqual(result.stderr, "")

    def test_clean_install_rejects_blank_approved_backstory(self) -> None:
        game_dir = create_initialized_game_dir()

        result = subprocess.run(
            [
                PYTHON_BIN,
                "-c",
                (
                    "from pathlib import Path\n"
                    "from decimal import Decimal\n"
                    "from redmond_server.bootstrap._env import "
                    "configure_django\n"
                    "configure_django(Path(r'"
                    + str(game_dir)
                    + "'), load_evennia=True)\n"
                    "import evennia\n"
                    "from django.conf import settings\n"
                    "from django.db import IntegrityError, transaction\n"
                    "from sheets.models import CharacterSheet, "
                    "CharacterSheetStatus\n"
                    "room = evennia.search_object('#2')[0]\n"
                    "character = evennia.create_object(\n"
                    "    typeclass=settings.BASE_CHARACTER_TYPECLASS,\n"
                    "    key='SheetBackstoryCheck',\n"
                    "    location=room,\n"
                    "    home=room,\n"
                    ")\n"
                    "try:\n"
                    "    with transaction.atomic():\n"
                    "        CharacterSheet.objects.create(\n"
                    "            character=character,\n"
                    "            status=CharacterSheetStatus.APPROVED,\n"
                    "            alias='Ghost',\n"
                    "            pronouns='they/them',\n"
                    "            metatype='Human',\n"
                    "            archetype_label='Runner',\n"
                    "            short_concept='Observant scout',\n"
                    "            backstory='\\n\\n',\n"
                    "            body=3,\n"
                    "            agility=4,\n"
                    "            reaction=4,\n"
                    "            strength=2,\n"
                    "            willpower=3,\n"
                    "            logic=3,\n"
                    "            intuition=4,\n"
                    "            charisma=2,\n"
                    "            edge=2,\n"
                    "            essence=Decimal('5.50'),\n"
                    "            magic=0,\n"
                    "            resonance=0,\n"
                    "        )\n"
                    "except IntegrityError:\n"
                    "    print('rejected')\n"
                ),
            ],
            cwd=PRODUCT_ROOT,
            env=self.merged_env({"PYTHONPATH": PYTHONPATH_DIR}),
            check=False,
            text=True,
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "rejected")
        self.assertEqual(result.stderr, "")

    def test_sheet_create_sample_missing_character_is_structured(self) -> None:
        game_dir = create_initialized_game_dir()

        result = subprocess.run(
            [
                PYTHON_BIN,
                "-m",
                "redmond_server.bootstrap",
                "sheet-create-sample",
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
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["code"], "character_not_found")
        self.assertIn("Character not found", payload["message"])

    def test_sheet_create_sample_ambiguous_character_is_structured(
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
                    "key='SampleChar', location=room, home=room); "
                    "evennia.create_object("
                    "typeclass=settings.BASE_CHARACTER_TYPECLASS, "
                    "key='SampleChar', location=room, home=room)"
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
                "sheet-create-sample",
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
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["code"], "character_name_ambiguous")
        self.assertIn("ambiguous", payload["message"])
