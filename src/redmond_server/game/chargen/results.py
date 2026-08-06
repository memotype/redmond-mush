"""Structured immutable chargen results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ChargenRulesProfileResult:
    """Result for profile ensure helpers."""

    profile_id: int
    profile_key: str
    profile_version: int
    profile_display_name: str
    is_available_for_new_sessions: bool
    is_default_for_new_sessions: bool
    starting_karma: int
    created: bool


@dataclass(frozen=True)
class ChargenSessionCreateResult:
    """Result for chargen-session creation."""

    session_id: int
    character_id: int
    status: str
    profile_key: str
    profile_version: int
    profile_display_name: str
    starting_karma_snapshot: int


@dataclass(frozen=True)
class ChargenAttributeValueView:
    """One chargen draft attribute for read presentation."""

    attribute_id: str
    label: str
    value: int | None


@dataclass(frozen=True)
class ChargenAttributeEditResult:
    """Result for one draft attribute edit."""

    session_id: int
    attribute_id: str
    attribute_label: str
    value: int


@dataclass(frozen=True)
class ChargenStatusView:
    """Read view for one active chargen session."""

    status: str
    profile_display_name: str
    profile_key: str
    profile_version: int
    starting_karma: int
    completion_state: str
    missing_attribute_ids: tuple[str, ...]
    backstory_state: str
    backstory: str
    created_at: datetime
    attributes: tuple[ChargenAttributeValueView, ...]
    next_step_text: str
