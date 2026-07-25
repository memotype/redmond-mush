"""Text presentation helpers for approved permanent sheet views."""

from __future__ import annotations

from .results import SheetBackstoryView, SheetView


def render_sheet(view: SheetView | None, *, character_name: str) -> str:
    """Render a compact approved permanent sheet view."""
    if view is None:
        return "This character does not have an approved sheet."

    lines = [f"{character_name} Sheet", f"Status: {view.status.title()}"]
    if view.alias:
        lines.append(f"Alias: {view.alias}")
    if view.pronouns:
        lines.append(f"Pronouns: {view.pronouns}")
    if view.metatype:
        lines.append(f"Metatype: {view.metatype}")
    if view.archetype_label:
        lines.append(f"Archetype: {view.archetype_label}")
    if view.short_concept:
        lines.append(f"Concept: {view.short_concept}")

    attribute_text = " ".join(
        f"{attribute.label} {attribute.value}"
        for attribute in view.attributes
    )
    lines.extend(
        [
            "",
            f"Attributes: {attribute_text}",
            f"Magic: {view.magic}",
            f"Resonance: {view.resonance}",
            f"Essence: {view.essence:f}",
            "",
            "Skills:",
        ]
    )

    if view.skills:
        lines.extend(
            f"- {skill.label}: {skill.rating}"
            for skill in view.skills
        )
    else:
        lines.append("- None")

    availability = "Available" if view.has_backstory else "Missing"
    lines.extend(["", f"Backstory: {availability}"])
    return "\n".join(lines)


def render_sheet_backstory(
    view: SheetBackstoryView | None,
    *,
    character_name: str,
) -> str:
    """Render the exact stored approved backstory text."""
    if view is None:
        return "This character does not have an approved sheet."

    lines = [f"{character_name} Backstory"]
    if view.alias:
        lines.append(f"Alias: {view.alias}")
    if view.metatype:
        lines.append(f"Metatype: {view.metatype}")
    lines.extend(["", view.backstory])
    return "\n".join(lines)
