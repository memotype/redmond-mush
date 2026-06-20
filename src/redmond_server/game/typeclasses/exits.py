# mypy: ignore-errors
"""Redmond exit typeclasses."""

from evennia.objects.objects import DefaultExit

from .objects import ObjectParent


class Exit(ObjectParent, DefaultExit):
    """Baseline exit typeclass for Redmond."""

    pass
