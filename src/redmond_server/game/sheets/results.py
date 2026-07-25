"""Structured immutable sheet read results."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class AttributeView:
    """One compact attribute value for presentation."""

    name: str
    label: str
    value: int


@dataclass(frozen=True)
class SkillView:
    """One compact skill value for presentation."""

    skill_id: str
    label: str
    rating: int


@dataclass(frozen=True)
class SheetView:
    """Compact approved sheet view for self-read presentation."""

    alias: str
    pronouns: str
    metatype: str
    archetype_label: str
    short_concept: str
    status: str
    attributes: tuple[AttributeView, ...]
    essence: Decimal
    magic: int
    resonance: int
    skills: tuple[SkillView, ...]
    has_backstory: bool


@dataclass(frozen=True)
class SheetBackstoryView:
    """Full approved backstory read result."""

    status: str
    backstory: str
    alias: str
    metatype: str
