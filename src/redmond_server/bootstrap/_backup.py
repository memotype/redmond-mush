"""Backup, restore, and migration helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import tarfile

from ._env import configure_django


BACKUP_MEMBERS = (
    "server/evennia.db3",
    "server/conf/secret_settings.py",
)


def create_backup(game_dir: Path, backup_dir: Path) -> Path:
    """Create a backup archive for the local database and secrets."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    archive_path = backup_dir / f"redmond-local-{timestamp}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        for member in BACKUP_MEMBERS:
            source_path = game_dir / member
            if source_path.exists():
                archive.add(source_path, arcname=member)
    return archive_path


def restore_backup(game_dir: Path, archive_path: Path) -> None:
    """Restore a backup archive into the local game directory."""
    if not archive_path.exists():
        raise FileNotFoundError(f"Backup archive not found: {archive_path}")

    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            member_name = str(Path(member.name))
            if member_name not in BACKUP_MEMBERS:
                raise RuntimeError(f"Unexpected backup member: {member.name}")

        for member_name in BACKUP_MEMBERS:
            target_path = game_dir / member_name
            if target_path.exists():
                target_path.unlink()

        archive.extractall(path=game_dir, filter="data")


def run_migrations(game_dir: Path) -> None:
    """Apply Django migrations without going through the Evennia launcher."""
    configure_django(game_dir, load_evennia=False)

    from django.core.management import (  # type: ignore[import-untyped]
        call_command,
    )

    call_command("migrate", interactive=False, verbosity=0)
