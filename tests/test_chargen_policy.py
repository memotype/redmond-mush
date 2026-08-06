from __future__ import annotations

import unittest

from redmond_server.game.chargen.policy import (
    backstory_completion_state,
    draft_attributes_completion_state,
    normalize_draft_attribute_name,
    validate_draft_attribute_name,
    validate_draft_attribute_value,
    normalize_profile_key,
    session_state_is_active,
    validate_default_profile_flags,
    validate_display_name,
    validate_positive_int,
    validate_profile_key,
)


class ChargenPolicyTest(unittest.TestCase):
    def test_session_state_active_membership(self) -> None:
        self.assertTrue(session_state_is_active("draft"))
        self.assertTrue(session_state_is_active("submitted"))
        self.assertFalse(session_state_is_active("approved"))

    def test_profile_key_normalization_and_validation(self) -> None:
        self.assertEqual(normalize_profile_key("  Redmond_Standard  "),
                         "redmond_standard")
        self.assertEqual(validate_profile_key("profile_key", "redmond_1"), [])
        self.assertEqual(
            validate_profile_key("profile_key", "Bad Key")[0].code,
            "invalid_format",
        )

    def test_starting_karma_validation(self) -> None:
        self.assertEqual(validate_positive_int("starting_karma", 0), [])
        self.assertEqual(
            validate_positive_int("starting_karma", -1)[0].code,
            "too_small",
        )
        self.assertEqual(
            validate_positive_int("starting_karma", False)[0].code,
            "invalid_type",
        )

    def test_backstory_completion_state(self) -> None:
        self.assertEqual(backstory_completion_state(""), "Required")
        self.assertEqual(backstory_completion_state("\n\n"), "Required")
        self.assertEqual(
            backstory_completion_state("Alpha\r\n\r\nBeta\n"),
            "Complete",
        )

    def test_default_profile_must_remain_available(self) -> None:
        issues = validate_default_profile_flags(
            is_available_for_new_sessions=False,
            is_default_for_new_sessions=True,
        )
        self.assertEqual(issues[0].code, "default_requires_available")

    def test_display_name_is_required(self) -> None:
        self.assertEqual(validate_display_name("Redmond Standard"), [])
        self.assertEqual(validate_display_name("   ")[0].code, "required")

    def test_draft_attribute_name_normalization_and_validation(self) -> None:
        self.assertEqual(normalize_draft_attribute_name("  bod "), "body")
        self.assertEqual(normalize_draft_attribute_name("edge"), "edge")
        self.assertEqual(
            validate_draft_attribute_name("attribute_name", "agi"),
            [],
        )
        self.assertEqual(
            validate_draft_attribute_name(
                "attribute_name",
                "luck",
            )[0].code,
            "unknown_attribute",
        )

    def test_draft_attribute_value_validation(self) -> None:
        self.assertEqual(validate_draft_attribute_value("value", 0), [])
        self.assertEqual(validate_draft_attribute_value("value", 99), [])
        self.assertEqual(
            validate_draft_attribute_value("value", -1)[0].code,
            "too_small",
        )
        self.assertEqual(
            validate_draft_attribute_value("value", 100)[0].code,
            "too_large",
        )
        self.assertEqual(
            validate_draft_attribute_value("value", False)[0].code,
            "invalid_type",
        )

    def test_draft_attributes_completion_state(self) -> None:
        partial = {
            "body": 1,
            "agility": 2,
            "reaction": 3,
            "strength": 4,
            "willpower": 5,
            "logic": 6,
            "intuition": 7,
            "charisma": None,
            "edge": 1,
        }
        self.assertEqual(
            draft_attributes_completion_state(partial),
            "Incomplete",
        )
        complete = {key: 1 for key in partial}
        self.assertEqual(
            draft_attributes_completion_state(complete),
            "Complete",
        )
