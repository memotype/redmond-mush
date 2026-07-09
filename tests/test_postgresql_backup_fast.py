from __future__ import annotations

import json
from pathlib import Path
import os
import stat
import subprocess
import tempfile
import unittest
from unittest import mock

from redmond_server import bootstrap
from redmond_server.bootstrap import _backup

from tests.bootstrap_test_utils import create_game_dir, load_backup_create


class PostgreSQLBackupFastTest(unittest.TestCase):
    def assert_owner_only_mode(self, path: Path) -> None:
        self.assertEqual(
            stat.S_IMODE(path.stat().st_mode),
            stat.S_IRUSR | stat.S_IWUSR,
        )

    def test_postgresql_backup_create_rejects_sqlite_mode(self) -> None:
        game_dir = create_game_dir()

        with self.assertRaisesRegex(
            RuntimeError,
            "PostgreSQL backup creation",
        ):
            bootstrap.create_postgresql_backup(game_dir)

    def test_postgresql_backup_create_rejects_missing_command(self) -> None:
        game_dir = create_game_dir()
        bootstrap.ensure_secret_settings(game_dir)
        repository_dir = (
            game_dir / "server" / "backups" / "postgresql" / "repository"
        )
        repository_dir.mkdir(parents=True)

        with mock.patch.dict(
            os.environ,
            {
                "REDMOND_DATABASE_URL": (
                    "postgres://user:pass@db.example:5432/redmond"
                ),
                "REDMOND_PGBACKREST_COMMAND": "missing-pgbackrest-binary",
            },
            clear=False,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "pgBackRest command not found",
            ):
                bootstrap.create_postgresql_backup(game_dir)

    def test_postgresql_backup_create_rejects_missing_persistent_files(
        self,
    ) -> None:
        game_dir = create_game_dir()
        repository_dir = (
            game_dir / "server" / "backups" / "postgresql" / "repository"
        )
        repository_dir.mkdir(parents=True)

        with mock.patch.dict(
            os.environ,
            {
                "REDMOND_DATABASE_URL": (
                    "postgres://user:pass@db.example:5432/redmond"
                ),
                "REDMOND_PGBACKREST_COMMAND": "sh",
            },
            clear=False,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "existing persistent files",
            ):
                bootstrap.create_postgresql_backup(game_dir)

    def test_postgresql_backup_create_rejects_missing_repository_dir(
        self,
    ) -> None:
        game_dir = create_game_dir()
        bootstrap.ensure_secret_settings(game_dir)

        with mock.patch.dict(
            os.environ,
            {
                "REDMOND_DATABASE_URL": (
                    "postgres://user:pass@db.example:5432/redmond"
                ),
                "REDMOND_PGBACKREST_COMMAND": "sh",
            },
            clear=False,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "repository directory",
            ):
                bootstrap.create_postgresql_backup(game_dir)

    def test_postgresql_backup_create_writes_metadata_snapshot(self) -> None:
        game_dir = create_game_dir()
        bootstrap.ensure_secret_settings(game_dir)
        repository_dir = (
            game_dir / "server" / "backups" / "postgresql" / "repository"
        )
        repository_dir.mkdir(parents=True)

        with mock.patch.dict(
            os.environ,
            {
                "REDMOND_DATABASE_URL": (
                    "postgres://user:pass@db.example:5432/redmond"
                )
            },
            clear=False,
        ):
            with mock.patch.object(
                _backup.shutil,
                "which",
                return_value="/usr/bin/pgbackrest",
            ):
                with mock.patch.object(
                    _backup.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess(
                        args=[],
                        returncode=0,
                        stdout="",
                        stderr="",
                    ),
                ):
                    payload = bootstrap.create_postgresql_backup(game_dir)

        metadata_dir = Path(str(payload["metadata_dir"]))
        metadata_path = Path(str(payload["metadata_path"]))
        self.assertTrue(metadata_dir.is_dir())
        self.assertEqual(
            stat.S_IMODE(metadata_dir.stat().st_mode),
            stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR,
        )
        self.assertTrue(metadata_path.is_file())
        self.assert_owner_only_mode(metadata_path)
        saved_payload = json.loads(metadata_path.read_text(encoding="ascii"))
        self.assertEqual(saved_payload["backend"], "postgresql")
        self.assertEqual(saved_payload["backup_type"], "full")
        pgbackrest = saved_payload["pgbackrest"]
        assert isinstance(pgbackrest, dict)
        self.assertTrue(pgbackrest["invocation_succeeded"])

    def test_postgresql_backup_create_bubbles_up_pgbackrest_stderr(
        self,
    ) -> None:
        game_dir = create_game_dir()
        bootstrap.ensure_secret_settings(game_dir)
        repository_dir = (
            game_dir / "server" / "backups" / "postgresql" / "repository"
        )
        repository_dir.mkdir(parents=True)

        with mock.patch.dict(
            os.environ,
            {
                "REDMOND_DATABASE_URL": (
                    "postgres://user:pass@db.example:5432/redmond"
                )
            },
            clear=False,
        ):
            with mock.patch.object(
                _backup.shutil,
                "which",
                return_value="/usr/bin/pgbackrest",
            ):
                with mock.patch.object(
                    _backup.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess(
                        args=[],
                        returncode=1,
                        stdout="",
                        stderr="permission denied\n",
                    ),
                ):
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "permission denied",
                    ):
                        bootstrap.create_postgresql_backup(game_dir)

    def test_backup_create_cli_returns_json(self) -> None:
        game_dir = create_game_dir()
        bootstrap.ensure_secret_settings(game_dir)
        repository_dir = (
            game_dir / "server" / "backups" / "postgresql" / "repository"
        )
        repository_dir.mkdir(parents=True)
        fake_bin = Path(tempfile.mkdtemp(prefix="redmond-fake-bin-"))
        pgbackrest_path = fake_bin / "pgbackrest"
        pgbackrest_path.write_text(
            "#!/usr/bin/env bash\nexit 0\n",
            encoding="ascii",
        )
        pgbackrest_path.chmod(0o755)

        payload = load_backup_create(
            game_dir,
            env={
                "REDMOND_DATABASE_URL": (
                    "postgres://user:pass@db.example:5432/redmond"
                ),
                "REDMOND_PGBACKREST_COMMAND": str(pgbackrest_path),
            },
        )

        self.assertEqual(payload["backend"], "postgresql")
        self.assertEqual(payload["backup_type"], "full")
        self.assertIn("metadata_path", payload)
