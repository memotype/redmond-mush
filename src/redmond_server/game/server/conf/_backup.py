"""Backup contract helpers for the committed Redmond game dir."""

from __future__ import annotations

import os
from pathlib import Path

from redmond_server.game.server.conf import _database


DEFAULT_BACKUP_ROOT_RELATIVE = Path("server/backups")
DEFAULT_PGBACKREST_COMMAND = "pgbackrest"
DEFAULT_PGBACKREST_STANZA = "redmond"
POSTGRESQL_METADATA_RELATIVE = Path("postgresql/manifests")
POSTGRESQL_REPOSITORY_RELATIVE = Path("postgresql/repository")
PERSISTENT_FILE_MANIFEST = (
    "server/conf/secret_settings.py",
)


def _trimmed_env(name: str, raw_value: str | None = None) -> str | None:
    """Return a trimmed env override value or None when unset."""
    if raw_value is None:
        raw_value = os.environ.get(name)
    if raw_value is None:
        return None
    value = raw_value.strip()
    return value or None


def _resolve_backup_root(
    *,
    game_dir: Path,
    raw_backup_dir: str | None = None,
) -> tuple[Path, str]:
    """Return the effective backup root path and source metadata."""
    override = _trimmed_env("REDMOND_BACKUP_DIR", raw_backup_dir)
    if override is None:
        return game_dir / DEFAULT_BACKUP_ROOT_RELATIVE, "default"
    return Path(override).expanduser().resolve(), "env_override"


def _resolve_pgbackrest_command(
    raw_command: str | None = None,
) -> tuple[str, str]:
    """Return the effective pgBackRest command and source metadata."""
    override = _trimmed_env("REDMOND_PGBACKREST_COMMAND", raw_command)
    if override is None:
        return DEFAULT_PGBACKREST_COMMAND, "default"
    return override, "env_override"


def _resolve_pgbackrest_stanza(
    raw_stanza: str | None = None,
) -> tuple[str, str]:
    """Return the effective pgBackRest stanza and source metadata."""
    override = _trimmed_env("REDMOND_PGBACKREST_STANZA", raw_stanza)
    if override is None:
        return DEFAULT_PGBACKREST_STANZA, "default"
    return override, "env_override"


def backup_backend_mode(
    raw_database_url: str | None = None,
    *,
    game_dir: Path | None = None,
) -> str:
    """Return the effective backup backend mode for the current config."""
    metadata = _database.describe_database_config(
        raw_url=raw_database_url,
        game_dir=game_dir,
    )
    if metadata["engine"] == "postgresql":
        return "postgresql"
    return "sqlite_local"


def persistent_file_entries(
    *,
    game_dir: Path,
    manifest_entries: tuple[str, ...] | None = None,
) -> list[dict[str, object]]:
    """Describe the resolved persistent non-database file contract."""
    entries = manifest_entries or PERSISTENT_FILE_MANIFEST
    resolved_game_dir = game_dir.resolve()
    described: list[dict[str, object]] = []
    for raw_entry in entries:
        entry_text = str(raw_entry)
        candidate = Path(entry_text)
        if candidate.is_absolute():
            described.append(
                {
                    "absolute_path": None,
                    "exists": False,
                    "is_file": False,
                    "reason": "absolute paths are not allowed",
                    "relative_path": entry_text,
                    "source": "default",
                    "valid": False,
                }
            )
            continue

        resolved_path = (resolved_game_dir / candidate).resolve()
        try:
            resolved_path.relative_to(resolved_game_dir)
        except ValueError:
            described.append(
                {
                    "absolute_path": str(resolved_path),
                    "exists": False,
                    "is_file": False,
                    "reason": "path escapes the game dir",
                    "relative_path": entry_text,
                    "source": "default",
                    "valid": False,
                }
            )
            continue

        exists = resolved_path.exists()
        is_file = resolved_path.is_file()
        reason = None
        if not exists:
            reason = "missing file"
        elif not is_file:
            reason = "path is not a file"

        described.append(
            {
                "absolute_path": str(resolved_path),
                "exists": exists,
                "is_file": is_file,
                "reason": reason,
                "relative_path": entry_text,
                "source": "default",
                "valid": True,
            }
        )
    return described


def describe_backup_contract(
    raw_database_url: str | None = None,
    *,
    game_dir: Path | None = None,
    raw_backup_dir: str | None = None,
    raw_command: str | None = None,
    raw_stanza: str | None = None,
    manifest_entries: tuple[str, ...] | None = None,
) -> dict[str, object]:
    """Return the effective backup contract for diagnostics and tests."""
    resolved_game_dir = _database.resolve_game_dir(game_dir)
    backend = backup_backend_mode(
        raw_database_url=raw_database_url,
        game_dir=resolved_game_dir,
    )
    backup_root, backup_root_source = _resolve_backup_root(
        game_dir=resolved_game_dir,
        raw_backup_dir=raw_backup_dir,
    )
    pgbackrest_command, pgbackrest_command_source = (
        _resolve_pgbackrest_command(raw_command)
    )
    pgbackrest_stanza, pgbackrest_stanza_source = (
        _resolve_pgbackrest_stanza(raw_stanza)
    )
    repository_dir = backup_root / POSTGRESQL_REPOSITORY_RELATIVE
    metadata_dir = backup_root / POSTGRESQL_METADATA_RELATIVE
    persistent_files = persistent_file_entries(
        game_dir=resolved_game_dir,
        manifest_entries=manifest_entries,
    )

    return {
        "backend": backend,
        "backup_root": str(backup_root),
        "backup_root_source": backup_root_source,
        "game_dir": str(resolved_game_dir),
        "metadata_dir": str(metadata_dir),
        "metadata_dir_source": "derived",
        "persistent_files": persistent_files,
        "pgbackrest_command": pgbackrest_command,
        "pgbackrest_command_source": pgbackrest_command_source,
        "pgbackrest_stanza": pgbackrest_stanza,
        "pgbackrest_stanza_source": pgbackrest_stanza_source,
        "postgresql_inspection_eligible": backend == "postgresql",
        "repository_dir": str(repository_dir),
        "repository_dir_source": "derived",
    }
