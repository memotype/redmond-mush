# mypy: ignore-errors
"""Redmond character typeclasses."""

from evennia.objects.objects import DefaultCharacter

from .objects import ObjectParent
from world.prompts import send_prompt


class Character(ObjectParent, DefaultCharacter):
    """Baseline player-character typeclass."""

    def at_post_puppet(self, **kwargs) -> None:
        """Emit the current prompt after standard puppet output."""
        super().at_post_puppet(**kwargs)
        sessions = list(self.sessions.all())
        session = sessions[-1] if sessions else None
        send_prompt(self, session=session)

    def at_post_unpuppet(self, account=None, session=None, **kwargs) -> None:
        """Restore an account-scoped prompt when leaving a character."""
        super().at_post_unpuppet(
            account=account,
            session=session,
            **kwargs,
        )
        if account is not None:
            send_prompt(account, session=session)
