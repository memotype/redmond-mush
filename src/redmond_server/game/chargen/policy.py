"""Pure-Python policy for chargen state and validation."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping

from shared_backstory import backstory_has_content


PROFILE_KEY_MAX_LENGTH = 80
PROFILE_DISPLAY_NAME_MAX_LENGTH = 120
SESSION_STATUS_MAX_LENGTH = 24
ATTRIBUTE_MIN_VALUE = 0
ATTRIBUTE_MAX_VALUE = 99
PROFILE_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
ACTIVE_SESSION_STATES = (
    "draft",
    "submitted",
    "changes_requested",
)
FINAL_SESSION_STATES = (
    "approved",
    "abandoned",
    "superseded",
)
ALL_SESSION_STATES = ACTIVE_SESSION_STATES + FINAL_SESSION_STATES


@dataclass(frozen=True)
class ValidationIssue:
    """Structured validation issue for stable service-level reporting."""

    field: str
    code: str
    message: str


@dataclass(frozen=True)
class DraftAttributeDefinition:
    """Stable draft-attribute metadata for chargen commands and views."""

    attribute_id: str
    label: str
    aliases: tuple[str, ...]


def _build_issue(field: str, code: str, message: str) -> ValidationIssue:
    """Create one validation issue."""
    return ValidationIssue(field=field, code=code, message=message)


DRAFT_ATTRIBUTE_DEFINITIONS = (
    DraftAttributeDefinition("body", "Body", ("body", "bod")),
    DraftAttributeDefinition("agility", "Agility", ("agility", "agi")),
    DraftAttributeDefinition("reaction", "Reaction", ("reaction", "rea")),
    DraftAttributeDefinition("strength", "Strength", ("strength", "str")),
    DraftAttributeDefinition(
        "willpower",
        "Willpower",
        ("willpower", "wil"),
    ),
    DraftAttributeDefinition("logic", "Logic", ("logic", "log")),
    DraftAttributeDefinition(
        "intuition",
        "Intuition",
        ("intuition", "int"),
    ),
    DraftAttributeDefinition("charisma", "Charisma", ("charisma", "cha")),
    DraftAttributeDefinition("edge", "Edge", ("edge", "edg")),
)
DRAFT_ATTRIBUTE_IDS = tuple(
    definition.attribute_id for definition in DRAFT_ATTRIBUTE_DEFINITIONS
)
_DRAFT_ATTRIBUTE_ALIAS_MAP = {
    alias: definition
    for definition in DRAFT_ATTRIBUTE_DEFINITIONS
    for alias in definition.aliases
}


def normalize_profile_key(value: object) -> str | None:
    """Normalize one rules-profile key."""
    if not isinstance(value, str):
        return None
    return value.strip().lower()


def validate_profile_key(field: str, value: object) -> list[ValidationIssue]:
    """Validate one normalized rules-profile key."""
    normalized = normalize_profile_key(value)
    if normalized is None:
        return [
            _build_issue(
                field,
                "invalid_type",
                f"{field} must be a string.",
            )
        ]
    if normalized == "":
        return [
            _build_issue(
                field,
                "required",
                f"{field} is required.",
            )
        ]
    if len(normalized) > PROFILE_KEY_MAX_LENGTH:
        return [
            _build_issue(
                field,
                "too_long",
                (
                    f"{field} must be at most "
                    f"{PROFILE_KEY_MAX_LENGTH} characters."
                ),
            )
        ]
    if PROFILE_KEY_PATTERN.fullmatch(normalized) is None:
        return [
            _build_issue(
                field,
                "invalid_format",
                (
                    f"{field} must start with a lowercase ASCII letter "
                    "and contain only lowercase letters, digits, or "
                    "underscores."
                ),
            )
        ]
    return []


def validate_display_name(value: object) -> list[ValidationIssue]:
    """Validate one rules-profile display name."""
    if not isinstance(value, str):
        return [
            _build_issue(
                "display_name",
                "invalid_type",
                "display_name must be a string.",
            )
        ]
    if value.strip() == "":
        return [
            _build_issue(
                "display_name",
                "required",
                "display_name is required.",
            )
        ]
    if len(value) > PROFILE_DISPLAY_NAME_MAX_LENGTH:
        return [
            _build_issue(
                "display_name",
                "too_long",
                (
                    "display_name must be at most "
                    f"{PROFILE_DISPLAY_NAME_MAX_LENGTH} characters."
                ),
            )
        ]
    return []


def validate_positive_int(
    field: str,
    value: object,
) -> list[ValidationIssue]:
    """Require a non-negative integer value."""
    if isinstance(value, bool) or not isinstance(value, int):
        return [
            _build_issue(
                field,
                "invalid_type",
                f"{field} must be an integer.",
            )
        ]
    if value < 0:
        return [
            _build_issue(
                field,
                "too_small",
                f"{field} must be zero or greater.",
            )
        ]
    return []


def validate_default_profile_flags(
    *,
    is_available_for_new_sessions: object,
    is_default_for_new_sessions: object,
) -> list[ValidationIssue]:
    """Validate the default-profile flag combination."""
    issues: list[ValidationIssue] = []
    if not isinstance(is_available_for_new_sessions, bool):
        issues.append(
            _build_issue(
                "is_available_for_new_sessions",
                "invalid_type",
                "is_available_for_new_sessions must be a boolean.",
            )
        )
    if not isinstance(is_default_for_new_sessions, bool):
        issues.append(
            _build_issue(
                "is_default_for_new_sessions",
                "invalid_type",
                "is_default_for_new_sessions must be a boolean.",
            )
        )
    if (
        isinstance(is_available_for_new_sessions, bool)
        and isinstance(is_default_for_new_sessions, bool)
        and is_default_for_new_sessions
        and not is_available_for_new_sessions
    ):
        issues.append(
            _build_issue(
                "is_default_for_new_sessions",
                "default_requires_available",
                "The default profile must remain available.",
            )
        )
    return issues


def normalize_draft_attribute_name(value: object) -> str | None:
    """Normalize one draft attribute selector."""
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized == "":
        return ""
    definition = _DRAFT_ATTRIBUTE_ALIAS_MAP.get(normalized)
    if definition is None:
        return None
    return definition.attribute_id


def validate_draft_attribute_name(
    field: str,
    value: object,
) -> list[ValidationIssue]:
    """Validate one draft attribute selector."""
    if not isinstance(value, str):
        return [
            _build_issue(
                field,
                "invalid_type",
                f"{field} must be a string.",
            )
        ]
    normalized = value.strip().lower()
    if normalized == "":
        return [
            _build_issue(
                field,
                "required",
                f"{field} is required.",
            )
        ]
    if normalized not in _DRAFT_ATTRIBUTE_ALIAS_MAP:
        return [
            _build_issue(
                field,
                "unknown_attribute",
                f"{field} must name one editable primary attribute.",
            )
        ]
    return []


def draft_attribute_definition(attribute_id: str) -> DraftAttributeDefinition:
    """Return one draft-attribute definition by canonical identifier."""
    definition = _DRAFT_ATTRIBUTE_ALIAS_MAP[attribute_id]
    return _DRAFT_ATTRIBUTE_ALIAS_MAP[definition.attribute_id]


def validate_draft_attribute_value(
    field: str,
    value: object,
) -> list[ValidationIssue]:
    """Require an in-range integer draft attribute value."""
    if isinstance(value, bool) or not isinstance(value, int):
        return [
            _build_issue(
                field,
                "invalid_type",
                f"{field} must be an integer rating.",
            )
        ]
    if value < ATTRIBUTE_MIN_VALUE:
        return [
            _build_issue(
                field,
                "too_small",
                f"{field} must be {ATTRIBUTE_MIN_VALUE} or greater.",
            )
        ]
    if value > ATTRIBUTE_MAX_VALUE:
        return [
            _build_issue(
                field,
                "too_large",
                f"{field} must be at most {ATTRIBUTE_MAX_VALUE}.",
            )
        ]
    return []


def missing_draft_attributes(
    values: Mapping[str, int | None],
) -> tuple[str, ...]:
    """Return canonical ids for attributes still missing from the draft."""
    return tuple(
        definition.attribute_id
        for definition in DRAFT_ATTRIBUTE_DEFINITIONS
        if values.get(definition.attribute_id) is None
    )


def draft_attributes_completion_state(
    values: Mapping[str, int | None],
) -> str:
    """Return whether all editable draft attributes are present."""
    if missing_draft_attributes(values):
        return "Incomplete"
    return "Complete"


def session_state_is_active(state: str) -> bool:
    """Return whether one session state counts as active."""
    return state in ACTIVE_SESSION_STATES


def session_state_label(state: str) -> str:
    """Return one human-readable session-state label."""
    return state.replace("_", " ").title()


def backstory_completion_state(text: str) -> str:
    """Return the D1 backstory completion state."""
    if backstory_has_content(text):
        return "Complete"
    return "Required"
