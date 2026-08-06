"""Read services for active chargen session status."""

from __future__ import annotations

from .models import ChargenSession
from .policy import (
    ACTIVE_SESSION_STATES,
    DRAFT_ATTRIBUTE_DEFINITIONS,
    backstory_completion_state,
    draft_attributes_completion_state,
    missing_draft_attributes,
)
from .results import ChargenAttributeValueView, ChargenStatusView


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
    attribute_values = {
        definition.attribute_id: getattr(session, definition.attribute_id)
        for definition in DRAFT_ATTRIBUTE_DEFINITIONS
    }
    missing_attribute_ids = missing_draft_attributes(attribute_values)
    return ChargenStatusView(
        status=session.status,
        profile_display_name=session.rules_profile.display_name,
        profile_key=session.rules_profile.profile_key,
        profile_version=session.rules_profile.version,
        starting_karma=session.starting_karma_snapshot,
        completion_state=draft_attributes_completion_state(
            attribute_values
        ),
        missing_attribute_ids=missing_attribute_ids,
        backstory_state=backstory_completion_state(session.backstory),
        backstory=session.backstory,
        created_at=session.created_at,
        attributes=tuple(
            ChargenAttributeValueView(
                attribute_id=definition.attribute_id,
                label=definition.label,
                value=attribute_values[definition.attribute_id],
            )
            for definition in DRAFT_ATTRIBUTE_DEFINITIONS
        ),
        next_step_text=(
            "Use +chargen/edit attr <attribute> <value> to fill in "
            "primary attributes. Use +chargen/show attr to review "
            "attribute values."
        ),
    )
