"""Database configuration helpers for the committed Redmond game dir."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured


DEFAULT_POSTGRES_PORT = 5432
SUPPORTED_POSTGRES_SCHEMES = {"postgres", "postgresql"}


def resolve_game_dir(game_dir: Path | None = None) -> Path:
    """Return the current Evennia game dir for this settings tree."""
    if game_dir is not None:
        return game_dir.resolve()
    return Path(__file__).resolve().parents[2]


def sqlite_database_path(game_dir: Path | None = None) -> Path:
    """Return the explicit local SQLite database path."""
    return resolve_game_dir(game_dir) / "server" / "evennia.db3"


def sqlite_database_settings(
    game_dir: Path | None = None,
) -> dict[str, dict[str, object]]:
    """Return the explicit default SQLite DATABASES mapping."""
    return {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(sqlite_database_path(game_dir)),
        }
    }


def normalize_database_url(raw_url: str | None = None) -> str | None:
    """Return the normalized database URL or None when unset."""
    if raw_url is None:
        raw_url = os.environ.get("REDMOND_DATABASE_URL")
    if raw_url is None:
        return None
    value = raw_url.strip()
    return value or None


def parse_database_url(raw_url: str) -> dict[str, dict[str, object]]:
    """Parse one supported PostgreSQL database URL into Django settings."""
    parsed = urlsplit(raw_url)
    scheme = parsed.scheme.lower()
    if scheme not in SUPPORTED_POSTGRES_SCHEMES:
        raise ImproperlyConfigured(
            "REDMOND_DATABASE_URL must use postgres:// or postgresql://."
        )
    if parsed.query:
        raise ImproperlyConfigured(
            "REDMOND_DATABASE_URL query parameters are not supported."
        )
    if not parsed.username:
        raise ImproperlyConfigured(
            "REDMOND_DATABASE_URL must include a username."
        )
    if not parsed.hostname:
        raise ImproperlyConfigured(
            "REDMOND_DATABASE_URL must include a hostname."
        )

    database_name = parsed.path.lstrip("/")
    if not database_name:
        raise ImproperlyConfigured(
            "REDMOND_DATABASE_URL must include a database name."
        )
    if "/" in database_name:
        raise ImproperlyConfigured(
            "REDMOND_DATABASE_URL must include one database name segment."
        )

    return {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": parsed.hostname,
            "NAME": unquote(database_name),
            "PASSWORD": unquote(parsed.password) if parsed.password else "",
            "PORT": parsed.port or DEFAULT_POSTGRES_PORT,
            "USER": unquote(parsed.username),
        }
    }


def build_database_settings(
    raw_url: str | None = None,
    *,
    game_dir: Path | None = None,
) -> dict[str, dict[str, object]]:
    """Return the effective Django DATABASES mapping for Redmond."""
    normalized_url = normalize_database_url(raw_url)
    if normalized_url is None:
        return sqlite_database_settings(game_dir)
    return parse_database_url(normalized_url)


def describe_database_config(
    raw_url: str | None = None,
    *,
    game_dir: Path | None = None,
) -> dict[str, object]:
    """Return non-secret metadata for diagnostics and tests."""
    normalized_url = normalize_database_url(raw_url)
    if normalized_url is None:
        return {
            "database_name": None,
            "engine": "sqlite",
            "host": None,
            "port": None,
            "source": "sqlite_default",
            "sqlite_path": str(sqlite_database_path(game_dir)),
        }

    settings = parse_database_url(normalized_url)["default"]
    return {
        "database_name": settings["NAME"],
        "engine": "postgresql",
        "host": settings["HOST"],
        "port": settings["PORT"],
        "source": "env_url",
        "sqlite_path": None,
    }
