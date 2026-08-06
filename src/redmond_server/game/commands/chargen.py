# mypy: ignore-errors
"""Chargen commands for draft views and primary-attribute edits."""

from django.conf import settings  # type: ignore[import-untyped]

from chargen.presentation import (
    render_chargen_attributes,
    render_chargen_background,
    render_chargen_help,
    render_chargen_status,
    render_chargen_summary,
)
from chargen.queries import ChargenStatusConflictError, get_chargen_status
from chargen.services import (
    ActiveChargenSessionExistsError,
    ActiveChargenSessionNotFoundError,
    ChargenProfileUnavailableError,
    ChargenValidationError,
    CreateChargenSessionInput,
    DefaultChargenProfileNotConfiguredError,
    EditChargenAttributeInput,
    UnknownDraftAttributeError,
    create_chargen_session,
    edit_chargen_attribute,
)
from commands.command import MuxCommand


class CmdChargen(MuxCommand):
    """
    View chargen help or the active chargen session status.

    Usage:
      +chargen
      +chargen/help
      +chargen/start
      +chargen/status
      +chargen/show
      +chargen/show attr
      +chargen/show background
      +chargen/show bg
      +chargen/edit attr <attribute> <value>
    """

    key = "+chargen"
    aliases = ["chargen"]
    help_category = "Character"
    switch_options = ("help", "start", "status", "show", "edit")

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
        """Render chargen views or edit one draft attribute."""
        character = self._require_character()
        if character is None:
            return

        if "help" in self.switches or not self.switches:
            self.msg(render_chargen_help())
            return

        if "show" in self.switches:
            self._show_view(character)
            return

        if "edit" in self.switches:
            self._edit_attribute(character)
            return

        if "start" in self.switches:
            self._start_session(character)
            return

        if "status" not in self.switches:
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

    def _show_view(self, character) -> None:
        """Render one chargen read view selected by args."""
        topic = self.args.strip().lower()
        try:
            view = get_chargen_status(character)
        except ChargenStatusConflictError:
            self.msg(
                "Chargen session data is inconsistent. Please contact staff."
            )
            return

        if topic == "":
            self.msg(render_chargen_summary(view, character_name=character.key))
            return
        if topic == "attr":
            self.msg(
                render_chargen_attributes(
                    view,
                    character_name=character.key,
                )
            )
            return
        if topic in {"background", "bg"}:
            self.msg(
                render_chargen_background(
                    view,
                    character_name=character.key,
                )
            )
            return
        self.msg(
            "Usage: +chargen/show, +chargen/show attr, or "
            "+chargen/show background"
        )

    def _start_session(self, character) -> None:
        """Create one active chargen session from the default profile."""
        if self.args.strip() != "":
            self.msg("Usage: +chargen/start")
            return

        try:
            create_chargen_session(
                CreateChargenSessionInput(character=character)
            )
        except ActiveChargenSessionExistsError:
            self.msg(
                "This character already has an active chargen session. "
                "Use +chargen/status or +chargen/show to continue."
            )
            return
        except DefaultChargenProfileNotConfiguredError:
            self.msg(
                "No default chargen rules profile is configured. "
                "Please contact staff."
            )
            return
        except ChargenProfileUnavailableError:
            self.msg(
                "The default chargen rules profile is unavailable. "
                "Please contact staff."
            )
            return
        except ChargenValidationError:
            self.msg(
                "The default chargen rules profile is invalid. "
                "Please contact staff."
            )
            return

        self.msg(
            "Chargen session started. "
            "Use +chargen/show or +chargen/status to continue."
        )

    def _edit_attribute(self, character) -> None:
        """Edit one draft primary attribute."""
        parts = self.args.strip().split()
        if len(parts) != 3 or parts[0].lower() != "attr":
            self.msg("Usage: +chargen/edit attr <attribute> <value>")
            return

        _, attribute_name, raw_value = parts
        try:
            value = int(raw_value)
        except ValueError:
            self.msg("Attribute values must be integers.")
            return

        try:
            result = edit_chargen_attribute(
                EditChargenAttributeInput(
                    character=character,
                    attribute_name=attribute_name,
                    value=value,
                )
            )
        except ActiveChargenSessionNotFoundError:
            self.msg(
                "This character does not have an active chargen session. "
                "Use +chargen/start first."
            )
            return
        except UnknownDraftAttributeError as exc:
            self.msg(str(exc))
            return
        except ChargenValidationError as exc:
            self.msg(exc.issues[0].message)
            return

        self.msg(
            f"{result.attribute_label} set to {result.value}. "
            "Use +chargen/show attr to review attribute values."
        )
