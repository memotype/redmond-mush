"""Backup, restore, and migration helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
import shutil
import stat
from pathlib import Path
import subprocess
import tarfile
import tempfile

from ._env import configure_django, load_game_conf_module


BACKUP_MEMBERS = (
    "server/evennia.db3",
    "server/conf/secret_settings.py",
)
BACKUP_MEMBER_SET = set(BACKUP_MEMBERS)


def _database_metadata(game_dir: Path) -> dict[str, object]:
    """Load non-secret database configuration metadata for one game dir."""
    database_module = load_game_conf_module(game_dir, "_database")
    return dict(database_module.describe_database_config(game_dir=game_dir))


def _backup_contract(game_dir: Path) -> dict[str, object]:
    """Load the effective backup contract for one game dir."""
    backup_module = load_game_conf_module(game_dir, "_backup")
    return dict(backup_module.describe_backup_contract(game_dir=game_dir))


def _require_sqlite_local_recovery(game_dir: Path) -> None:
    """Reject local backup helpers when PostgreSQL is configured."""
    metadata = _database_metadata(game_dir)
    engine = metadata["engine"]
    if engine != "sqlite":
        raise RuntimeError(
            "SQLite-local recovery commands are available only for "
            "SQLite-backed dev/test runs. PostgreSQL production backup "
            "and restore are not implemented in this slice."
        )


def _set_owner_only_dir(path: Path) -> None:
    """Apply owner-only permissions to one directory path."""
    path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)


def _set_owner_only_file(path: Path) -> None:
    """Apply owner-only permissions to one file path."""
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def _require_postgresql_backup_contract(
    game_dir: Path,
) -> dict[str, object]:
    """Return the PostgreSQL contract or reject unsupported backends."""
    contract = _backup_contract(game_dir)
    if contract["backend"] != "postgresql":
        raise RuntimeError(
            "PostgreSQL backup creation is available only for "
            "PostgreSQL-backed configurations."
        )
    return contract


def _require_persistent_files_ready(
    contract: dict[str, object],
) -> list[dict[str, object]]:
    """Validate the configured persistent-file entries."""
    entries = contract["persistent_files"]
    if not isinstance(entries, list):
        raise RuntimeError("Persistent-file contract metadata is invalid.")

    validated_entries: list[dict[str, object]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("Persistent-file contract entry is invalid.")
        validated_entry = dict(entry)
        if not bool(validated_entry.get("valid")):
            relative_path = str(validated_entry.get("relative_path", ""))
            reason = str(validated_entry.get("reason", "invalid path"))
            raise RuntimeError(
                "PostgreSQL backup creation requires valid persistent-file "
                f"entries. {relative_path}: {reason}"
            )
        if not bool(validated_entry.get("exists")):
            relative_path = str(validated_entry.get("relative_path", ""))
            raise RuntimeError(
                "PostgreSQL backup creation requires existing persistent "
                f"files. Missing: {relative_path}"
            )
        if not bool(validated_entry.get("is_file")):
            relative_path = str(validated_entry.get("relative_path", ""))
            raise RuntimeError(
                "PostgreSQL backup creation requires persistent-file "
                f"entries to be regular files: {relative_path}"
            )
        validated_entries.append(validated_entry)
    return validated_entries


def _require_repository_dir(path: Path) -> None:
    """Require the configured pgBackRest repository directory to exist."""
    if not path.is_dir():
        raise RuntimeError(
            "PostgreSQL backup creation requires an existing pgBackRest "
            f"repository directory: {path}"
        )


def _require_pgbackrest_command(command: str) -> str:
    """Resolve the configured pgBackRest command or reject it."""
    resolved = shutil.which(command)
    if resolved is None:
        raise RuntimeError(f"pgBackRest command not found: {command}")
    return resolved


def _run_pgbackrest_backup(
    *,
    command: str,
    repository_dir: Path,
    stanza: str,
) -> None:
    """Run the first PostgreSQL backup-create mutation surface."""
    try:
        result = subprocess.run(
            [
                command,
                "backup",
                "--type=full",
                "--stanza",
                stanza,
                "--repo1-path",
                str(repository_dir),
            ],
            check=False,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"pgBackRest command not found: {command}"
        ) from exc

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if stderr:
            raise RuntimeError(f"pgBackRest backup failed: {stderr}")
        raise RuntimeError(
            f"pgBackRest backup failed with exit code {result.returncode}."
        )


def _metadata_filename(created_at: datetime) -> str:
    """Return the Redmond backup metadata filename for one run."""
    stamp = created_at.strftime("%Y%m%dT%H%M%S.%fZ")
    return f"backup-{stamp}.json"


def _write_backup_metadata(
    metadata_dir: Path,
    payload: dict[str, object],
) -> Path:
    """Persist one Redmond-owned metadata snapshot for a backup run."""
    metadata_dir.mkdir(parents=True, exist_ok=True)
    _set_owner_only_dir(metadata_dir)
    created_at_text = str(payload["created_at"])
    created_at = datetime.strptime(
        created_at_text,
        "%Y-%m-%dT%H:%M:%S.%fZ",
    ).replace(tzinfo=UTC)
    metadata_path = metadata_dir / _metadata_filename(created_at)
    metadata_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="ascii",
    )
    _set_owner_only_file(metadata_path)
    return metadata_path


def _required_member_paths(game_dir: Path) -> dict[str, Path]:
    """Return the required local recovery members for one game dir."""
    return {
        member_name: game_dir / member_name
        for member_name in BACKUP_MEMBERS
    }


def create_backup(game_dir: Path, backup_dir: Path) -> Path:
    """Create a backup archive for the local database and secrets."""
    _require_sqlite_local_recovery(game_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    _set_owner_only_dir(backup_dir)
    required_paths = _required_member_paths(game_dir)
    missing_members = [
        member_name
        for member_name, source_path in required_paths.items()
        if not source_path.exists()
    ]
    if missing_members:
        missing_text = ", ".join(missing_members)
        raise RuntimeError(
            f"SQLite-local backup requires existing files: {missing_text}"
        )

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    archive_path = backup_dir / f"redmond-local-{timestamp}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        for member_name, source_path in required_paths.items():
            archive.add(source_path, arcname=member_name)
    _set_owner_only_file(archive_path)
    return archive_path


def create_postgresql_backup(game_dir: Path) -> dict[str, object]:
    """Create one PostgreSQL full backup through the pgBackRest contract."""
    contract = _require_postgresql_backup_contract(game_dir)
    persistent_files = _require_persistent_files_ready(contract)
    repository_dir = Path(str(contract["repository_dir"]))
    metadata_dir = Path(str(contract["metadata_dir"]))
    _require_repository_dir(repository_dir)
    pgbackrest_command = _require_pgbackrest_command(
        str(contract["pgbackrest_command"])
    )
    stanza = str(contract["pgbackrest_stanza"])

    _run_pgbackrest_backup(
        command=pgbackrest_command,
        repository_dir=repository_dir,
        stanza=stanza,
    )

    created_at = datetime.now(UTC)
    metadata_payload: dict[str, object] = {
        "backend": "postgresql",
        "backup_type": "full",
        "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "metadata_dir": str(metadata_dir),
        "persistent_files": persistent_files,
        "pgbackrest": {
            "command": pgbackrest_command,
            "invocation_succeeded": True,
            "repository_dir": str(repository_dir),
            "stanza": stanza,
        },
        "repository_dir": str(repository_dir),
        "stanza": stanza,
    }
    metadata_path = _write_backup_metadata(metadata_dir, metadata_payload)

    return {
        "backend": "postgresql",
        "backup_type": "full",
        "metadata_dir": str(metadata_dir),
        "metadata_path": str(metadata_path),
        "persistent_files": persistent_files,
        "pgbackrest_command": pgbackrest_command,
        "repository_dir": str(repository_dir),
        "stanza": stanza,
    }


def restore_backup(game_dir: Path, archive_path: Path) -> None:
    """Restore a backup archive into the local game directory."""
    _require_sqlite_local_recovery(game_dir)
    if not archive_path.exists():
        raise FileNotFoundError(f"Backup archive not found: {archive_path}")

    required_paths = _required_member_paths(game_dir)
    with tarfile.open(archive_path, "r:gz") as archive:
        members_by_name: dict[str, tarfile.TarInfo] = {}
        for member in archive.getmembers():
            member_name = str(Path(member.name))
            if member_name not in BACKUP_MEMBER_SET:
                raise RuntimeError(f"Unexpected backup member: {member.name}")
            if not member.isfile():
                raise RuntimeError(
                    f"Backup member must be a regular file: {member.name}"
                )
            members_by_name[member_name] = member

        missing_members = sorted(
            BACKUP_MEMBER_SET.difference(members_by_name.keys())
        )
        if missing_members:
            missing_text = ", ".join(missing_members)
            raise RuntimeError(
                f"Backup archive is missing required members: {missing_text}"
            )

        with tempfile.TemporaryDirectory(
            prefix="redmond-restore-",
            dir=game_dir,
        ) as temp_root_text:
            temp_root = Path(temp_root_text)
            archive.extractall(path=temp_root, filter="data")

            staged_paths = {
                member_name: temp_root / member_name
                for member_name in BACKUP_MEMBERS
            }
            missing_staged = [
                member_name
                for member_name, staged_path in staged_paths.items()
                if not staged_path.is_file()
            ]
            if missing_staged:
                missing_text = ", ".join(missing_staged)
                raise RuntimeError(
                    "Backup archive did not extract the expected files: "
                    f"{missing_text}"
                )

            for member_name, target_path in required_paths.items():
                target_path.parent.mkdir(parents=True, exist_ok=True)
                staged_paths[member_name].replace(target_path)

    secret_settings_path = required_paths["server/conf/secret_settings.py"]
    _set_owner_only_file(secret_settings_path)


def run_migrations(game_dir: Path) -> None:
    """Apply Django migrations without going through the Evennia launcher."""
    configure_django(game_dir, load_evennia=False)

    from django.core.management import (  # type: ignore[import-untyped]
        call_command,
    )

    call_command("migrate", interactive=False, verbosity=0)
