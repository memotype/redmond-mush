"""Django persistence models for permanent Redmond character sheets."""

from __future__ import annotations

from django.db import models
from django.db.models.functions import Length, Replace
from django.db.models.lookups import GreaterThan
from evennia.objects.models import ObjectDB  # type: ignore[import-untyped]

from .policy import (
    ATTRIBUTE_MAX_VALUE,
    ATTRIBUTE_MIN_VALUE,
    ESSENCE_MAX_VALUE,
    SHEET_ALIAS_MAX_LENGTH,
    SHEET_ARCHETYPE_LABEL_MAX_LENGTH,
    SHEET_METATYPE_MAX_LENGTH,
    SHEET_PRONOUNS_MAX_LENGTH,
    SHEET_SHORT_CONCEPT_MAX_LENGTH,
    SKILL_ID_MAX_LENGTH,
    SKILL_MAX_VALUE,
    SKILL_MIN_VALUE,
)


class CharacterSheetStatus(models.TextChoices):
    """Permanent sheet lifecycle states."""

    APPROVED = "approved", "Approved"
    RETIRED = "retired", "Retired"
    ARCHIVED = "archived", "Archived"


STATUS_VALUES = (
    CharacterSheetStatus.APPROVED,
    CharacterSheetStatus.RETIRED,
    CharacterSheetStatus.ARCHIVED,
)


def _backstory_visible_characters(field_name: str):
    """Return an expression with common blank characters removed."""
    expression = models.F(field_name)
    for source in ("\r", "\n", "\t", " "):
        expression = Replace(
            expression,
            models.Value(source),
            models.Value(""),
        )
    return expression


class CharacterSheet(models.Model):
    """One permanent approved mechanical sheet per Evennia character."""

    character = models.OneToOneField(
        ObjectDB,
        on_delete=models.CASCADE,
        related_name="redmond_sheet",
    )
    status = models.CharField(
        max_length=16,
        choices=CharacterSheetStatus.choices,
        db_index=True,
    )
    schema_version = models.PositiveSmallIntegerField(default=1)
    alias = models.CharField(
        max_length=SHEET_ALIAS_MAX_LENGTH,
        blank=True,
        default="",
    )
    pronouns = models.CharField(
        max_length=SHEET_PRONOUNS_MAX_LENGTH,
        blank=True,
        default="",
    )
    metatype = models.CharField(
        max_length=SHEET_METATYPE_MAX_LENGTH,
        blank=True,
        default="",
    )
    archetype_label = models.CharField(
        max_length=SHEET_ARCHETYPE_LABEL_MAX_LENGTH,
        blank=True,
        default="",
    )
    short_concept = models.CharField(
        max_length=SHEET_SHORT_CONCEPT_MAX_LENGTH,
        blank=True,
        default="",
    )
    backstory = models.TextField(blank=False)
    body = models.PositiveSmallIntegerField()
    agility = models.PositiveSmallIntegerField()
    reaction = models.PositiveSmallIntegerField()
    strength = models.PositiveSmallIntegerField()
    willpower = models.PositiveSmallIntegerField()
    logic = models.PositiveSmallIntegerField()
    intuition = models.PositiveSmallIntegerField()
    charisma = models.PositiveSmallIntegerField()
    edge = models.PositiveSmallIntegerField()
    essence = models.DecimalField(max_digits=4, decimal_places=2)
    magic = models.PositiveSmallIntegerField()
    resonance = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=STATUS_VALUES),
                name="sheet_status_valid",
            ),
            models.CheckConstraint(
                condition=GreaterThan(
                    Length(_backstory_visible_characters("backstory")),
                    models.Value(0),
                ),
                name="sheet_backstory_visible_text",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    body__gte=ATTRIBUTE_MIN_VALUE,
                    body__lte=ATTRIBUTE_MAX_VALUE,
                ),
                name="sheet_body_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    agility__gte=ATTRIBUTE_MIN_VALUE,
                    agility__lte=ATTRIBUTE_MAX_VALUE,
                ),
                name="sheet_agility_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    reaction__gte=ATTRIBUTE_MIN_VALUE,
                    reaction__lte=ATTRIBUTE_MAX_VALUE,
                ),
                name="sheet_reaction_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    strength__gte=ATTRIBUTE_MIN_VALUE,
                    strength__lte=ATTRIBUTE_MAX_VALUE,
                ),
                name="sheet_strength_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    willpower__gte=ATTRIBUTE_MIN_VALUE,
                    willpower__lte=ATTRIBUTE_MAX_VALUE,
                ),
                name="sheet_willpower_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    logic__gte=ATTRIBUTE_MIN_VALUE,
                    logic__lte=ATTRIBUTE_MAX_VALUE,
                ),
                name="sheet_logic_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    intuition__gte=ATTRIBUTE_MIN_VALUE,
                    intuition__lte=ATTRIBUTE_MAX_VALUE,
                ),
                name="sheet_intuition_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    charisma__gte=ATTRIBUTE_MIN_VALUE,
                    charisma__lte=ATTRIBUTE_MAX_VALUE,
                ),
                name="sheet_charisma_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    edge__gte=ATTRIBUTE_MIN_VALUE,
                    edge__lte=ATTRIBUTE_MAX_VALUE,
                ),
                name="sheet_edge_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    magic__gte=ATTRIBUTE_MIN_VALUE,
                    magic__lte=ATTRIBUTE_MAX_VALUE,
                ),
                name="sheet_magic_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    resonance__gte=ATTRIBUTE_MIN_VALUE,
                    resonance__lte=ATTRIBUTE_MAX_VALUE,
                ),
                name="sheet_resonance_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    essence__gte=ATTRIBUTE_MIN_VALUE,
                    essence__lte=ESSENCE_MAX_VALUE,
                ),
                name="sheet_essence_non_negative",
            ),
        ]


class CharacterSkill(models.Model):
    """One approved skill row on a permanent character sheet."""

    sheet = models.ForeignKey(
        CharacterSheet,
        on_delete=models.CASCADE,
        related_name="skills",
    )
    skill_id = models.CharField(max_length=SKILL_ID_MAX_LENGTH)
    rating = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("sheet", "skill_id"),
                name="sheet_skill_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    rating__gte=SKILL_MIN_VALUE,
                    rating__lte=SKILL_MAX_VALUE,
                ),
                name="sheet_skill_rating_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=("sheet", "skill_id"),
                name="sheet_skill_lookup_idx",
            )
        ]
        ordering = ("skill_id", "id")
