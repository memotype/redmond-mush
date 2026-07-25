"""Text presentation helpers for chargen status views."""

from __future__ import annotations

from .policy import session_state_label
from .results import ChargenStatusView


def render_chargen_help() -> str:
    """Render the early chargen help surface."""
    return (
        "Chargen Commands\n"
        "Use +chargen/status to view the active chargen session.\n"
        "Writable chargen commands are not implemented yet."
    )


def render_chargen_status(
    view: ChargenStatusView | None,
    *,
    character_name: str,
) -> str:
    """Render one active chargen status view."""
    if view is None:
        return "This character does not have an active chargen session."

    created_at = view.created_at.strftime("%Y-%m-%d %H:%M UTC")
    return "\n".join(
        [
            f"{character_name} Chargen Status",
            f"Status: {session_state_label(view.status)}",
            (
                "Rules Profile: "
                f"{view.profile_display_name} "
                f"({view.profile_key} v{view.profile_version})"
            ),
            f"Starting Karma: {view.starting_karma}",
            f"Backstory: {view.backstory_state}",
            f"Created: {created_at}",
            "",
            view.next_step_text,
        ]
    )
