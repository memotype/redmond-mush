"""Read-only PostgreSQL backup contract inspection helpers."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

from ._env import load_game_conf_module


def _backup_contract(game_dir: Path) -> dict[str, object]:
    """Load the effective backup contract from the game-dir config."""
    backup_module = load_game_conf_module(game_dir, "_backup")
    return dict(backup_module.describe_backup_contract(game_dir=game_dir))


def backup_status(game_dir: Path) -> dict[str, object]:
    """Return read-only backup contract status for the current backend."""
    contract = _backup_contract(game_dir)
    command = str(contract["pgbackrest_command"])
    command_available = shutil.which(command) is not None
    repository_dir = Path(str(contract["repository_dir"]))
    metadata_dir = Path(str(contract["metadata_dir"]))
    persistent_files = contract["persistent_files"]
    assert isinstance(persistent_files, list)

    persistent_paths_valid = all(
        bool(entry["valid"]) for entry in persistent_files
    )
    persistent_paths_ready = all(
        bool(entry["valid"]) and bool(entry["exists"]) and bool(entry["is_file"])
        for entry in persistent_files
    )
    inspection_eligible = bool(contract["postgresql_inspection_eligible"])
    ready_for_listing = (
        inspection_eligible
        and command_available
        and repository_dir.is_dir()
        and metadata_dir.is_dir()
        and persistent_paths_valid
        and persistent_paths_ready
    )
    status = "not_applicable"
    if inspection_eligible and ready_for_listing:
        status = "ready_for_read_only_listing"
    elif inspection_eligible:
        status = "configured_not_ready"

    return {
        "backend": contract["backend"],
        "config": contract,
        "pgbackrest": {
            "available": command_available,
            "resolved_command": command,
        },
        "readiness": {
            "metadata_dir_exists": metadata_dir.is_dir(),
            "persistent_paths_ready": persistent_paths_ready,
            "persistent_paths_valid": persistent_paths_valid,
            "postgresql_inspection_eligible": inspection_eligible,
            "ready_for_read_only_listing": ready_for_listing,
            "repository_dir_exists": repository_dir.is_dir(),
            "status": status,
        },
    }


def _require_postgresql_inspection(contract: dict[str, object]) -> None:
    """Reject read-only PostgreSQL listing when the backend is SQLite."""
    if not bool(contract["postgresql_inspection_eligible"]):
        raise RuntimeError(
            "PostgreSQL backup listing is available only for "
            "PostgreSQL-backed configurations."
        )


def _run_pgbackrest_info(
    *,
    command: str,
    repository_dir: Path,
    stanza: str,
) -> list[dict[str, object]]:
    """Run pgBackRest info in read-only mode and return parsed JSON."""
    try:
        result = subprocess.run(
            [
                command,
                "info",
                "--output=json",
                "--repo1-path",
                str(repository_dir),
                "--stanza",
                stanza,
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
            raise RuntimeError(f"pgBackRest info failed: {stderr}")
        raise RuntimeError(
            f"pgBackRest info failed with exit code {result.returncode}."
        )

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "pgBackRest info returned invalid JSON output."
        ) from exc

    if not isinstance(payload, list):
        raise RuntimeError("pgBackRest info JSON must be a list.")

    return [dict(entry) for entry in payload]


def _first_matching_stanza(
    payload: list[dict[str, object]],
    stanza: str,
) -> dict[str, object]:
    """Return the requested stanza payload from pgBackRest info JSON."""
    for entry in payload:
        if entry.get("name") == stanza:
            return entry
    raise RuntimeError(f"pgBackRest info did not include stanza {stanza!r}.")


def _optional_text(value: object) -> str | None:
    """Return an optional string field from parsed pgBackRest JSON."""
    if value is None:
        return None
    return str(value)


def _optional_int(value: object) -> int | None:
    """Return an optional int field from parsed pgBackRest JSON."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise RuntimeError("Expected integer metadata, got boolean.")
    if isinstance(value, int):
        return value
    raise RuntimeError("Expected integer metadata from pgBackRest info.")


def _restore_points(backup_entries: object) -> list[dict[str, object]]:
    """Normalize pgBackRest backup entries into Redmond restore points."""
    if not isinstance(backup_entries, list):
        raise RuntimeError("pgBackRest stanza backup list is invalid.")

    restore_points: list[dict[str, object]] = []
    for entry in backup_entries:
        if not isinstance(entry, dict):
            raise RuntimeError("pgBackRest backup entry must be an object.")
        archive = entry.get("archive")
        timestamp = entry.get("timestamp")
        database = entry.get("database")
        references = entry.get("reference", [])
        if archive is not None and not isinstance(archive, dict):
            raise RuntimeError("pgBackRest archive metadata is invalid.")
        if timestamp is not None and not isinstance(timestamp, dict):
            raise RuntimeError("pgBackRest timestamp metadata is invalid.")
        if database is not None and not isinstance(database, dict):
            raise RuntimeError("pgBackRest database metadata is invalid.")
        if not isinstance(references, list):
            raise RuntimeError("pgBackRest reference metadata is invalid.")

        restore_points.append(
            {
                "archive_start": _optional_text(
                    None if archive is None else archive.get("start")
                ),
                "archive_stop": _optional_text(
                    None if archive is None else archive.get("stop")
                ),
                "database_id": _optional_int(
                    None if database is None else database.get("id")
                ),
                "database_repo_key": _optional_int(
                    None if database is None else database.get("repo-key")
                ),
                "error": bool(entry.get("error", False)),
                "label": _optional_text(entry.get("label")),
                "reference": [str(item) for item in references],
                "timestamp_start": _optional_int(
                    None if timestamp is None else timestamp.get("start")
                ),
                "timestamp_stop": _optional_int(
                    None if timestamp is None else timestamp.get("stop")
                ),
                "type": _optional_text(entry.get("type")),
            }
        )
    return restore_points


def backup_list(game_dir: Path) -> dict[str, object]:
    """List PostgreSQL restore points from pgBackRest info output."""
    contract = _backup_contract(game_dir)
    _require_postgresql_inspection(contract)
    repository_dir = Path(str(contract["repository_dir"]))
    metadata_dir = Path(str(contract["metadata_dir"]))
    pgbackrest_command = str(contract["pgbackrest_command"])
    stanza = str(contract["pgbackrest_stanza"])
    payload = _run_pgbackrest_info(
        command=pgbackrest_command,
        repository_dir=repository_dir,
        stanza=stanza,
    )
    stanza_entry = _first_matching_stanza(payload, stanza)
    status = stanza_entry.get("status", {})
    if not isinstance(status, dict):
        raise RuntimeError("pgBackRest stanza status metadata is invalid.")

    return {
        "backend": contract["backend"],
        "metadata_dir": str(metadata_dir),
        "pgbackrest_command": pgbackrest_command,
        "repository_dir": str(repository_dir),
        "restore_points": _restore_points(stanza_entry.get("backup", [])),
        "stanza": stanza,
        "stanza_status": {
            "code": _optional_int(status.get("code")),
            "message": _optional_text(status.get("message")),
        },
    }
