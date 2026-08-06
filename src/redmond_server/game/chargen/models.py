"""Django persistence models for chargen workflow state."""

from __future__ import annotations

from django.db import models
from evennia.objects.models import ObjectDB  # type: ignore[import-untyped]

from .policy import (
    ATTRIBUTE_MAX_VALUE,
    ATTRIBUTE_MIN_VALUE,
    ACTIVE_SESSION_STATES,
    ALL_SESSION_STATES,
    PROFILE_DISPLAY_NAME_MAX_LENGTH,
    PROFILE_KEY_MAX_LENGTH,
    SESSION_STATUS_MAX_LENGTH,
)


class ChargenSessionStatus(models.TextChoices):
    """Chargen lifecycle states."""

    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    CHANGES_REQUESTED = "changes_requested", "Changes Requested"
    APPROVED = "approved", "Approved"
    ABANDONED = "abandoned", "Abandoned"
    SUPERSEDED = "superseded", "Superseded"


class ChargenRulesProfile(models.Model):
    """One immutable versioned rules profile for chargen."""

    profile_key = models.CharField(max_length=PROFILE_KEY_MAX_LENGTH)
    version = models.PositiveIntegerField()
    display_name = models.CharField(
        max_length=PROFILE_DISPLAY_NAME_MAX_LENGTH
    )
    is_available_for_new_sessions = models.BooleanField(default=True)
    is_default_for_new_sessions = models.BooleanField(default=False)
    starting_karma = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("profile_key", "version"),
                name="chargen_profile_identity_unique",
            ),
            models.UniqueConstraint(
                fields=("is_default_for_new_sessions",),
                condition=models.Q(is_default_for_new_sessions=True),
                name="chargen_default_profile_unique",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(is_default_for_new_sessions=False)
                    | models.Q(is_available_for_new_sessions=True)
                ),
                name="chargen_default_requires_available",
            ),
        ]
        indexes = [
            models.Index(
                fields=("profile_key", "is_available_for_new_sessions"),
                name="chargen_profile_lookup_idx",
            )
        ]
        ordering = ("profile_key", "version", "id")


class ChargenSession(models.Model):
    """One chargen attempt for one Evennia character."""

    character = models.ForeignKey(
        ObjectDB,
        on_delete=models.CASCADE,
        related_name="redmond_chargen_sessions",
    )
    status = models.CharField(
        max_length=SESSION_STATUS_MAX_LENGTH,
        choices=ChargenSessionStatus.choices,
        db_index=True,
    )
    rules_profile = models.ForeignKey(
        ChargenRulesProfile,
        on_delete=models.PROTECT,
        related_name="sessions",
    )
    starting_karma_snapshot = models.PositiveIntegerField()
    backstory = models.TextField(blank=True, default="")
    body = models.PositiveSmallIntegerField(null=True, blank=True)
    agility = models.PositiveSmallIntegerField(null=True, blank=True)
    reaction = models.PositiveSmallIntegerField(null=True, blank=True)
    strength = models.PositiveSmallIntegerField(null=True, blank=True)
    willpower = models.PositiveSmallIntegerField(null=True, blank=True)
    logic = models.PositiveSmallIntegerField(null=True, blank=True)
    intuition = models.PositiveSmallIntegerField(null=True, blank=True)
    charisma = models.PositiveSmallIntegerField(null=True, blank=True)
    edge = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=ALL_SESSION_STATES),
                name="chargen_session_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(starting_karma_snapshot__gte=0),
                name="chargen_session_karma_non_negative",
            ),
            models.UniqueConstraint(
                fields=("character",),
                condition=models.Q(status__in=ACTIVE_SESSION_STATES),
                name="chargen_active_session_unique",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(body__isnull=True)
                    | models.Q(
                        body__gte=ATTRIBUTE_MIN_VALUE,
                        body__lte=ATTRIBUTE_MAX_VALUE,
                    )
                ),
                name="chargen_body_draft_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(agility__isnull=True)
                    | models.Q(
                        agility__gte=ATTRIBUTE_MIN_VALUE,
                        agility__lte=ATTRIBUTE_MAX_VALUE,
                    )
                ),
                name="chargen_agility_draft_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(reaction__isnull=True)
                    | models.Q(
                        reaction__gte=ATTRIBUTE_MIN_VALUE,
                        reaction__lte=ATTRIBUTE_MAX_VALUE,
                    )
                ),
                name="chargen_reaction_draft_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(strength__isnull=True)
                    | models.Q(
                        strength__gte=ATTRIBUTE_MIN_VALUE,
                        strength__lte=ATTRIBUTE_MAX_VALUE,
                    )
                ),
                name="chargen_strength_draft_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(willpower__isnull=True)
                    | models.Q(
                        willpower__gte=ATTRIBUTE_MIN_VALUE,
                        willpower__lte=ATTRIBUTE_MAX_VALUE,
                    )
                ),
                name="chargen_willpower_draft_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(logic__isnull=True)
                    | models.Q(
                        logic__gte=ATTRIBUTE_MIN_VALUE,
                        logic__lte=ATTRIBUTE_MAX_VALUE,
                    )
                ),
                name="chargen_logic_draft_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(intuition__isnull=True)
                    | models.Q(
                        intuition__gte=ATTRIBUTE_MIN_VALUE,
                        intuition__lte=ATTRIBUTE_MAX_VALUE,
                    )
                ),
                name="chargen_intuition_draft_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(charisma__isnull=True)
                    | models.Q(
                        charisma__gte=ATTRIBUTE_MIN_VALUE,
                        charisma__lte=ATTRIBUTE_MAX_VALUE,
                    )
                ),
                name="chargen_charisma_draft_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(edge__isnull=True)
                    | models.Q(
                        edge__gte=ATTRIBUTE_MIN_VALUE,
                        edge__lte=ATTRIBUTE_MAX_VALUE,
                    )
                ),
                name="chargen_edge_draft_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=("character", "status"),
                name="chargen_character_status_idx",
            ),
            models.Index(
                fields=("character", "created_at"),
                name="chargen_character_created_idx",
            ),
        ]
        ordering = ("created_at", "id")
