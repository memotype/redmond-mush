# mypy: ignore-errors
"""Read-only character sheet commands."""

from django.conf import settings  # type: ignore[import-untyped]

from commands.command import MuxCommand
from sheets.presentation import render_sheet, render_sheet_backstory
from sheets.queries import get_sheet_backstory_view, get_sheet_view


class CmdSheet(MuxCommand):
    """
    View the approved permanent character sheet.

    Usage:
      +sheet
      +sheet/backstory
    """

    key = "+sheet"
    aliases = ["sheet"]
    help_category = "Character"
    switch_options = ("backstory",)

    def _require_character(self):
        """Return the caller only when it is a live character object."""
        caller = getattr(self, "caller", None)
        if caller is None or not hasattr(caller, "is_typeclass"):
            self.msg("You must be puppeting a character to use +sheet.")
            return None

        if not caller.is_typeclass(
            settings.BASE_CHARACTER_TYPECLASS,
            exact=False,
        ):
            self.msg("You must be puppeting a character to use +sheet.")
            return None
        return caller

    def func(self):
        """Render the compact sheet or the full approved backstory."""
        character = self._require_character()
        if character is None:
            return

        if "backstory" in self.switches:
            view = get_sheet_backstory_view(character)
            self.msg(
                render_sheet_backstory(
                    view,
                    character_name=character.key,
                )
            )
            return

        view = get_sheet_view(character)
        self.msg(render_sheet(view, character_name=character.key))
