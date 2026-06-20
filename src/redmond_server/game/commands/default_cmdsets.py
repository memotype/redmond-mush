# mypy: ignore-errors
"""Default command-set hooks for the Redmond game directory."""

from evennia import default_cmds


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """Character command set for in-world characters."""

    key = "DefaultCharacter"

    def at_cmdset_creation(self) -> None:
        """Populate the default character command set."""
        super().at_cmdset_creation()


class AccountCmdSet(default_cmds.AccountCmdSet):
    """Account command set for out-of-character account commands."""

    key = "DefaultAccount"

    def at_cmdset_creation(self) -> None:
        """Populate the default account command set."""
        super().at_cmdset_creation()


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """Command set available before login."""

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self) -> None:
        """Populate the unlogged-in command set."""
        super().at_cmdset_creation()


class SessionCmdSet(default_cmds.SessionCmdSet):
    """Session-level command set for logged-in sessions."""

    key = "DefaultSession"

    def at_cmdset_creation(self) -> None:
        """Populate the session command set."""
        super().at_cmdset_creation()
