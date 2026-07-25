from __future__ import annotations
# ruff: noqa: E402

from decimal import Decimal
from pathlib import Path
import os
from unittest.mock import patch

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

from django.db import IntegrityError, transaction  # type: ignore[import-untyped]
from evennia.utils.test_resources import EvenniaCommandTest

from sheets.models import CharacterSheet, CharacterSkill
from sheets.models import CharacterSheetStatus
from sheets.queries import get_sheet_backstory_view, get_sheet_view
from sheets.services import (
    ApprovedSheetCreateInput,
    ApprovedSkillInput,
    SheetAlreadyExistsError,
    SheetConflictError,
    SheetValidationError,
    create_approved_sheet,
)
from sheets.policy import (
    ATTRIBUTE_MAX_VALUE,
    SHEET_ALIAS_MAX_LENGTH,
    SKILL_ID_MAX_LENGTH,
)


class SheetServiceTest(EvenniaCommandTest):
    def _make_input(
        self,
        *,
        backstory: str = "Alpha\r\n\r\nBeta\n",
        skills: tuple[ApprovedSkillInput, ...] = (
            ApprovedSkillInput("perception", 4),
            ApprovedSkillInput("athletics", 3),
        ),
        **overrides,
    ) -> ApprovedSheetCreateInput:
        payload = ApprovedSheetCreateInput(
            character=self.char1,
            alias="Ghost",
            pronouns="they/them",
            metatype="Human",
            archetype_label="Runner",
            short_concept="Observant scout",
            backstory=backstory,
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
            skills=skills,
        )
        return ApprovedSheetCreateInput(
            **{**payload.__dict__, **overrides}
        )

    def test_create_approved_sheet_persists_full_round_trip(self) -> None:
        result = create_approved_sheet(self._make_input())

        sheet = CharacterSheet.objects.get(pk=result.sheet_id)
        self.assertEqual(result.character_id, self.char1.pk)
        self.assertEqual(result.skill_count, 2)
        self.assertEqual(sheet.backstory, "Alpha\n\nBeta")
        self.assertEqual(sheet.alias, "Ghost")
        self.assertEqual(sheet.essence, Decimal("5.50"))
        self.assertEqual(sheet.magic, 0)
        self.assertEqual(sheet.resonance, 0)

    def test_service_explicitly_creates_approved_status(self) -> None:
        result = create_approved_sheet(self._make_input())
        sheet = CharacterSheet.objects.get(pk=result.sheet_id)
        self.assertEqual(result.status, CharacterSheetStatus.APPROVED)
        self.assertEqual(sheet.status, CharacterSheetStatus.APPROVED)

    def test_create_approved_sheet_rejects_duplicate_sheet(self) -> None:
        create_approved_sheet(self._make_input())
        with self.assertRaises(SheetAlreadyExistsError):
            create_approved_sheet(self._make_input())

    def test_duplicate_skill_input_rejects_without_sheet(self) -> None:
        with self.assertRaises(SheetValidationError):
            create_approved_sheet(
                self._make_input(
                    skills=(
                        ApprovedSkillInput("athletics", 3),
                        ApprovedSkillInput("Athletics", 4),
                    )
                )
            )
        self.assertFalse(CharacterSheet.objects.exists())

    def test_invalid_attribute_failures_return_structured_issues(self) -> None:
        for raw_value, expected_code in (
            (-1, "too_small"),
            (ATTRIBUTE_MAX_VALUE + 1, "too_large"),
            (2.5, "invalid_type"),
        ):
            with self.subTest(raw_value=raw_value):
                with self.assertRaises(SheetValidationError) as raised:
                    create_approved_sheet(
                        self._make_input(body=raw_value)  # type: ignore[arg-type]
                    )
                self.assertEqual(raised.exception.issues[0].field, "body")
                self.assertEqual(raised.exception.issues[0].code, expected_code)

    def test_invalid_skill_rating_failures_return_structured_issues(self) -> None:
        for raw_value, expected_code in (
            (0, "too_small"),
            (-1, "too_small"),
            (2.5, "invalid_type"),
        ):
            with self.subTest(raw_value=raw_value):
                with self.assertRaises(SheetValidationError) as raised:
                    create_approved_sheet(
                        self._make_input(
                            skills=(
                                ApprovedSkillInput(
                                    "athletics",
                                    raw_value,  # type: ignore[arg-type]
                                ),
                            )
                        )
                    )
                self.assertEqual(
                    raised.exception.issues[0].field,
                    "skills[0].rating",
                )
                self.assertEqual(
                    raised.exception.issues[0].code,
                    expected_code,
                )

    def test_invalid_essence_failures_return_structured_issues(self) -> None:
        for raw_value, expected_code in (
            ("nope", "invalid_format"),
            ("-0.01", "too_small"),
            ("NaN", "non_finite"),
            ("Infinity", "non_finite"),
            ("100.00", "too_large"),
        ):
            with self.subTest(raw_value=raw_value):
                with self.assertRaises(SheetValidationError) as raised:
                    create_approved_sheet(self._make_input(essence=raw_value))
                self.assertEqual(raised.exception.issues[0].field, "essence")
                self.assertEqual(
                    raised.exception.issues[0].code,
                    expected_code,
                )

    def test_metadata_length_failures_return_structured_issues(self) -> None:
        with self.assertRaises(SheetValidationError) as raised:
            create_approved_sheet(
                self._make_input(
                    alias="x" * (SHEET_ALIAS_MAX_LENGTH + 1),
                )
            )
        self.assertEqual(raised.exception.issues[0].field, "alias")
        self.assertEqual(raised.exception.issues[0].code, "too_long")

    def test_skill_identifier_validation_uses_canonical_policy(self) -> None:
        with self.assertRaises(SheetValidationError) as raised:
            create_approved_sheet(
                self._make_input(
                    skills=(
                        ApprovedSkillInput("athletics!", 3),
                    )
                )
            )
        self.assertEqual(
            raised.exception.issues[0].field,
            "skills[0].skill_id",
        )
        self.assertEqual(
            raised.exception.issues[0].code,
            "invalid_format",
        )

    def test_skill_identifier_max_length_is_enforced(self) -> None:
        with self.assertRaises(SheetValidationError) as raised:
            create_approved_sheet(
                self._make_input(
                    skills=(
                        ApprovedSkillInput(
                            "a" * (SKILL_ID_MAX_LENGTH + 1),
                            3,
                        ),
                    )
                )
            )
        self.assertEqual(
            raised.exception.issues[0].code,
            "too_long",
        )

    def test_bulk_create_failure_rolls_back_sheet(self) -> None:
        with patch(
            "sheets.services.CharacterSkill.objects.bulk_create",
            side_effect=IntegrityError("boom"),
        ):
            with self.assertRaises(SheetConflictError):
                create_approved_sheet(self._make_input())
        self.assertFalse(CharacterSheet.objects.exists())

    def test_optional_metadata_may_be_blank(self) -> None:
        create_approved_sheet(
            ApprovedSheetCreateInput(
                character=self.char1,
                backstory="Valid approved backstory.",
                body=1,
                agility=1,
                reaction=1,
                strength=1,
                willpower=1,
                logic=1,
                intuition=1,
                charisma=1,
                edge=1,
                essence="6.00",
                magic=0,
                resonance=0,
                skills=(),
            )
        )

        sheet = CharacterSheet.objects.get(character=self.char1)
        self.assertEqual(sheet.alias, "")
        self.assertEqual(sheet.pronouns, "")
        self.assertEqual(sheet.metatype, "")

    def test_get_sheet_view_returns_none_when_missing(self) -> None:
        self.assertIsNone(get_sheet_view(self.char1))
        self.assertIsNone(get_sheet_backstory_view(self.char1))

    def test_retired_sheet_is_hidden_from_self_view_queries(self) -> None:
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
            essence=Decimal("5.50"),
            magic=0,
            resonance=0,
        )
        self.assertIsNone(get_sheet_view(self.char1))
        self.assertIsNone(get_sheet_backstory_view(self.char1))

    def test_archived_sheet_is_hidden_from_self_view_queries(self) -> None:
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
            essence=Decimal("5.50"),
            magic=0,
            resonance=0,
        )
        self.assertIsNone(get_sheet_view(self.char1))
        self.assertIsNone(get_sheet_backstory_view(self.char1))

    def test_query_results_order_skills_and_structure_results(self) -> None:
        create_approved_sheet(self._make_input())

        sheet_view = get_sheet_view(self.char1)
        assert sheet_view is not None
        backstory_view = get_sheet_backstory_view(self.char1)
        assert backstory_view is not None

        self.assertEqual([item.label for item in sheet_view.attributes], [
            "BOD",
            "AGI",
            "REA",
            "STR",
            "WIL",
            "LOG",
            "INT",
            "CHA",
            "EDG",
        ])
        self.assertEqual(
            [item.skill_id for item in sheet_view.skills],
            ["athletics", "perception"],
        )
        self.assertTrue(sheet_view.has_backstory)
        self.assertEqual(backstory_view.backstory, "Alpha\n\nBeta")

    def test_skill_rows_use_unique_constraint(self) -> None:
        create_approved_sheet(self._make_input())
        sheet = CharacterSheet.objects.get(character=self.char1)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CharacterSkill.objects.create(
                    sheet=sheet,
                    skill_id="athletics",
                    rating=2,
                )
