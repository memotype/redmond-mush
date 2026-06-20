# mypy: ignore-errors
"""Redmond in-world object typeclasses."""

from evennia.objects.objects import DefaultObject


class ObjectParent:
    """Mixin for shared hooks across in-world typeclasses."""


class Object(ObjectParent, DefaultObject):
    """Base in-world object typeclass."""

    pass
