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
class ChargenStatusView:
    """Read-only active chargen status result."""

    status: str
    profile_display_name: str
    profile_key: str
    profile_version: int
    starting_karma: int
    backstory_state: str
    created_at: datetime
    next_step_text: str
