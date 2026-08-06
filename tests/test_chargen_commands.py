from __future__ import annotations
# ruff: noqa: E402

from unittest.mock import patch

from tests.bootstrap_test_utils import configure_isolated_django


configure_isolated_django()

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
        self.assertIn("+chargen/start", output)
        self.assertIn("+chargen/status", output)
        self.assertIn("+chargen/show", output)
        self.assertIn("+chargen/edit attr", output)

    def test_chargen_help_switch_renders_help(self) -> None:
        output = self.call(
            CmdChargen(),
            "/help",
            msg=None,
            raw_string="+chargen/help",
        )
        self.assertIn("+chargen/show background", output)

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
        self.assertIn("+chargen/start", output)

    def test_chargen_status_renders_active_session(self) -> None:
        create_chargen_session(CreateChargenSessionInput(character=self.char1))
        output = self.call(
            CmdChargen(),
            "/status",
            msg=None,
            raw_string="+chargen/status",
        )
        self.assertIn("Char Chargen Status", output)
        self.assertIn("Completion: Incomplete", output)
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

    def test_chargen_show_renders_default_summary(self) -> None:
        create_chargen_session(CreateChargenSessionInput(character=self.char1))
        output = self.call(
            CmdChargen(),
            "/show",
            msg=None,
            raw_string="+chargen/show",
        )
        self.assertIn("Char Chargen Draft", output)
        self.assertIn("Attributes:", output)

    def test_chargen_show_attr_renders_attribute_view(self) -> None:
        create_chargen_session(CreateChargenSessionInput(character=self.char1))
        output = self.call(
            CmdChargen(),
            "/show attr",
            msg=None,
            raw_string="+chargen/show attr",
        )
        self.assertIn("Char Chargen Attributes", output)
        self.assertIn("Body: --", output)
        self.assertIn("Edge: --", output)

    def test_chargen_show_background_renders_draft_backstory(self) -> None:
        created = create_chargen_session(
            CreateChargenSessionInput(character=self.char1)
        )
        session = self.char1.redmond_chargen_sessions.get(pk=created.session_id)
        session.backstory = "Stored draft backstory."
        session.save(update_fields=["backstory", "updated_at"])
        output = self.call(
            CmdChargen(),
            "/show background",
            msg=None,
            raw_string="+chargen/show background",
        )
        self.assertIn("Stored draft backstory.", output)

    def test_chargen_show_bg_alias_renders_background(self) -> None:
        create_chargen_session(CreateChargenSessionInput(character=self.char1))
        output = self.call(
            CmdChargen(),
            "/show bg",
            msg=None,
            raw_string="+chargen/show bg",
        )
        self.assertIn("No draft backstory is set.", output)

    def test_chargen_edit_attr_updates_primary_attribute(self) -> None:
        create_chargen_session(CreateChargenSessionInput(character=self.char1))
        output = self.call(
            CmdChargen(),
            "/edit attr bod 8",
            msg=None,
            raw_string="+chargen/edit attr bod 8",
        )
        self.assertIn("Body set to 8.", output)
        session = self.char1.redmond_chargen_sessions.get()
        self.assertEqual(session.body, 8)

    def test_chargen_edit_attr_rejects_invalid_usage(self) -> None:
        create_chargen_session(CreateChargenSessionInput(character=self.char1))
        output = self.call(
            CmdChargen(),
            "/edit attr bod",
            msg=None,
            raw_string="+chargen/edit attr bod",
        )
        self.assertIn("Usage: +chargen/edit attr <attribute> <value>", output)

    def test_chargen_start_creates_session(self) -> None:
        output = self.call(
            CmdChargen(),
            "/start",
            msg=None,
            raw_string="+chargen/start",
        )
        self.assertIn("Chargen session started.", output)
        self.assertTrue(self.char1.redmond_chargen_sessions.exists())

    def test_chargen_start_handles_existing_session(self) -> None:
        create_chargen_session(CreateChargenSessionInput(character=self.char1))
        output = self.call(
            CmdChargen(),
            "/start",
            msg=None,
            raw_string="+chargen/start",
        )
        self.assertIn("already has an active chargen session", output)

    def test_chargen_start_rejects_extra_args(self) -> None:
        output = self.call(
            CmdChargen(),
            "/start now",
            msg=None,
            raw_string="+chargen/start now",
        )
        self.assertIn("Usage: +chargen/start", output)

    def test_character_cmdset_wires_chargen_command(self) -> None:
        cmdset = CharacterCmdSet()
        cmdset.at_cmdset_creation()
        keys = {command.key for command in cmdset.commands}
        self.assertIn("+chargen", keys)
