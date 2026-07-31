"""Pure-Python policy for permanent sheet normalization and validation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re

from shared_backstory import (
    backstory_has_content,
    normalize_backstory as _normalize_backstory,
)


APPROVED_BACKSTORY_MAX_CHARS = 4000
ATTRIBUTE_MIN_VALUE = 0
ATTRIBUTE_MAX_VALUE = 99
SKILL_MIN_VALUE = 1
SKILL_MAX_VALUE = 99
SKILL_ID_MAX_LENGTH = 80
SHEET_ALIAS_MAX_LENGTH = 80
SHEET_PRONOUNS_MAX_LENGTH = 80
SHEET_METATYPE_MAX_LENGTH = 80
SHEET_ARCHETYPE_LABEL_MAX_LENGTH = 80
SHEET_SHORT_CONCEPT_MAX_LENGTH = 120
ESSENCE_PRECISION = Decimal("0.01")
ESSENCE_MAX_VALUE = Decimal("99.99")
SKILL_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class ValidationIssue:
    """Structured validation issue for stable service-level reporting."""

    field: str
    code: str
    message: str


def _build_issue(
    field: str,
    code: str,
    message: str,
) -> ValidationIssue:
    """Create one structured validation issue."""
    return ValidationIssue(field=field, code=code, message=message)


def normalize_backstory(text: str) -> str:
    """Preserve the existing sheet-policy helper import surface."""
    return _normalize_backstory(text)
def validate_backstory(text: str) -> list[ValidationIssue]:
    """Validate a normalized approved backstory candidate."""
    issues: list[ValidationIssue] = []
    if not backstory_has_content(text):
        issues.append(
            _build_issue(
                "backstory",
                "required",
                "An approved backstory is required.",
            )
        )
    if len(text) > APPROVED_BACKSTORY_MAX_CHARS:
        issues.append(
            _build_issue(
                "backstory",
                "too_long",
                (
                    "Approved backstory exceeds the maximum length of "
                    f"{APPROVED_BACKSTORY_MAX_CHARS} characters."
                ),
            )
        )
    return issues


def validate_bounded_text(
    field: str,
    value: object,
    *,
    label: str,
    max_length: int,
) -> list[ValidationIssue]:
    """Validate one bounded metadata string."""
    if not isinstance(value, str):
        return [
            _build_issue(
                field,
                "invalid_type",
                f"{label} must be a string.",
            )
        ]
    if len(value) > max_length:
        return [
            _build_issue(
                field,
                "too_long",
                f"{label} must be at most {max_length} characters.",
            )
        ]
    return []


def validate_attribute_rating(
    name: str,
    value: object,
) -> list[ValidationIssue]:
    """Require an in-range integer attribute value."""
    if isinstance(value, bool) or not isinstance(value, int):
        return [
            _build_issue(
                name,
                "invalid_type",
                f"{name} must be an integer rating.",
            )
        ]
    if value < ATTRIBUTE_MIN_VALUE:
        return [
            _build_issue(
                name,
                "too_small",
                f"{name} must be {ATTRIBUTE_MIN_VALUE} or greater.",
            )
        ]
    if value > ATTRIBUTE_MAX_VALUE:
        return [
            _build_issue(
                name,
                "too_large",
                f"{name} must be at most {ATTRIBUTE_MAX_VALUE}.",
            )
        ]
    return []


def validate_skill_rating(
    field: str,
    value: object,
) -> list[ValidationIssue]:
    """Require an in-range integer skill value."""
    if isinstance(value, bool) or not isinstance(value, int):
        return [
            _build_issue(
                field,
                "invalid_type",
                f"{field} must be an integer rating.",
            )
        ]
    if value < SKILL_MIN_VALUE:
        return [
            _build_issue(
                field,
                "too_small",
                f"{field} must be at least {SKILL_MIN_VALUE}.",
            )
        ]
    if value > SKILL_MAX_VALUE:
        return [
            _build_issue(
                field,
                "too_large",
                f"{field} must be at most {SKILL_MAX_VALUE}.",
            )
        ]
    return []


def normalize_skill_id(value: object) -> str | None:
    """Normalize one skill identifier for deterministic validation."""
    if not isinstance(value, str):
        return None
    return value.strip().lower()


def validate_skill_id(field: str, value: object) -> list[ValidationIssue]:
    """Validate one normalized stable skill identifier."""
    normalized = normalize_skill_id(value)
    if normalized is None:
        return [
            _build_issue(
                field,
                "invalid_type",
                "skill_id must be a string.",
            )
        ]
    if normalized == "":
        return [
            _build_issue(
                field,
                "required",
                "skill_id is required.",
            )
        ]
    if len(normalized) > SKILL_ID_MAX_LENGTH:
        return [
            _build_issue(
                field,
                "too_long",
                "skill_id exceeds the maximum allowed length.",
            )
        ]
    if SKILL_ID_PATTERN.fullmatch(normalized) is None:
        return [
            _build_issue(
                field,
                "invalid_format",
                (
                    "skill_id must start with a lowercase ASCII letter "
                    "and contain only lowercase letters, digits, or "
                    "underscores."
                ),
            )
        ]
    return []


def validate_essence_value(
    value: Decimal | str,
) -> tuple[Decimal | None, list[ValidationIssue]]:
    """Parse and normalize exact Essence values."""
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return (
            None,
            [
                _build_issue(
                    "essence",
                    "invalid_format",
                    "essence must be a decimal value.",
                )
            ],
        )

    if not parsed.is_finite():
        return (
            None,
            [
                _build_issue(
                    "essence",
                    "non_finite",
                    "essence must be a finite decimal value.",
                )
            ],
        )
    if parsed < 0:
        return (
            None,
            [
                _build_issue(
                    "essence",
                    "too_small",
                    "essence must be zero or greater.",
                )
            ],
        )
    try:
        quantized = parsed.quantize(ESSENCE_PRECISION, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return (
            None,
            [
                _build_issue(
                    "essence",
                    "invalid_format",
                    "essence must be a decimal value.",
                )
            ],
        )
    if quantized > ESSENCE_MAX_VALUE:
        return (
            None,
            [
                _build_issue(
                    "essence",
                    "too_large",
                    f"essence must be at most {ESSENCE_MAX_VALUE}.",
                )
            ],
        )
    return quantized, []
