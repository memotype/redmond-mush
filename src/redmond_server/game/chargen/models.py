"""Django persistence models for chargen workflow state."""

from __future__ import annotations

from django.db import models
from evennia.objects.models import ObjectDB  # type: ignore[import-untyped]

from .policy import (
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
