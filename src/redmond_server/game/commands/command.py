# mypy: ignore-errors
"""Redmond command base classes."""

from evennia.commands.default.muxcommand import MuxCommand as EvenniaMuxCommand

from world.prompts import (
    clear_prompt_emitted,
    prompt_was_emitted,
    send_prompt,
)


class MuxCommand(EvenniaMuxCommand):
    """Redmond-aware MUX command base with prompt emission."""

    def at_pre_cmd(self):
        """Reset prompt state before command execution."""
        clear_prompt_emitted(getattr(self, "session", None))
        return super().at_pre_cmd()

    def at_post_cmd(self):
        """Emit a prompt unless one was already sent during the command."""
        super().at_post_cmd()
        session = getattr(self, "session", None)
        if prompt_was_emitted(session):
            clear_prompt_emitted(session)
            return
        send_prompt(getattr(self, "caller", None), session=session)
        clear_prompt_emitted(session)


class MuxAccountCommand(MuxCommand):
    """Account-scoped Redmond command base."""

    account_caller = True
