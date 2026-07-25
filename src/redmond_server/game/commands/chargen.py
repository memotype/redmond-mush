# mypy: ignore-errors
"""Read-only chargen commands."""

from django.conf import settings  # type: ignore[import-untyped]

from chargen.presentation import render_chargen_help, render_chargen_status
from chargen.queries import ChargenStatusConflictError, get_chargen_status
from commands.command import MuxCommand


class CmdChargen(MuxCommand):
    """
    View chargen help or the active chargen session status.

    Usage:
      +chargen
      +chargen/help
      +chargen/status
    """

    key = "+chargen"
    aliases = ["chargen"]
    help_category = "Character"
    switch_options = ("help", "status")

    def _require_character(self):
        """Return the caller only when it is a live character object."""
        caller = getattr(self, "caller", None)
        if caller is None or not hasattr(caller, "is_typeclass"):
            self.msg("You must be puppeting a character to use +chargen.")
            return None

        if not caller.is_typeclass(
            settings.BASE_CHARACTER_TYPECLASS,
            exact=False,
        ):
            self.msg("You must be puppeting a character to use +chargen.")
            return None
        return caller

    def func(self):
        """Render early chargen help or active status."""
        character = self._require_character()
        if character is None:
            return

        if "help" in self.switches or "status" not in self.switches:
            self.msg(render_chargen_help())
            return

        try:
            view = get_chargen_status(character)
        except ChargenStatusConflictError:
            self.msg(
                "Chargen session data is inconsistent. Please contact staff."
            )
            return

        self.msg(render_chargen_status(view, character_name=character.key))
