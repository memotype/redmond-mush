"""Application services for chargen profiles and sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.conf import settings  # type: ignore[import-untyped]
from django.db import IntegrityError, transaction

from .models import (
    ChargenRulesProfile,
    ChargenSession,
    ChargenSessionStatus,
)
from .policy import (
    ACTIVE_SESSION_STATES,
    ValidationIssue,
    draft_attribute_definition,
    normalize_draft_attribute_name,
    normalize_profile_key,
    validate_draft_attribute_name,
    validate_draft_attribute_value,
    validate_default_profile_flags,
    validate_display_name,
    validate_positive_int,
    validate_profile_key,
)
from .results import (
    ChargenAttributeEditResult,
    ChargenRulesProfileResult,
    ChargenSessionCreateResult,
)


@dataclass(frozen=True)
class EnsureChargenRulesProfileInput:
    """Stable input for rules-profile bootstrap maintenance."""

    profile_key: str
    version: int
    display_name: str
    is_available_for_new_sessions: bool = True
    is_default_for_new_sessions: bool = False
    starting_karma: int = 0


@dataclass(frozen=True)
class CreateChargenSessionInput:
    """Stable input for chargen-session creation."""

    character: object
    profile_key: str | None = None
    version: int | None = None


@dataclass(frozen=True)
class EditChargenAttributeInput:
    """Stable input for one draft attribute edit."""

    character: object
    attribute_name: object
    value: object


class ChargenError(Exception):
    """Base application error for chargen services."""


class InvalidCharacterError(ChargenError):
    """Raised when a target is not a valid Evennia character."""


class ChargenProfileNotFoundError(ChargenError):
    """Raised when one exact rules profile does not exist."""


class DefaultChargenProfileNotConfiguredError(ChargenError):
    """Raised when no default rules profile is configured."""


class ChargenProfileUnavailableError(ChargenError):
    """Raised when a rules profile cannot accept new sessions."""


class ActiveChargenSessionExistsError(ChargenError):
    """Raised when a character already has one active chargen session."""


class ActiveChargenSessionNotFoundError(ChargenError):
    """Raised when no active chargen session exists for editing."""


class ChargenSessionConflictError(ChargenError):
    """Raised for integrity conflicts during session creation."""


class ChargenProfileImmutableError(ChargenError):
    """Raised when immutable rules-profile fields would change."""


class ChargenValidationError(ChargenError):
    """Raised for stable validation failures."""

    def __init__(self, issues: Iterable[ValidationIssue]):
        self.issues = tuple(issues)
        super().__init__("Chargen validation failed.")


class UnknownDraftAttributeError(ChargenError):
    """Raised when one editable draft attribute name is unknown."""


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


def _validate_profile_input(
    input: EnsureChargenRulesProfileInput,
) -> tuple[str | None, list[ValidationIssue]]:
    """Validate one rules-profile ensure payload."""
    issues: list[ValidationIssue] = []
    issues.extend(validate_profile_key("profile_key", input.profile_key))
    normalized_profile_key = normalize_profile_key(input.profile_key)
    issues.extend(validate_positive_int("version", input.version))
    if input.version == 0:
        issues.append(
            ValidationIssue(
                field="version",
                code="too_small",
                message="version must be one or greater.",
            )
        )
    issues.extend(validate_display_name(input.display_name))
    issues.extend(validate_positive_int("starting_karma", input.starting_karma))
    issues.extend(
        validate_default_profile_flags(
            is_available_for_new_sessions=input.is_available_for_new_sessions,
            is_default_for_new_sessions=input.is_default_for_new_sessions,
        )
    )
    return normalized_profile_key, issues


def _get_active_chargen_session(character) -> ChargenSession:
    """Return the one active chargen session for a character."""
    sessions = list(
        ChargenSession.objects.filter(
            character=character,
            status__in=ACTIVE_SESSION_STATES,
        )
        .order_by("-created_at", "-id")[:2]
    )
    if not sessions:
        raise ActiveChargenSessionNotFoundError(
            "Character does not have an active chargen session."
        )
    if len(sessions) > 1:
        raise ChargenSessionConflictError(
            "Stored chargen session state is inconsistent."
        )
    return sessions[0]


def ensure_chargen_rules_profile(
    input: EnsureChargenRulesProfileInput,
) -> ChargenRulesProfileResult:
    """Create or maintain one rules profile for bootstrap and tests."""
    normalized_profile_key, issues = _validate_profile_input(input)
    if issues:
        raise ChargenValidationError(issues)

    assert normalized_profile_key is not None

    with transaction.atomic():
        profile = ChargenRulesProfile.objects.filter(
            profile_key=normalized_profile_key,
            version=input.version,
        ).first()
        created = profile is None
        if input.is_default_for_new_sessions:
            default_profiles = ChargenRulesProfile.objects.filter(
                is_default_for_new_sessions=True,
            )
            if profile is not None:
                default_profiles = default_profiles.exclude(pk=profile.pk)
            default_profiles.update(is_default_for_new_sessions=False)
        if profile is None:
            profile = ChargenRulesProfile.objects.create(
                profile_key=normalized_profile_key,
                version=input.version,
                display_name=input.display_name,
                is_available_for_new_sessions=(
                    input.is_available_for_new_sessions
                ),
                is_default_for_new_sessions=(
                    input.is_default_for_new_sessions
                ),
                starting_karma=input.starting_karma,
            )
        elif profile.sessions.exists():
            immutable_changes = []
            if profile.profile_key != normalized_profile_key:
                immutable_changes.append("profile_key")
            if profile.version != input.version:
                immutable_changes.append("version")
            if profile.display_name != input.display_name:
                immutable_changes.append("display_name")
            if profile.starting_karma != input.starting_karma:
                immutable_changes.append("starting_karma")
            if immutable_changes:
                fields_text = ", ".join(immutable_changes)
                raise ChargenProfileImmutableError(
                    "Referenced rules profiles keep these fields "
                    f"immutable: {fields_text}."
                )
            profile.is_available_for_new_sessions = (
                input.is_available_for_new_sessions
            )
            profile.is_default_for_new_sessions = (
                input.is_default_for_new_sessions
            )
            profile.save(
                update_fields=[
                    "is_available_for_new_sessions",
                    "is_default_for_new_sessions",
                    "updated_at",
                ]
            )
        else:
            profile.profile_key = normalized_profile_key
            profile.version = input.version
            profile.display_name = input.display_name
            profile.is_available_for_new_sessions = (
                input.is_available_for_new_sessions
            )
            profile.is_default_for_new_sessions = (
                input.is_default_for_new_sessions
            )
            profile.starting_karma = input.starting_karma
            profile.save()
        profile.refresh_from_db()

    return ChargenRulesProfileResult(
        profile_id=profile.id,
        profile_key=profile.profile_key,
        profile_version=profile.version,
        profile_display_name=profile.display_name,
        is_available_for_new_sessions=profile.is_available_for_new_sessions,
        is_default_for_new_sessions=profile.is_default_for_new_sessions,
        starting_karma=profile.starting_karma,
        created=created,
    )


def _resolve_profile_selection(
    input: CreateChargenSessionInput,
) -> ChargenRulesProfile:
    """Resolve one rules-profile row for session creation."""
    if input.profile_key is None and input.version is None:
        profile = ChargenRulesProfile.objects.filter(
            is_default_for_new_sessions=True,
        ).first()
        if profile is None:
            raise DefaultChargenProfileNotConfiguredError(
                "No default chargen rules profile is configured."
            )
    else:
        issues: list[ValidationIssue] = []
        if input.profile_key is None or input.version is None:
            issues.append(
                ValidationIssue(
                    field="profile_selection",
                    code="incomplete_identity",
                    message=(
                        "profile_key and version must be provided "
                        "together."
                    ),
                )
            )
            raise ChargenValidationError(issues)
        issues.extend(validate_profile_key("profile_key", input.profile_key))
        issues.extend(validate_positive_int("version", input.version))
        if input.version == 0:
            issues.append(
                ValidationIssue(
                    field="version",
                    code="too_small",
                    message="version must be one or greater.",
                )
            )
        if issues:
            raise ChargenValidationError(issues)
        normalized_profile_key = normalize_profile_key(input.profile_key)
        assert normalized_profile_key is not None
        profile = ChargenRulesProfile.objects.filter(
            profile_key=normalized_profile_key,
            version=input.version,
        ).first()
        if profile is None:
            raise ChargenProfileNotFoundError(
                "Chargen rules profile was not found."
            )

    if not profile.is_available_for_new_sessions:
        raise ChargenProfileUnavailableError(
            "Chargen rules profile is unavailable for new sessions."
        )
    karma_issues = validate_positive_int(
        "starting_karma",
        profile.starting_karma,
    )
    if karma_issues:
        raise ChargenValidationError(karma_issues)
    return profile


def create_chargen_session(
    input: CreateChargenSessionInput,
) -> ChargenSessionCreateResult:
    """Create one active draft chargen session."""
    character = _require_character(input.character)
    profile = _resolve_profile_selection(input)

    if ChargenSession.objects.filter(
        character=character,
        status__in=ACTIVE_SESSION_STATES,
    ).exists():
        raise ActiveChargenSessionExistsError(
            f"Character {character.pk} already has an active chargen session."
        )

    try:
        with transaction.atomic():
            session = ChargenSession.objects.create(
                character=character,
                status=ChargenSessionStatus.DRAFT,
                rules_profile=profile,
                starting_karma_snapshot=profile.starting_karma,
                backstory="",
            )
    except IntegrityError as exc:
        message = str(exc).lower()
        if "chargen_active_session_unique" in message:
            raise ActiveChargenSessionExistsError(
                "Character already has an active chargen session."
            ) from exc
        raise ChargenSessionConflictError(
            "Chargen session creation conflicted with stored data."
        ) from exc

    return ChargenSessionCreateResult(
        session_id=session.id,
        character_id=character.pk,
        status=session.status,
        profile_key=profile.profile_key,
        profile_version=profile.version,
        profile_display_name=profile.display_name,
        starting_karma_snapshot=session.starting_karma_snapshot,
    )


def edit_chargen_attribute(
    input: EditChargenAttributeInput,
) -> ChargenAttributeEditResult:
    """Update one editable draft attribute on the active chargen session."""
    character = _require_character(input.character)

    issues = validate_draft_attribute_name(
        "attribute_name",
        input.attribute_name,
    )
    if issues:
        first_issue = issues[0]
        if first_issue.code == "unknown_attribute":
            raise UnknownDraftAttributeError(first_issue.message)
        raise ChargenValidationError(issues)

    normalized_attribute_name = normalize_draft_attribute_name(
        input.attribute_name
    )
    assert normalized_attribute_name is not None

    value_issues = validate_draft_attribute_value("value", input.value)
    if value_issues:
        raise ChargenValidationError(value_issues)
    assert isinstance(input.value, int)
    assert not isinstance(input.value, bool)
    value = input.value

    definition = draft_attribute_definition(normalized_attribute_name)
    session = _get_active_chargen_session(character)
    setattr(session, definition.attribute_id, value)
    try:
        session.save(
            update_fields=[definition.attribute_id, "updated_at"]
        )
    except IntegrityError as exc:
        raise ChargenSessionConflictError(
            "Chargen attribute edit conflicted with stored data."
        ) from exc

    return ChargenAttributeEditResult(
        session_id=session.id,
        attribute_id=definition.attribute_id,
        attribute_label=definition.label,
        value=value,
    )
