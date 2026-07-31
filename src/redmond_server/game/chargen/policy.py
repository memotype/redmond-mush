"""Pure-Python policy for chargen state and validation."""

from __future__ import annotations

from dataclasses import dataclass
import re

from shared_backstory import backstory_has_content


PROFILE_KEY_MAX_LENGTH = 80
PROFILE_DISPLAY_NAME_MAX_LENGTH = 120
SESSION_STATUS_MAX_LENGTH = 24
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


def _build_issue(field: str, code: str, message: str) -> ValidationIssue:
    """Create one validation issue."""
    return ValidationIssue(field=field, code=code, message=message)


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
