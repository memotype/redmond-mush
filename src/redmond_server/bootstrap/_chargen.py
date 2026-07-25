"""Bootstrap helpers for creating development chargen state."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from ._characters import CharacterLookupError, find_character
from ._env import configure_django


ALLOW_DEV_SAMPLE_DATA_FLAG = "allow_dev_sample_data"
DEFAULT_PROFILE_KEY = "redmond_standard"
DEFAULT_PROFILE_VERSION = 1
DEFAULT_PROFILE_DISPLAY_NAME = "Redmond Standard"
DEFAULT_PROFILE_STARTING_KARMA = 50


def create_sample_chargen_session(
    game_dir: Path,
    character_name: str,
    *,
    allow_dev_sample_data: bool,
    profile_key: str | None = None,
    version: int | None = None,
) -> dict[str, Any]:
    """Create one draft chargen session for development or testing."""
    if not allow_dev_sample_data:
        return {
            "status": "refused",
            "message": (
                "Sample-data creation refused. Pass "
                "--allow-dev-sample-data to continue."
            ),
        }

    configure_django(game_dir, load_evennia=True)

    from chargen.models import ChargenSession  # type: ignore[import-not-found]
    from chargen.services import (  # type: ignore[import-not-found]
        ActiveChargenSessionExistsError,
        ChargenProfileNotFoundError,
        ChargenProfileUnavailableError,
        ChargenValidationError,
        CreateChargenSessionInput,
        DefaultChargenProfileNotConfiguredError,
        EnsureChargenRulesProfileInput,
        create_chargen_session,
        ensure_chargen_rules_profile,
    )

    try:
        character = find_character(character_name)
    except CharacterLookupError as exc:
        return {
            "status": "error",
            "code": exc.code,
            "message": str(exc),
        }

    if profile_key is None and version is None:
        ensure_chargen_rules_profile(
            EnsureChargenRulesProfileInput(
                profile_key=DEFAULT_PROFILE_KEY,
                version=DEFAULT_PROFILE_VERSION,
                display_name=DEFAULT_PROFILE_DISPLAY_NAME,
                is_available_for_new_sessions=True,
                is_default_for_new_sessions=True,
                starting_karma=DEFAULT_PROFILE_STARTING_KARMA,
            )
        )

    try:
        result = create_chargen_session(
            CreateChargenSessionInput(
                character=character,
                profile_key=profile_key,
                version=version,
            )
        )
    except ActiveChargenSessionExistsError:
        existing = ChargenSession.objects.get(
            character=character,
            status="draft",
        )
        return {
            "status": "exists",
            "message": "Active chargen session already exists.",
            "character_key": character.key,
            "session_id": existing.id,
        }
    except DefaultChargenProfileNotConfiguredError as exc:
        return {
            "status": "error",
            "code": "default_profile_not_configured",
            "message": str(exc),
        }
    except ChargenProfileNotFoundError as exc:
        return {
            "status": "error",
            "code": "profile_not_found",
            "message": str(exc),
        }
    except ChargenProfileUnavailableError as exc:
        return {
            "status": "error",
            "code": "profile_unavailable",
            "message": str(exc),
        }
    except ChargenValidationError as exc:
        return {
            "status": "error",
            "code": "validation_failed",
            "message": str(exc),
            "issues": [issue.__dict__ for issue in exc.issues],
        }

    payload = asdict(result)
    payload["status"] = "created"
    payload["message"] = "Active chargen session created."
    payload["character_key"] = character.key
    return payload
