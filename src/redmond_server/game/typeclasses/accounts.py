# mypy: ignore-errors
"""Redmond account typeclasses."""

from evennia.accounts.accounts import DefaultAccount, DefaultGuest

from world.game_text import LOGIN_MOTD


class Account(DefaultAccount):
    """Out-of-character Redmond account typeclass."""

    def at_post_login(self, session=None, **kwargs) -> None:
        """Show the Redmond MOTD after a successful login."""
        super().at_post_login(session=session, **kwargs)
        self.msg(LOGIN_MOTD)


class Guest(DefaultGuest):
    """Guest account typeclass placeholder."""

    pass
