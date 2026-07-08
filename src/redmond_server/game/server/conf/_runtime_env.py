"""Runtime environment helpers for the committed game dir."""

from __future__ import annotations

import os
from typing import Any


def runtime_secret_key(raw_value: str | None = None) -> str | None:
    """Return the trimmed runtime secret key when one is configured."""
    if raw_value is None:
        raw_value = os.environ.get("REDMOND_SECRET_KEY")
    if raw_value is None:
        return None
    value = raw_value.strip()
    if not value:
        return None
    return value


def apply_runtime_env_overrides(
    namespace: dict[str, Any],
    *,
    raw_secret_key: str | None = None,
) -> None:
    """Apply supported runtime env overrides to one settings namespace."""
    secret_key = runtime_secret_key(raw_secret_key)
    if secret_key is not None:
        namespace["SECRET_KEY"] = secret_key
