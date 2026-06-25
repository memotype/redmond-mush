from __future__ import annotations
# ruff: noqa: E402

from pathlib import Path
import os
from tempfile import TemporaryDirectory
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

from server.conf import connection_screens


class ConnectionScreenTest(unittest.TestCase):
    def test_load_title_cards_reads_non_empty_text_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            title_card_dir = Path(temp_dir)
            (title_card_dir / "a.txt").write_text(
                "|gAlpha|n\n",
                encoding="ascii",
            )
            (title_card_dir / "b.txt").write_text(
                "\n|bBeta|n\n",
                encoding="ascii",
            )
            (title_card_dir / "empty.txt").write_text(
                "\n",
                encoding="ascii",
            )
            (title_card_dir / "skip.md").write_text(
                "|rSkip|n",
                encoding="ascii",
            )

            self.assertEqual(
                connection_screens.load_title_cards(title_card_dir),
                ["|gAlpha|n", "|bBeta|n"],
            )

    def test_choose_title_card_falls_back_when_directory_missing(self) -> None:
        with patch.object(
            connection_screens,
            "TITLE_CARD_DIR",
            Path("/does/not/exist"),
        ):
            self.assertEqual(
                connection_screens.choose_title_card(),
                connection_screens.DEFAULT_TITLE_CARD,
            )

    def test_unloggedin_look_uses_connection_screen_title_card(self) -> None:
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

        with patch.object(
            connection_screens,
            "choose_title_card",
            return_value="|gTITLE|n",
        ):
            self.assertFalse(cmd.at_pre_cmd())
            cmd.parse()
            cmd.func()
            cmd.at_post_cmd()

        screen_call = session.msg.mock_calls[0]
        prompt_call = session.msg.mock_calls[-1]
        self.assertIn("|gTITLE|n", screen_call.kwargs["text"])
        self.assertIn(
            "connect <username> <password>",
            screen_call.kwargs["text"],
        )
        self.assertIn(
            "Type |whelp|n for more info.",
            screen_call.kwargs["text"],
        )
        self.assertEqual(prompt_call.kwargs["prompt"], "\nRedmond> ")
