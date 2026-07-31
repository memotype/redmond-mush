from __future__ import annotations

from decimal import Decimal
import unittest

from redmond_server.game.sheets.policy import (
    APPROVED_BACKSTORY_MAX_CHARS,
    ATTRIBUTE_MAX_VALUE,
    ESSENCE_MAX_VALUE,
    SHEET_ALIAS_MAX_LENGTH,
    SKILL_ID_MAX_LENGTH,
    normalize_backstory,
    validate_bounded_text,
    validate_attribute_rating,
    validate_backstory,
    validate_essence_value,
    validate_skill_id,
    validate_skill_rating,
)


class SheetPolicyTest(unittest.TestCase):
    def test_normalize_backstory_normalizes_line_endings(self) -> None:
        self.assertEqual(
            normalize_backstory("Alpha\r\nBeta\rGamma\n"),
            "Alpha\nBeta\nGamma",
        )

    def test_normalize_backstory_preserves_internal_paragraphs(self) -> None:
        self.assertEqual(
            normalize_backstory("Alpha\n\nBeta\nGamma"),
            "Alpha\n\nBeta\nGamma",
        )

    def test_normalize_backstory_removes_trailing_blank_lines(self) -> None:
        self.assertEqual(
            normalize_backstory("Alpha\n\n\n"),
            "Alpha",
        )

    def test_validate_backstory_rejects_blank_text(self) -> None:
        issues = validate_backstory(normalize_backstory(" \n\t\n"))
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "required")

    def test_validate_backstory_enforces_maximum_length(self) -> None:
        too_long = "a" * (APPROVED_BACKSTORY_MAX_CHARS + 1)
        issues = validate_backstory(too_long)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "too_long")

    def test_validate_attribute_rating_requires_non_negative_int(self) -> None:
        self.assertEqual(validate_attribute_rating("body", 0), [])
        self.assertEqual(
            validate_attribute_rating("body", -1)[0].code,
            "too_small",
        )
        self.assertEqual(
            validate_attribute_rating(
                "body",
                ATTRIBUTE_MAX_VALUE + 1,
            )[0].code,
            "too_large",
        )
        self.assertEqual(
            validate_attribute_rating(
                "body",
                2.5,  # type: ignore[arg-type]
            )[0].code,
            "invalid_type",
        )

    def test_validate_skill_rating_requires_positive_int(self) -> None:
        self.assertEqual(validate_skill_rating("skills[0].rating", 1), [])
        self.assertEqual(
            validate_skill_rating("skills[0].rating", 0)[0].code,
            "too_small",
        )
        self.assertEqual(
            validate_skill_rating(
                "skills[0].rating",
                False,  # type: ignore[arg-type]
            )[0].code,
            "invalid_type",
        )

    def test_validate_essence_value_quantizes_exact_decimal(self) -> None:
        value, issues = validate_essence_value("5.126")
        self.assertEqual(value, Decimal("5.13"))
        self.assertEqual(issues, [])

    def test_validate_essence_value_rejects_negative_or_non_finite(
        self,
    ) -> None:
        for raw_value, expected_code in (
            ("-0.01", "too_small"),
            ("NaN", "non_finite"),
            ("Infinity", "non_finite"),
            ("-Infinity", "non_finite"),
            ("100.00", "too_large"),
            ("abc", "invalid_format"),
        ):
            with self.subTest(raw_value=raw_value):
                value, issues = validate_essence_value(raw_value)
                self.assertIsNone(value)
                self.assertEqual(issues[0].code, expected_code)

    def test_validate_essence_value_enforces_maximum(self) -> None:
        value, issues = validate_essence_value(str(ESSENCE_MAX_VALUE))
        self.assertEqual(value, ESSENCE_MAX_VALUE)
        self.assertEqual(issues, [])
        value, issues = validate_essence_value("99.995")
        self.assertIsNone(value)
        self.assertEqual(issues[0].code, "too_large")

    def test_validate_skill_id_enforces_format_and_length(self) -> None:
        self.assertEqual(validate_skill_id("skill_id", "athletics_1"), [])
        self.assertEqual(
            validate_skill_id("skill_id", "  Athletics_1  "),
            [],
        )
        self.assertEqual(
            validate_skill_id("skill_id", "")[0].code,
            "required",
        )
        self.assertEqual(
            validate_skill_id("skill_id", "athletics!")[0].code,
            "invalid_format",
        )
        self.assertEqual(
            validate_skill_id(
                "skill_id",
                "a" * (SKILL_ID_MAX_LENGTH + 1),
            )[0].code,
            "too_long",
        )

    def test_validate_bounded_text_enforces_metadata_length(self) -> None:
        self.assertEqual(
            validate_bounded_text(
                "alias",
                "Ghost",
                label="alias",
                max_length=SHEET_ALIAS_MAX_LENGTH,
            ),
            [],
        )
        self.assertEqual(
            validate_bounded_text(
                "alias",
                "x" * (SHEET_ALIAS_MAX_LENGTH + 1),
                label="alias",
                max_length=SHEET_ALIAS_MAX_LENGTH,
            )[0].code,
            "too_long",
        )
