"""Read services for approved permanent character sheets."""

from __future__ import annotations

from django.db.models import Prefetch

from .models import CharacterSheet, CharacterSheetStatus, CharacterSkill
from .results import (
    AttributeView,
    SheetBackstoryView,
    SheetView,
    SkillView,
)


ATTRIBUTE_LABELS = (
    ("body", "BOD"),
    ("agility", "AGI"),
    ("reaction", "REA"),
    ("strength", "STR"),
    ("willpower", "WIL"),
    ("logic", "LOG"),
    ("intuition", "INT"),
    ("charisma", "CHA"),
    ("edge", "EDG"),
)


def _skill_label(skill_id: str) -> str:
    """Derive a readable label from a stable skill identifier."""
    return skill_id.replace("_", " ").title()


def _load_sheet(character) -> CharacterSheet | None:
    """Fetch the approved permanent sheet for one character."""
    if getattr(character, "pk", None) is None:
        return None

    return (
        CharacterSheet.objects.filter(
            character=character,
            status=CharacterSheetStatus.APPROVED,
        )
        .prefetch_related(
            Prefetch(
                "skills",
                queryset=CharacterSkill.objects.order_by("skill_id"),
            )
        )
        .first()
    )


def get_sheet_view(character) -> SheetView | None:
    """Return a compact immutable view of the approved permanent sheet."""
    sheet = _load_sheet(character)
    if sheet is None:
        return None

    attributes = tuple(
        AttributeView(
            name=name,
            label=label,
            value=getattr(sheet, name),
        )
        for name, label in ATTRIBUTE_LABELS
    )
    skills = tuple(
        SkillView(
            skill_id=skill.skill_id,
            label=_skill_label(skill.skill_id),
            rating=skill.rating,
        )
        for skill in sheet.skills.all()
    )
    return SheetView(
        alias=sheet.alias,
        pronouns=sheet.pronouns,
        metatype=sheet.metatype,
        archetype_label=sheet.archetype_label,
        short_concept=sheet.short_concept,
        status=sheet.status,
        attributes=attributes,
        essence=sheet.essence,
        magic=sheet.magic,
        resonance=sheet.resonance,
        skills=skills,
        has_backstory=bool(sheet.backstory.strip()),
    )


def get_sheet_backstory_view(character) -> SheetBackstoryView | None:
    """Return the approved permanent backstory for one character."""
    sheet = _load_sheet(character)
    if sheet is None:
        return None

    return SheetBackstoryView(
        status=sheet.status,
        backstory=sheet.backstory,
        alias=sheet.alias,
        metatype=sheet.metatype,
    )
