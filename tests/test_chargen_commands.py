from __future__ import annotations
# ruff: noqa: E402

from pathlib import Path
import os
from unittest.mock import patch

from redmond_server.bootstrap._backup import run_migrations
from redmond_server.bootstrap._env import configure_django


GAME_DIR = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "redmond_server"
    / "game"
)
ORIGINAL_CWD = Path.cwd()
configure_django(GAME_DIR, load_evennia=True)
os.chdir(ORIGINAL_CWD)
run_migrations(GAME_DIR)

from evennia.utils.test_resources import EvenniaCommandTest

from chargen.services import (
    CreateChargenSessionInput,
    EnsureChargenRulesProfileInput,
    create_chargen_session,
    ensure_chargen_rules_profile,
)
from commands.chargen import CmdChargen
from commands.default_cmdsets import CharacterCmdSet


class ChargenCommandTest(EvenniaCommandTest):
    def setUp(self) -> None:
        super().setUp()
        ensure_chargen_rules_profile(
            EnsureChargenRulesProfileInput(
                profile_key="redmond_standard",
                version=1,
                display_name="Redmond Standard",
                is_available_for_new_sessions=True,
                is_default_for_new_sessions=True,
                starting_karma=50,
            )
        )

    def test_chargen_help_renders_for_bare_command(self) -> None:
        output = self.call(
            CmdChargen(),
            "",
            msg=None,
            raw_string="+chargen",
        )
        self.assertIn("Chargen Commands", output)
        self.assertIn("+chargen/status", output)

    def test_chargen_help_switch_renders_help(self) -> None:
        output = self.call(
            CmdChargen(),
            "/help",
            msg=None,
            raw_string="+chargen/help",
        )
        self.assertIn("Writable chargen commands", output)

    def test_chargen_status_handles_missing_session(self) -> None:
        output = self.call(
            CmdChargen(),
            "/status",
            msg=None,
            raw_string="+chargen/status",
        )
        self.assertIn(
            "This character does not have an active chargen session.",
            output,
        )

    def test_chargen_status_renders_active_session(self) -> None:
        create_chargen_session(CreateChargenSessionInput(character=self.char1))
        output = self.call(
            CmdChargen(),
            "/status",
            msg=None,
            raw_string="+chargen/status",
        )
        self.assertIn("Char Chargen Status", output)
        self.assertIn("Rules Profile: Redmond Standard", output)
        self.assertIn("Starting Karma: 50", output)
        self.assertIn("Backstory: Required", output)

    def test_chargen_status_uses_presentation_formatter(self) -> None:
        create_chargen_session(CreateChargenSessionInput(character=self.char1))
        with patch(
            "commands.chargen.render_chargen_status",
            return_value="formatted chargen",
        ) as render_chargen_status:
            output = self.call(
                CmdChargen(),
                "/status",
                msg=None,
                raw_string="+chargen/status",
            )
        render_chargen_status.assert_called_once()
        self.assertIn("formatted chargen", output)

    def test_character_cmdset_wires_chargen_command(self) -> None:
        cmdset = CharacterCmdSet()
        cmdset.at_cmdset_creation()
        keys = {command.key for command in cmdset.commands}
        self.assertIn("+chargen", keys)
