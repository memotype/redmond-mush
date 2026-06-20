"""Account-oriented bootstrap operations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ._env import configure_django
from ._world import sync_staff_channel_membership

TEST_FAIL_STAFF_SYNC_ENV = "REDMOND_TEST_FAIL_STAFF_SYNC"


class _RecoverySessionHandler:
    """Minimal session handler for offline account creation."""

    @staticmethod
    def sessions_from_account(account) -> list[object]:
        return []


def _record_follow_up(
    payload: dict[str, Any],
    *,
    action: str,
    status: str,
    warning: str | None = None,
) -> dict[str, Any]:
    """Attach follow-up status without changing the primary action result."""
    payload["follow_up"] = {
        "action": action,
        "status": status,
    }
    if warning is not None:
        payload["follow_up"]["warning"] = warning
        payload["warning"] = warning
    return payload


def _get_account_by_username(game_dir: Path, username: str):
    """Return an account by case-insensitive username or fail clearly."""
    configure_django(game_dir, load_evennia=False)

    from evennia.accounts.models import (  # type: ignore[import-untyped]
        AccountDB,
    )

    account = AccountDB.objects.filter(username__iexact=username).first()
    if account is None:
        raise RuntimeError(f"Account not found: {username}")
    return account


def _sync_staff_channel_follow_up(
    game_dir: Path,
    username: str,
) -> dict[str, Any]:
    """Run staff-channel synchronization as a best-effort follow-up."""
    result: dict[str, Any] = {}
    try:
        if os.environ.get(TEST_FAIL_STAFF_SYNC_ENV) == "1":
            raise RuntimeError(
                "staff channel unavailable "
                f"({TEST_FAIL_STAFF_SYNC_ENV}=1)"
            )
        sync_staff_channel_membership(game_dir, username)
    except Exception as exc:
        warning = (
            "Primary account change succeeded, but staff-channel "
            f"sync was deferred: {type(exc).__name__}: {exc}"
        )
        return _record_follow_up(
            result,
            action="staff_channel_sync",
            status="deferred",
            warning=warning,
        )

    return _record_follow_up(
        result,
        action="staff_channel_sync",
        status="applied",
    )


def _prepare_offline_account_creation() -> None:
    """Provide the minimum Evennia globals needed for offline account setup."""
    import evennia  # type: ignore[import-untyped]

    if getattr(evennia, "SESSION_HANDLER", None) is None:
        evennia.SESSION_HANDLER = _RecoverySessionHandler()


def ensure_superuser(
    game_dir: Path,
    username: str,
    password: str,
    email: str,
) -> str:
    """Create the bootstrap superuser if the database has none yet."""
    configure_django(game_dir, load_evennia=False)

    from evennia.accounts.models import (  # type: ignore[import-untyped]
        AccountDB,
    )

    existing = AccountDB.objects.filter(is_superuser=True).first()
    if existing is not None:
        return existing.username

    account = AccountDB.objects.create_superuser(
        username=username,
        email=email,
        password=password,
    )
    return account.username


def list_accounts(game_dir: Path) -> list[dict[str, Any]]:
    """Return local account summaries for operator tooling."""
    configure_django(game_dir, load_evennia=False)

    from evennia.accounts.models import (  # type: ignore[import-untyped]
        AccountDB,
    )

    summaries: list[dict[str, Any]] = []
    for account in AccountDB.objects.order_by("id"):
        last_login = None
        if account.last_login is not None:
            last_login = account.last_login.isoformat()
        summaries.append(
            {
                "email": account.email or "",
                "id": account.id,
                "is_staff": bool(account.is_staff),
                "is_superuser": bool(account.is_superuser),
                "last_login": last_login,
                "username": account.username,
            }
        )
    return summaries


def create_account(
    game_dir: Path,
    username: str,
    password: str,
    email: str,
    *,
    is_superuser: bool,
) -> dict[str, Any]:
    """Create a new account for the local server."""
    configure_django(game_dir, load_evennia=False)
    _prepare_offline_account_creation()

    from evennia.accounts.models import (  # type: ignore[import-untyped]
        AccountDB,
    )

    account = AccountDB.objects.create_account(
        key=username,
        email=email,
        password=password,
        is_superuser=is_superuser,
    )
    if is_superuser and not account.is_staff:
        account.is_staff = True
        account.save(update_fields=["is_staff"])

    result = {
        "created": True,
        "is_superuser": bool(account.is_superuser),
        "username": account.username,
    }
    if not is_superuser:
        return result

    result.update(_sync_staff_channel_follow_up(game_dir, account.username))
    return result


def set_account_password(
    game_dir: Path,
    username: str,
    password: str,
) -> dict[str, Any]:
    """Reset the password for an existing account."""
    account = _get_account_by_username(game_dir, username)
    account.set_password(password)
    account.save(update_fields=["password"])
    return {
        "password_updated": True,
        "username": account.username,
    }


def verify_account_password(
    game_dir: Path,
    username: str,
    password: str,
) -> dict[str, Any]:
    """Report whether the provided password matches the named account."""
    account = _get_account_by_username(game_dir, username)
    return {
        "password_matches": bool(account.check_password(password)),
        "username": account.username,
    }


def set_account_superuser(
    game_dir: Path,
    username: str,
    is_superuser: bool,
) -> dict[str, Any]:
    """Promote or demote an account's admin flags."""
    account = _get_account_by_username(game_dir, username)
    account.is_superuser = is_superuser
    account.is_staff = is_superuser
    account.save(update_fields=["is_staff", "is_superuser"])

    result = {
        "is_superuser": bool(account.is_superuser),
        "username": account.username,
    }
    result.update(_sync_staff_channel_follow_up(game_dir, account.username))
    return result
