"""Shared bootstrap data shapes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BootstrapState:
    """Current bootstrap state for a game directory."""

    account_count: int
    object_count: int
    superuser_count: int
    db_exists: bool | None
    secret_settings_exists: bool

    @property
    def needs_initial_start(self) -> bool:
        """Return whether Evennia still needs its first startup."""
        return self.object_count == 0

    @property
    def initial_world_ready(self) -> bool:
        """Return whether Evennia created its baseline world objects."""
        return self.account_count >= 1 and self.object_count >= 2


@dataclass(frozen=True)
class AccountState:
    """Operator-facing summary of one local account."""

    id: int
    username: str
    email: str
    is_staff: bool
    is_superuser: bool
    last_login: str | None
