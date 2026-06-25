from __future__ import annotations
# ruff: noqa: E402

from pathlib import Path
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

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

from evennia.commands.default.unloggedin import CmdUnconnectedLook
from evennia.utils.test_resources import EvenniaCommandTest

from commands.command import MuxCommand
from commands.prompt import CmdPrompt
from typeclasses.accounts import Account
from world.game_text import LOGIN_MOTD
from world.prompts import (
    ACCOUNT_PROMPT_ATTR,
    DEFAULT_LOGGED_IN_PROMPT,
    DEFAULT_UNLOGGED_IN_PROMPT,
    OOC_CONTEXT_LABEL,
    PromptContext,
    build_prompt_context,
    build_prompt_text,
    render_prompt_template,
)


class CmdNoop(MuxCommand):
    """Simple command used to exercise post-command prompt emission."""

    key = "noop"

    def func(self):
        """Emit a normal line before prompt emission."""
        self.caller.msg("OK")


class PromptRendererTest(unittest.TestCase):
    def test_default_unlogged_prompt_renders(self) -> None:
        context = PromptContext(
            account_name="",
            character_name=None,
            context_label=OOC_CONTEXT_LABEL,
            logged_in=False,
        )
        self.assertEqual(
            render_prompt_template(DEFAULT_UNLOGGED_IN_PROMPT, context),
            "\nRedmond> ",
        )

    def test_default_logged_in_ooc_prompt_uses_account_name(self) -> None:
        context = PromptContext(
            account_name="Nyx",
            character_name=None,
            context_label=OOC_CONTEXT_LABEL,
            logged_in=True,
        )
        self.assertEqual(
            render_prompt_template(DEFAULT_LOGGED_IN_PROMPT, context),
            "\nNyx @ OOC > ",
        )

    def test_default_logged_in_ic_prompt_uses_character_and_room(self) -> None:
        context = PromptContext(
            account_name="NyxAcct",
            character_name="Nyx",
            context_label="Dante's Inferno",
            logged_in=True,
        )
        self.assertEqual(
            render_prompt_template(DEFAULT_LOGGED_IN_PROMPT, context),
            "\nNyx @ Dante's Inferno > ",
        )

    def test_control_tokens_and_literal_percent_render(self) -> None:
        context = PromptContext(
            account_name="Nyx",
            character_name=None,
            context_label=OOC_CONTEXT_LABEL,
            logged_in=True,
        )
        self.assertEqual(
            render_prompt_template("%n%t%%done%r> ", context),
            "Nyx\t%done\n> ",
        )

    def test_unknown_tokens_stay_literal(self) -> None:
        context = PromptContext(
            account_name="Nyx",
            character_name=None,
            context_label=OOC_CONTEXT_LABEL,
            logged_in=True,
        )
        self.assertEqual(render_prompt_template("%x %q", context), "%x %q")

    def test_trailing_spaces_are_preserved(self) -> None:
        context = PromptContext(
            account_name="Nyx",
            character_name=None,
            context_label=OOC_CONTEXT_LABEL,
            logged_in=True,
        )
        self.assertEqual(render_prompt_template("%n >  ", context), "Nyx >  ")


class PromptEvenniaTest(EvenniaCommandTest):
    def test_build_prompt_context_for_unlogged_session(self) -> None:
        session = SimpleNamespace(account=None, puppet=None)
        context = build_prompt_context(session)
        self.assertFalse(context.logged_in)
        self.assertEqual(context.context_label, OOC_CONTEXT_LABEL)

    def test_build_prompt_context_for_logged_in_ooc_session(self) -> None:
        self.account.unpuppet_object(self.session)
        context = build_prompt_context(self.session)
        self.assertTrue(context.logged_in)
        self.assertEqual(context.account_name, self.account.key)
        self.assertIsNone(context.character_name)
        self.assertEqual(context.context_label, OOC_CONTEXT_LABEL)

    def test_build_prompt_context_for_puppeted_character(self) -> None:
        context = build_prompt_context(self.session)
        self.assertTrue(context.logged_in)
        self.assertEqual(context.account_name, self.account.key)
        self.assertEqual(context.character_name, self.char1.key)
        self.assertEqual(context.context_label, self.room1.key)

    def test_prompt_command_shows_current_template(self) -> None:
        output = self.call(
            CmdPrompt(),
            "",
            msg=None,
            caller=self.account,
            raw_string="@prompt",
        )
        self.assertIn("Saved override: no", output)
        self.assertIn("Template: '%r%n @ %l > '", output)

    def test_prompt_command_saves_template_with_trailing_space(self) -> None:
        output = self.call(
            CmdPrompt(),
            "%n >  ",
            msg=None,
            caller=self.account,
            raw_string="@prompt %n >  ",
        )
        self.assertIn("Prompt updated.", output)
        self.assertEqual(
            self.account.attributes.get(ACCOUNT_PROMPT_ATTR),
            "%n >  ",
        )

    def test_prompt_command_previews_without_saving(self) -> None:
        output = self.call(
            CmdPrompt(),
            "/test %l > ",
            msg=None,
            caller=self.account,
            raw_string="@prompt/test %l > ",
        )
        self.assertIn("Prompt preview only; no changes were saved.", output)
        self.assertFalse(self.account.attributes.has(ACCOUNT_PROMPT_ATTR))

    def test_prompt_command_resets_to_default(self) -> None:
        self.account.attributes.add(ACCOUNT_PROMPT_ATTR, "%n >  ")
        output = self.call(
            CmdPrompt(),
            "/reset",
            msg=None,
            caller=self.account,
            raw_string="@prompt/reset",
        )
        self.assertIn("Prompt reset to the default logged-in template.", output)
        self.assertFalse(self.account.attributes.has(ACCOUNT_PROMPT_ATTR))

    def test_logged_in_command_emits_real_prompt(self) -> None:
        output = self.call(CmdNoop(), "", msg=None)
        expected = "\\nChar @ Room > "
        self.assertIn("'prompt': '" + expected + "'", output)

    def test_unloggedin_look_emits_unlogged_prompt(self) -> None:
        session = SimpleNamespace(msg=Mock(), account=None, puppet=None)
        cmd = CmdUnconnectedLook()
        cmd.caller = session
        cmd.session = session
        cmd.account = None
        cmd.args = ""
        cmd.cmdname = cmd.key
        cmd.raw_cmdname = cmd.key
        cmd.cmdstring = cmd.key
        cmd.raw_string = cmd.key
        cmd.obj = session
        self.assertFalse(cmd.at_pre_cmd())
        cmd.parse()
        cmd.func()
        cmd.at_post_cmd()
        prompt_call = session.msg.mock_calls[-1]
        self.assertEqual(prompt_call.kwargs["prompt"], "\nRedmond> ")

    def test_account_post_login_sends_motd_then_prompt(self) -> None:
        fake_session = SimpleNamespace(account=self.account, puppet=self.char1)
        self.account.msg = Mock()
        with patch(
            "evennia.accounts.accounts.DefaultAccount.at_post_login",
            return_value=None,
        ):
            Account.at_post_login(self.account, session=fake_session)
        first_call = self.account.msg.mock_calls[0]
        second_call = self.account.msg.mock_calls[1]
        self.assertEqual(first_call.args[0], LOGIN_MOTD)
        self.assertEqual(second_call.kwargs["prompt"], "\nChar @ Room > ")

    def test_build_prompt_text_uses_ooc_fallback_when_unpuppeted(self) -> None:
        self.account.unpuppet_object(self.session)
        self.assertEqual(
            build_prompt_text(self.session, account=self.account),
            "\nTestAccount @ OOC > ",
        )
