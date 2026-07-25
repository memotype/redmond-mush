"""Bootstrap helpers for creating development sample sheets."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from ._characters import CharacterLookupError, find_character
from ._env import configure_django


ALLOW_DEV_SAMPLE_DATA_FLAG = "allow_dev_sample_data"


def create_sample_sheet(
    game_dir: Path,
    character_name: str,
    *,
    allow_dev_sample_data: bool,
) -> dict[str, Any]:
    """Create one approved sample sheet for development or testing."""
    if not allow_dev_sample_data:
        return {
            "status": "refused",
            "message": (
                "Sample-data creation refused. Pass "
                "--allow-dev-sample-data to continue."
            ),
        }

    configure_django(game_dir, load_evennia=True)

    from sheets.models import CharacterSheet  # type: ignore[import-not-found]
    from sheets.services import (  # type: ignore[import-not-found]
        ApprovedSheetCreateInput,
        ApprovedSkillInput,
        SheetAlreadyExistsError,
        create_approved_sheet,
    )

    try:
        character = find_character(character_name)
    except CharacterLookupError as exc:
        return {
            "status": "error",
            "code": exc.code,
            "message": str(exc),
        }
    try:
        result = create_approved_sheet(
            ApprovedSheetCreateInput(
                character=character,
                alias="Sample Runner",
                pronouns="they/them",
                metatype="Human",
                archetype_label="Runner",
                short_concept="Streetwise scout",
                backstory=(
                    "Raised in the sprawl, this runner survives by staying "
                    "observant and moving first.\n\n"
                    "They keep jobs small, quiet, and profitable."
                ),
                body=3,
                agility=4,
                reaction=4,
                strength=2,
                willpower=3,
                logic=3,
                intuition=4,
                charisma=2,
                edge=2,
                essence="6.00",
                magic=0,
                resonance=0,
                skills=(
                    ApprovedSkillInput("athletics", 3),
                    ApprovedSkillInput("perception", 4),
                ),
            )
        )
    except SheetAlreadyExistsError:
        existing_sheet = CharacterSheet.objects.get(character=character)
        return {
            "status": "exists",
            "message": "Sample sheet already exists.",
            "character_key": character.key,
            "sheet_id": existing_sheet.id,
        }
    payload = asdict(result)
    payload["status"] = "created"
    payload["message"] = "Sample sheet created."
    payload["character_key"] = character.key
    return payload
