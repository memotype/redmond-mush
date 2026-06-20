# mypy: ignore-errors
"""Redmond room typeclasses."""

from evennia.objects.objects import DefaultRoom

from .objects import ObjectParent


class Room(ObjectParent, DefaultRoom):
    """Baseline room typeclass for Redmond."""

    pass
