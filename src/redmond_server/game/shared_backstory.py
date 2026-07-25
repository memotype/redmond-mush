"""Shared backstory normalization helpers."""

from __future__ import annotations


def normalize_backstory(text: str) -> str:
    """Normalize line endings and trim trailing blank lines."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    while lines and lines[-1].strip() == "":
        lines.pop()
    return "\n".join(lines)


def backstory_has_content(text: str) -> bool:
    """Return whether a normalized backstory contains visible content."""
    return normalize_backstory(text).strip() != ""
