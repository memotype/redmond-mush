"""Shared Evennia character lookup helpers for bootstrap commands."""

from __future__ import annotations


class CharacterLookupError(RuntimeError):
    """Base error for operator-facing character lookup failures."""

    def __init__(self, *, code: str, message: str):
        self.code = code
        super().__init__(message)


def find_character(character_name: str):
    """Resolve one existing Evennia character by exact key."""
    import evennia  # type: ignore[import-untyped]
    from django.conf import settings  # type: ignore[import-untyped]

    matches = evennia.search_object(character_name, exact=True)
    characters = [
        obj
        for obj in matches
        if obj.is_typeclass(
            settings.BASE_CHARACTER_TYPECLASS,
            exact=False,
        )
    ]
    if not characters:
        raise CharacterLookupError(
            code="character_not_found",
            message=f"Character not found: {character_name}",
        )
    if len(characters) > 1:
        raise CharacterLookupError(
            code="character_name_ambiguous",
            message=(
                "Character name is ambiguous for bootstrap lookup: "
                f"{character_name}"
            ),
        )
    return characters[0]
