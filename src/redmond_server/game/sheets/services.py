"""Application services for permanent approved character sheets."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.conf import settings  # type: ignore[import-untyped]
from django.db import IntegrityError, transaction

from .models import CharacterSheet, CharacterSheetStatus, CharacterSkill
from .policy import (
    SHEET_ALIAS_MAX_LENGTH,
    SHEET_ARCHETYPE_LABEL_MAX_LENGTH,
    SHEET_METATYPE_MAX_LENGTH,
    SHEET_PRONOUNS_MAX_LENGTH,
    SHEET_SHORT_CONCEPT_MAX_LENGTH,
    ValidationIssue,
    normalize_skill_id,
    normalize_backstory,
    validate_bounded_text,
    validate_attribute_rating,
    validate_backstory,
    validate_essence_value,
    validate_skill_id,
    validate_skill_rating,
)


ATTRIBUTE_NAMES = (
    "body",
    "agility",
    "reaction",
    "strength",
    "willpower",
    "logic",
    "intuition",
    "charisma",
    "edge",
    "magic",
    "resonance",
)


@dataclass(frozen=True)
class ApprovedSkillInput:
    """Stable approved skill creation payload."""

    skill_id: str
    rating: int


@dataclass(frozen=True)
class ApprovedSheetCreateInput:
    """Approved permanent sheet creation payload."""

    character: object
    alias: str = ""
    pronouns: str = ""
    metatype: str = ""
    archetype_label: str = ""
    short_concept: str = ""
    backstory: str = ""
    body: int = 0
    agility: int = 0
    reaction: int = 0
    strength: int = 0
    willpower: int = 0
    logic: int = 0
    intuition: int = 0
    charisma: int = 0
    edge: int = 0
    essence: Decimal | str = "0.00"
    magic: int = 0
    resonance: int = 0
    skills: tuple[ApprovedSkillInput, ...] = ()


@dataclass(frozen=True)
class ApprovedSheetCreateResult:
    """Stable creation result for callers and bootstrap helpers."""

    sheet_id: int
    character_id: int
    skill_count: int
    status: str


class SheetError(Exception):
    """Base application error for sheet services."""


class InvalidCharacterError(SheetError):
    """Raised when a creation target is not a valid Evennia character."""


class SheetAlreadyExistsError(SheetError):
    """Raised when a character already has a permanent sheet."""


class SheetConflictError(SheetError):
    """Raised for integrity conflicts during sheet creation."""


class SheetValidationError(SheetError):
    """Raised for stable validation problems."""

    def __init__(self, issues: Iterable[ValidationIssue]):
        self.issues = tuple(issues)
        super().__init__("Sheet validation failed.")


def _require_character(character: object):
    """Validate that the target is a live Evennia character object."""
    if character is None or not hasattr(character, "is_typeclass"):
        raise InvalidCharacterError("Target is not an Evennia character.")

    if not character.is_typeclass(
        settings.BASE_CHARACTER_TYPECLASS,
        exact=False,
    ):
        raise InvalidCharacterError("Target is not an Evennia character.")

    if getattr(character, "pk", None) is None:
        raise InvalidCharacterError("Target character must be saved first.")
    return character


def _validate_skills(
    skills: tuple[ApprovedSkillInput, ...],
) -> tuple[tuple[ApprovedSkillInput, ...], list[ValidationIssue]]:
    """Validate skill payloads before database work begins."""
    seen: set[str] = set()
    normalized: list[ApprovedSkillInput] = []
    issues: list[ValidationIssue] = []
    for index, skill in enumerate(skills):
        skill_id_field = f"skills[{index}].skill_id"
        rating_field = f"skills[{index}].rating"
        issues.extend(validate_skill_id(skill_id_field, skill.skill_id))
        normalized_skill_id = normalize_skill_id(skill.skill_id)
        issues.extend(validate_skill_rating(rating_field, skill.rating))
        if normalized_skill_id is None:
            continue
        if any(issue.field == skill_id_field for issue in issues):
            continue
        if normalized_skill_id in seen:
            issues.append(
                ValidationIssue(
                    field=skill_id_field,
                    code="duplicate",
                    message=(
                        "skill_id must be unique per sheet after "
                        "normalization."
                    ),
                )
            )
            continue
        seen.add(normalized_skill_id)
        normalized.append(
            ApprovedSkillInput(
                skill_id=normalized_skill_id,
                rating=skill.rating,
            )
        )
    return tuple(normalized), issues


def _validate_attributes(
    data: ApprovedSheetCreateInput,
) -> list[ValidationIssue]:
    """Validate the permanent attribute payload."""
    issues: list[ValidationIssue] = []
    for attribute_name in ATTRIBUTE_NAMES:
        issues.extend(
            validate_attribute_rating(
                attribute_name,
                getattr(data, attribute_name),
            )
        )
    return issues


def _validate_metadata(
    data: ApprovedSheetCreateInput,
) -> list[ValidationIssue]:
    """Validate bounded sheet metadata strings."""
    return [
        *validate_bounded_text(
            "alias",
            data.alias,
            label="alias",
            max_length=SHEET_ALIAS_MAX_LENGTH,
        ),
        *validate_bounded_text(
            "pronouns",
            data.pronouns,
            label="pronouns",
            max_length=SHEET_PRONOUNS_MAX_LENGTH,
        ),
        *validate_bounded_text(
            "metatype",
            data.metatype,
            label="metatype",
            max_length=SHEET_METATYPE_MAX_LENGTH,
        ),
        *validate_bounded_text(
            "archetype_label",
            data.archetype_label,
            label="archetype label",
            max_length=SHEET_ARCHETYPE_LABEL_MAX_LENGTH,
        ),
        *validate_bounded_text(
            "short_concept",
            data.short_concept,
            label="short concept",
            max_length=SHEET_SHORT_CONCEPT_MAX_LENGTH,
        ),
    ]


def create_approved_sheet(
    input: ApprovedSheetCreateInput,
) -> ApprovedSheetCreateResult:
    """Create one approved permanent sheet and its initial skills."""
    character = _require_character(input.character)
    issues: list[ValidationIssue] = []
    if not isinstance(input.backstory, str):
        issues.append(
            ValidationIssue(
                field="backstory",
                code="invalid_type",
                message="backstory must be a string.",
            )
        )
        normalized_backstory = ""
    else:
        normalized_backstory = normalize_backstory(input.backstory)
        issues.extend(validate_backstory(normalized_backstory))

    issues.extend(_validate_metadata(input))
    issues.extend(_validate_attributes(input))
    normalized_skills, skill_issues = _validate_skills(input.skills)
    issues.extend(skill_issues)
    essence, essence_issues = validate_essence_value(input.essence)
    issues.extend(essence_issues)
    if issues:
        raise SheetValidationError(issues)

    assert essence is not None

    if CharacterSheet.objects.filter(character=character).exists():
        raise SheetAlreadyExistsError(
            f"Character {character.pk} already has a permanent sheet."
        )

    try:
        with transaction.atomic():
            sheet = CharacterSheet.objects.create(
                character=character,
                status=CharacterSheetStatus.APPROVED,
                alias=input.alias,
                pronouns=input.pronouns,
                metatype=input.metatype,
                archetype_label=input.archetype_label,
                short_concept=input.short_concept,
                backstory=normalized_backstory,
                body=input.body,
                agility=input.agility,
                reaction=input.reaction,
                strength=input.strength,
                willpower=input.willpower,
                logic=input.logic,
                intuition=input.intuition,
                charisma=input.charisma,
                edge=input.edge,
                essence=essence,
                magic=input.magic,
                resonance=input.resonance,
            )
            CharacterSkill.objects.bulk_create(
                [
                    CharacterSkill(
                        sheet=sheet,
                        skill_id=skill.skill_id,
                        rating=skill.rating,
                    )
                    for skill in normalized_skills
                ]
            )
    except IntegrityError as exc:
        message = str(exc).lower()
        if "unique" in message and "character" in message:
            raise SheetAlreadyExistsError(
                "Character already has a permanent sheet."
            ) from exc
        raise SheetConflictError(
            "Permanent sheet creation conflicted with stored data."
        ) from exc

    return ApprovedSheetCreateResult(
        sheet_id=sheet.id,
        character_id=character.pk,
        skill_count=len(normalized_skills),
        status=sheet.status,
    )
