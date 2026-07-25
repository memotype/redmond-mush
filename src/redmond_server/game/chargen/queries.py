"""Read services for active chargen session status."""

from __future__ import annotations

from .models import ChargenSession
from .policy import ACTIVE_SESSION_STATES, backstory_completion_state
from .results import ChargenStatusView


class ChargenStatusConflictError(RuntimeError):
    """Raised when active chargen session state is inconsistent."""


def get_chargen_status(character) -> ChargenStatusView | None:
    """Return the one active chargen status view for a character."""
    if getattr(character, "pk", None) is None:
        return None

    sessions = list(
        ChargenSession.objects.filter(
            character=character,
            status__in=ACTIVE_SESSION_STATES,
        )
        .select_related("rules_profile")
        .order_by("-created_at", "-id")[:2]
    )
    if not sessions:
        return None
    if len(sessions) > 1:
        raise ChargenStatusConflictError(
            "Stored chargen session state is inconsistent."
        )

    session = sessions[0]
    return ChargenStatusView(
        status=session.status,
        profile_display_name=session.rules_profile.display_name,
        profile_key=session.rules_profile.profile_key,
        profile_version=session.rules_profile.version,
        starting_karma=session.starting_karma_snapshot,
        backstory_state=backstory_completion_state(session.backstory),
        created_at=session.created_at,
        next_step_text="Writable chargen commands are not implemented yet.",
    )
