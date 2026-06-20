# mypy: ignore-errors
"""Redmond character typeclasses."""

from evennia.objects.objects import DefaultCharacter

from .objects import ObjectParent


class Character(ObjectParent, DefaultCharacter):
    """Baseline player-character typeclass."""

    pass
