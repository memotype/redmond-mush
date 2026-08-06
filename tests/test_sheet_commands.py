from __future__ import annotations
# ruff: noqa: E402

from unittest.mock import patch

from tests.bootstrap_test_utils import configure_isolated_django


configure_isolated_django()

from evennia.utils.test_resources import EvenniaCommandTest

from commands.sheet import CmdSheet
from commands.default_cmdsets import CharacterCmdSet
from sheets.models import CharacterSheetStatus
from sheets.models import CharacterSheet
from sheets.services import (
    ApprovedSheetCreateInput,
    ApprovedSkillInput,
    create_approved_sheet,
)


class SheetCommandTest(EvenniaCommandTest):
    def setUp(self) -> None:
        super().setUp()
        create_approved_sheet(
            ApprovedSheetCreateInput(
                character=self.char1,
                alias="Ghost",
                pronouns="they/them",
                metatype="Human",
                archetype_label="Runner",
                short_concept="Observant scout",
                backstory="Stored approved backstory.",
                body=3,
                agility=4,
                reaction=4,
                strength=2,
                willpower=3,
                logic=3,
                intuition=4,
                charisma=2,
                edge=2,
                essence="5.50",
                magic=0,
                resonance=0,
                skills=(
                    ApprovedSkillInput("athletics", 3),
                    ApprovedSkillInput("perception", 4),
                ),
            )
        )

    def test_sheet_command_renders_approved_sheet(self) -> None:
        output = self.call(
            CmdSheet(),
            "",
            msg=None,
            raw_string="+sheet",
        )
        self.assertIn("Char Sheet", output)
        self.assertIn("Alias: Ghost", output)
        self.assertIn("Essence: 5.50", output)
        self.assertIn("Athletics: 3", output)
        self.assertIn("Backstory: Available", output)

    def test_sheet_command_renders_missing_sheet_cleanly(self) -> None:
        self.char1.redmond_sheet.delete()
        output = self.call(
            CmdSheet(),
            "",
            msg=None,
            raw_string="+sheet",
        )
        self.assertIn(
            "This character does not have an approved sheet.",
            output,
        )

    def test_sheet_backstory_command_renders_exact_backstory(self) -> None:
        output = self.call(
            CmdSheet(),
            "/backstory",
            msg=None,
            raw_string="+sheet/backstory",
        )
        self.assertIn("Char Backstory", output)
        self.assertIn("Stored approved backstory.", output)

    def test_sheet_backstory_command_handles_missing_sheet(self) -> None:
        self.char1.redmond_sheet.delete()
        output = self.call(
            CmdSheet(),
            "/backstory",
            msg=None,
            raw_string="+sheet/backstory",
        )
        self.assertIn(
            "This character does not have an approved sheet.",
            output,
        )

    def test_sheet_command_hides_retired_sheet(self) -> None:
        approved = self.char1.redmond_sheet
        approved.delete()
        CharacterSheet.objects.create(
            character=self.char1,
            status=CharacterSheetStatus.RETIRED,
            alias="Ghost",
            pronouns="they/them",
            metatype="Human",
            archetype_label="Runner",
            short_concept="Observant scout",
            backstory="Stored approved backstory.",
            body=3,
            agility=4,
            reaction=4,
            strength=2,
            willpower=3,
            logic=3,
            intuition=4,
            charisma=2,
            edge=2,
            essence="5.50",
            magic=0,
            resonance=0,
        )
        output = self.call(
            CmdSheet(),
            "",
            msg=None,
            raw_string="+sheet",
        )
        self.assertIn(
            "This character does not have an approved sheet.",
            output,
        )

    def test_sheet_backstory_hides_archived_sheet(self) -> None:
        approved = self.char1.redmond_sheet
        approved.delete()
        CharacterSheet.objects.create(
            character=self.char1,
            status=CharacterSheetStatus.ARCHIVED,
            alias="Ghost",
            pronouns="they/them",
            metatype="Human",
            archetype_label="Runner",
            short_concept="Observant scout",
            backstory="Stored approved backstory.",
            body=3,
            agility=4,
            reaction=4,
            strength=2,
            willpower=3,
            logic=3,
            intuition=4,
            charisma=2,
            edge=2,
            essence="5.50",
            magic=0,
            resonance=0,
        )
        output = self.call(
            CmdSheet(),
            "/backstory",
            msg=None,
            raw_string="+sheet/backstory",
        )
        self.assertIn(
            "This character does not have an approved sheet.",
            output,
        )

    def test_sheet_command_uses_presentation_formatter(self) -> None:
        with patch(
            "commands.sheet.render_sheet",
            return_value="formatted sheet",
        ) as render_sheet:
            output = self.call(
                CmdSheet(),
                "",
                msg=None,
                raw_string="+sheet",
            )
        render_sheet.assert_called_once()
        self.assertIn("formatted sheet", output)

    def test_sheet_backstory_command_uses_presentation_formatter(self) -> None:
        with patch(
            "commands.sheet.render_sheet_backstory",
            return_value="formatted backstory",
        ) as render_sheet_backstory:
            output = self.call(
                CmdSheet(),
                "/backstory",
                msg=None,
                raw_string="+sheet/backstory",
            )
        render_sheet_backstory.assert_called_once()
        self.assertIn("formatted backstory", output)

    def test_character_cmdset_wires_sheet_command(self) -> None:
        cmdset = CharacterCmdSet()
        cmdset.at_cmdset_creation()
        keys = {command.key for command in cmdset.commands}
        self.assertIn("+sheet", keys)
