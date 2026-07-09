from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from redmond_server import bootstrap

from tests.bootstrap_test_utils import (
    TEST_PASSWORD_INPUT_ENV,
    PRODUCT_ROOT,
    build_env,
    create_game_dir,
    load_accounts,
    run_command,
)


class WrapperConfigIntegrationTest(unittest.TestCase):
    def merged_env(self, extra: dict[str, str]) -> dict[str, str]:
        return {**os.environ, **extra}

    def write_wrapper_config(
        self,
        path: Path,
        *,
        game_dir: Path | str,
        database_url: str | None = None,
        pgbackrest_command: str | None = None,
        stanza: str | None = None,
    ) -> Path:
        lines = [f"REDMOND_GAME_DIR={game_dir}"]
        if database_url is not None:
            lines.append(f"REDMOND_DATABASE_URL={database_url}")
        if pgbackrest_command is not None:
            lines.append(f"REDMOND_PGBACKREST_COMMAND={pgbackrest_command}")
        if stanza is not None:
            lines.append(f"REDMOND_PGBACKREST_STANZA={stanza}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="ascii")
        return path

    def write_fake_pgbackrest(
        self,
        *,
        stdout_text: str = "",
        exit_code: int = 0,
    ) -> Path:
        fake_bin = Path(tempfile.mkdtemp(prefix="redmond-fake-bin-"))
        pgbackrest_path = fake_bin / "pgbackrest"
        pgbackrest_path.write_text(
            "#!/usr/bin/env bash\n"
            f"printf '%s' {stdout_text!r}\n"
            f"exit {exit_code}\n",
            encoding="ascii",
        )
        pgbackrest_path.chmod(0o755)
        return pgbackrest_path

    def test_backup_status_wrapper_accepts_absolute_config_path(self) -> None:
        game_dir = create_game_dir()
        bootstrap.ensure_secret_settings(game_dir)
        repository_dir = (
            game_dir / "server" / "backups" / "postgresql" / "repository"
        )
        metadata_dir = (
            game_dir / "server" / "backups" / "postgresql" / "manifests"
        )
        repository_dir.mkdir(parents=True)
        metadata_dir.mkdir(parents=True)
        config_path = self.write_wrapper_config(
            Path(tempfile.mkdtemp(prefix="redmond-config-"))
            / "redmond.env",
            game_dir=game_dir,
            database_url="postgres://user:secret@127.0.0.1:5432/redmond",
            pgbackrest_command="sh",
        )

        result = run_command(
            [
                "./scripts/backup_status.sh",
                "--config",
                str(config_path),
            ],
            cwd=PRODUCT_ROOT,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["backend"], "postgresql")
        readiness = payload["readiness"]
        assert isinstance(readiness, dict)
        self.assertTrue(readiness["ready_for_read_only_listing"])

    def test_backup_list_wrapper_accepts_relative_config_path(self) -> None:
        game_dir = create_game_dir()
        bootstrap.ensure_secret_settings(game_dir)
        repository_dir = (
            game_dir / "server" / "backups" / "postgresql" / "repository"
        )
        metadata_dir = (
            game_dir / "server" / "backups" / "postgresql" / "manifests"
        )
        repository_dir.mkdir(parents=True)
        metadata_dir.mkdir(parents=True)
        pgbackrest_path = self.write_fake_pgbackrest(
            stdout_text=(
                '[{"name":"redmond","status":{"code":0,"message":"ok"},'
                '"backup":[{"label":"demo-full","type":"full","reference":[],'
                '"error":false,"timestamp":{"start":10,"stop":20}}]}]'
            ),
        )
        cwd = Path(tempfile.mkdtemp(prefix="redmond-wrapper-cwd-"))
        config_path = self.write_wrapper_config(
            cwd / "cfg" / "redmond.env",
            game_dir=game_dir,
            database_url="postgres://user:secret@127.0.0.1:5432/redmond",
            pgbackrest_command=str(pgbackrest_path),
        )

        result = run_command(
            [
                str(PRODUCT_ROOT / "scripts" / "backup_list.sh"),
                "--config",
                os.path.relpath(config_path, cwd),
            ],
            cwd=cwd,
        )

        payload = json.loads(result.stdout)
        restore_points = payload["restore_points"]
        assert isinstance(restore_points, list)
        self.assertEqual(restore_points[0]["label"], "demo-full")

    def test_backup_create_wrapper_uses_default_repo_relative_config(
        self,
    ) -> None:
        copied_product = Path(tempfile.mkdtemp(prefix="redmond-product-"))
        shutil.rmtree(copied_product)
        shutil.copytree(PRODUCT_ROOT, copied_product)
        game_source = create_game_dir()
        game_dir = copied_product / "test-game"
        shutil.copytree(game_source, game_dir)
        bootstrap.ensure_secret_settings(game_dir)
        repository_dir = (
            game_dir / "server" / "backups" / "postgresql" / "repository"
        )
        repository_dir.mkdir(parents=True)
        fake_bin = copied_product / "fake-bin"
        fake_bin.mkdir()
        pgbackrest_path = fake_bin / "pgbackrest"
        pgbackrest_path.write_text(
            "#!/usr/bin/env bash\nexit 0\n",
            encoding="ascii",
        )
        pgbackrest_path.chmod(0o755)
        self.write_wrapper_config(
            copied_product / "config" / "redmond.env",
            game_dir="../test-game",
            database_url="postgres://user:secret@127.0.0.1:5432/redmond",
            pgbackrest_command="../fake-bin/pgbackrest",
        )
        cwd = Path(tempfile.mkdtemp(prefix="redmond-nonrepo-cwd-"))

        result = run_command(
            [str(copied_product / "scripts" / "backup_create.sh")],
            cwd=cwd,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["backend"], "postgresql")
        self.assertEqual(payload["repository_dir"], str(repository_dir))

    def test_backup_status_wrapper_fails_for_missing_explicit_config(
        self,
    ) -> None:
        missing_path = Path(tempfile.mkdtemp(prefix="redmond-config-"))
        result = subprocess.run(
            [
                str(PRODUCT_ROOT / "scripts" / "backup_status.sh"),
                "--config",
                str(missing_path / "missing.env"),
            ],
            cwd=Path(tempfile.mkdtemp(prefix="redmond-wrapper-cwd-")),
            env=self.merged_env({}),
            check=False,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Config file not found", result.stderr)

    def test_account_set_admin_wrapper_preserves_positional_args_with_config(
        self,
    ) -> None:
        game_dir = create_game_dir()
        env = build_env(game_dir)
        run_command(
            ["./scripts/init_local.sh"],
            cwd=PRODUCT_ROOT,
            env={
                **env,
                TEST_PASSWORD_INPUT_ENV: "1",
            },
            input_text="pass123\n",
        )
        config_path = self.write_wrapper_config(
            Path(tempfile.mkdtemp(prefix="redmond-config-"))
            / "redmond.env",
            game_dir=game_dir,
        )

        run_command(
            [
                "./scripts/account_set_admin.sh",
                "--config",
                str(config_path),
                "admin",
                "true",
            ],
            cwd=PRODUCT_ROOT,
        )

        accounts = load_accounts(game_dir)
        admin = next(
            account
            for account in accounts
            if account["username"] == "admin"
        )
        self.assertTrue(admin["is_superuser"])
