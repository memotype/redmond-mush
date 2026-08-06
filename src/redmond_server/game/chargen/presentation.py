"""Text presentation helpers for chargen status views."""

from __future__ import annotations

from .policy import session_state_label
from .results import ChargenStatusView


NO_ACTIVE_SESSION_TEXT = (
    "This character does not have an active chargen session. "
    "Use +chargen/start first."
)


def render_chargen_help() -> str:
    """Render the early chargen help surface."""
    return (
        "Chargen Commands\n"
        "Use +chargen/start to begin or resume chargen setup.\n"
        "Use +chargen/status to view chargen workflow status.\n"
        "Use +chargen/show to view the draft summary.\n"
        "Use +chargen/show attr to list primary attributes.\n"
        "Use +chargen/show background to view the draft backstory.\n"
        "Use +chargen/edit attr <attribute> <value> to edit "
        "primary attributes."
    )


def _format_attribute_value(value: int | None) -> str:
    """Format one chargen attribute value for read views."""
    if value is None:
        return "--"
    return str(value)


def render_chargen_status(
    view: ChargenStatusView | None,
    *,
    character_name: str,
) -> str:
    """Render one active chargen status view."""
    if view is None:
        return NO_ACTIVE_SESSION_TEXT

    created_at = view.created_at.strftime("%Y-%m-%d %H:%M UTC")
    if view.missing_attribute_ids:
        missing_text = ", ".join(
            attribute_id.title().replace("_", " ")
            for attribute_id in view.missing_attribute_ids
        )
    else:
        missing_text = "None"
    return "\n".join(
        [
            f"{character_name} Chargen Status",
            f"Status: {session_state_label(view.status)}",
            f"Completion: {view.completion_state}",
            (
                "Rules Profile: "
                f"{view.profile_display_name} "
                f"({view.profile_key} v{view.profile_version})"
            ),
            f"Starting Karma: {view.starting_karma}",
            f"Missing Attributes: {missing_text}",
            f"Backstory: {view.backstory_state}",
            f"Created: {created_at}",
            "",
            view.next_step_text,
        ]
    )


def render_chargen_summary(
    view: ChargenStatusView | None,
    *,
    character_name: str,
) -> str:
    """Render the default chargen draft summary."""
    if view is None:
        return NO_ACTIVE_SESSION_TEXT

    attribute_text = " ".join(
        f"{attribute.label} {_format_attribute_value(attribute.value)}"
        for attribute in view.attributes
    )
    lines = [
        f"{character_name} Chargen Draft",
        f"Status: {session_state_label(view.status)}",
        f"Completion: {view.completion_state}",
        (
            "Rules Profile: "
            f"{view.profile_display_name} "
            f"({view.profile_key} v{view.profile_version})"
        ),
        f"Starting Karma: {view.starting_karma}",
        "",
        f"Attributes: {attribute_text}",
        f"Backstory: {view.backstory_state}",
        "",
        view.next_step_text,
    ]
    return "\n".join(lines)


def render_chargen_attributes(
    view: ChargenStatusView | None,
    *,
    character_name: str,
) -> str:
    """Render the focused chargen attribute view."""
    if view is None:
        return NO_ACTIVE_SESSION_TEXT

    lines = [
        f"{character_name} Chargen Attributes",
        f"Completion: {view.completion_state}",
        "",
    ]
    lines.extend(
        f"{attribute.label}: {_format_attribute_value(attribute.value)}"
        for attribute in view.attributes
    )
    return "\n".join(lines)


def render_chargen_background(
    view: ChargenStatusView | None,
    *,
    character_name: str,
) -> str:
    """Render the exact stored draft backstory text."""
    if view is None:
        return NO_ACTIVE_SESSION_TEXT
    if view.backstory == "":
        return (
            f"{character_name} Chargen Background\n\n"
            "No draft backstory is set."
        )
    return "\n".join(
        [
            f"{character_name} Chargen Background",
            "",
            view.backstory,
        ]
    )
