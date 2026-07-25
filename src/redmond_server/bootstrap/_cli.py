"""CLI dispatch for the bootstrap facade."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
from pathlib import Path
from typing import Any

from ._accounts import (
    create_account,
    ensure_superuser,
    list_accounts,
    set_account_password,
    set_account_superuser,
    verify_account_password,
)
from ._chargen import create_sample_chargen_session
from ._backup import (
    create_backup,
    create_postgresql_backup,
    restore_backup,
    run_migrations,
)
from ._backup_contract import backup_list, backup_status
from ._env import ensure_secret_settings, game_dir_arg
from ._passwords import read_password
from ._sheets import create_sample_sheet
from ._world import (
    current_state,
    diagnostic_state,
    dump_state,
    ensure_seeded_world,
    set_ooc_room_name,
)
from ._world import run_initial_setup


def print_json(data: dict[str, Any]) -> None:
    """Serialize structured state for shell scripts and tests."""
    print(json.dumps(data, indent=2, sort_keys=True))


def collect_quietly(callback, *args):
    """Run a bootstrap collector while suppressing incidental stdout noise."""
    with contextlib.redirect_stdout(io.StringIO()):
        return callback(*args)


def _sample_command_exit_code(payload: dict[str, Any]) -> int:
    """Return the process exit code for opt-in sample-data commands."""
    status = str(payload.get("status", ""))
    if status in ("created", "exists"):
        return 0
    return 1


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for bootstrap operations."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "--game-dir",
        required=True,
        type=game_dir_arg,
    )

    subparsers.add_parser(
        "ensure-secret-settings",
        parents=[common_parser],
    )

    ensure_superuser_parser = subparsers.add_parser(
        "ensure-superuser",
        parents=[common_parser],
    )
    ensure_superuser_parser.add_argument("--username", required=True)
    ensure_superuser_parser.add_argument("--email", default="")

    account_list_parser = subparsers.add_parser(
        "account-list",
        parents=[common_parser],
    )
    account_list_parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
    )

    account_create_parser = subparsers.add_parser(
        "account-create",
        parents=[common_parser],
    )
    account_create_parser.add_argument("--username", required=True)
    account_create_parser.add_argument("--email", default="")
    account_create_parser.add_argument(
        "--superuser",
        action="store_true",
    )

    account_password_parser = subparsers.add_parser(
        "account-set-password",
        parents=[common_parser],
    )
    account_password_parser.add_argument("--username", required=True)

    account_verify_parser = subparsers.add_parser(
        "account-verify-password",
        parents=[common_parser],
    )
    account_verify_parser.add_argument("--username", required=True)

    account_superuser_parser = subparsers.add_parser(
        "account-set-superuser",
        parents=[common_parser],
    )
    account_superuser_parser.add_argument("--username", required=True)
    account_superuser_parser.add_argument(
        "--value",
        choices=("true", "false"),
        required=True,
    )

    subparsers.add_parser("needs-initial-start", parents=[common_parser])
    subparsers.add_parser("initial-world-ready", parents=[common_parser])
    subparsers.add_parser("has-superuser", parents=[common_parser])
    subparsers.add_parser("seed", parents=[common_parser])
    subparsers.add_parser("runtime-state", parents=[common_parser])
    ooc_room_parser = subparsers.add_parser(
        "set-ooc-room-name",
        parents=[common_parser],
    )
    ooc_room_parser.add_argument("--name", required=True)
    subparsers.add_parser("state", parents=[common_parser])
    subparsers.add_parser("doctor", parents=[common_parser])
    subparsers.add_parser("initial-setup", parents=[common_parser])
    subparsers.add_parser("migrate", parents=[common_parser])
    subparsers.add_parser("backup-status", parents=[common_parser])
    subparsers.add_parser("backup-list", parents=[common_parser])
    subparsers.add_parser("backup-create", parents=[common_parser])
    sheet_sample_parser = subparsers.add_parser(
        "sheet-create-sample",
        parents=[common_parser],
    )
    sheet_sample_parser.add_argument("--character", required=True)
    sheet_sample_parser.add_argument(
        "--allow-dev-sample-data",
        action="store_true",
    )
    chargen_sample_parser = subparsers.add_parser(
        "chargen-create-sample",
        parents=[common_parser],
    )
    chargen_sample_parser.add_argument("--character", required=True)
    chargen_sample_parser.add_argument("--profile-key")
    chargen_sample_parser.add_argument("--version", type=int)
    chargen_sample_parser.add_argument(
        "--allow-dev-sample-data",
        action="store_true",
    )

    backup_parser = subparsers.add_parser(
        "backup",
        parents=[common_parser],
    )
    backup_parser.add_argument(
        "--backup-dir",
        required=True,
        type=Path,
    )

    restore_parser = subparsers.add_parser(
        "restore",
        parents=[common_parser],
    )
    restore_parser.add_argument(
        "--archive",
        required=True,
        type=Path,
    )
    return parser


def main() -> int:
    """Run the requested bootstrap command."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "ensure-secret-settings":
        path = ensure_secret_settings(args.game_dir)
        print(path)
        return 0

    if args.command == "ensure-superuser":
        password = read_password(
            f"Bootstrap superuser password for {args.username}: ",
            confirm=True,
        )
        username = ensure_superuser(
            game_dir=args.game_dir,
            username=args.username,
            password=password,
            email=args.email,
        )
        print(username)
        return 0

    if args.command == "account-list":
        accounts = list_accounts(args.game_dir)
        if args.format == "text":
            for account in accounts:
                print(
                    "\t".join(
                        [
                            str(account["id"]),
                            account["username"],
                            account["email"],
                            (
                                "superuser"
                                if account["is_superuser"]
                                else "account"
                            ),
                        ]
                    )
                )
        else:
            print_json({"accounts": accounts})
        return 0

    if args.command == "account-create":
        password = read_password(
            f"Password for new account {args.username}: ",
            confirm=True,
        )
        print_json(
            create_account(
                game_dir=args.game_dir,
                username=args.username,
                password=password,
                email=args.email,
                is_superuser=args.superuser,
            )
        )
        return 0

    if args.command == "account-set-password":
        password = read_password(
            f"New password for {args.username}: ",
            confirm=True,
        )
        print_json(
            set_account_password(
                game_dir=args.game_dir,
                username=args.username,
                password=password,
            )
        )
        return 0

    if args.command == "account-verify-password":
        password = read_password(
            f"Password for {args.username}: ",
            confirm=False,
        )
        print_json(
            verify_account_password(
                game_dir=args.game_dir,
                username=args.username,
                password=password,
            )
        )
        return 0

    if args.command == "account-set-superuser":
        print_json(
            set_account_superuser(
                game_dir=args.game_dir,
                username=args.username,
                is_superuser=(args.value == "true"),
            )
        )
        return 0

    if args.command == "needs-initial-start":
        state = current_state(args.game_dir)
        return 0 if state.needs_initial_start else 1

    if args.command == "initial-world-ready":
        state = current_state(args.game_dir)
        return 0 if state.initial_world_ready else 1

    if args.command == "has-superuser":
        state = current_state(args.game_dir)
        return 0 if state.superuser_count > 0 else 1

    if args.command == "seed":
        print_json(ensure_seeded_world(args.game_dir))
        return 0

    if args.command == "runtime-state":
        from ._runtime import runtime_state

        print_json(runtime_state(args.game_dir))
        return 0

    if args.command == "set-ooc-room-name":
        print_json(
            set_ooc_room_name(
                game_dir=args.game_dir,
                name=args.name,
            )
        )
        return 0

    if args.command == "initial-setup":
        print_json(run_initial_setup(args.game_dir))
        return 0

    if args.command == "state":
        print_json(dump_state(args.game_dir))
        return 0

    if args.command == "doctor":
        print_json(collect_quietly(diagnostic_state, args.game_dir))
        return 0

    if args.command == "backup-status":
        print_json(backup_status(args.game_dir))
        return 0

    if args.command == "backup-list":
        print_json(backup_list(args.game_dir))
        return 0

    if args.command == "backup-create":
        print_json(create_postgresql_backup(args.game_dir))
        return 0

    if args.command == "sheet-create-sample":
        payload = create_sample_sheet(
            game_dir=args.game_dir,
            character_name=args.character,
            allow_dev_sample_data=args.allow_dev_sample_data,
        )
        print_json(payload)
        return _sample_command_exit_code(payload)

    if args.command == "chargen-create-sample":
        payload = create_sample_chargen_session(
            game_dir=args.game_dir,
            character_name=args.character,
            allow_dev_sample_data=args.allow_dev_sample_data,
            profile_key=args.profile_key,
            version=args.version,
        )
        print_json(payload)
        return _sample_command_exit_code(payload)

    if args.command == "migrate":
        run_migrations(args.game_dir)
        return 0

    if args.command == "backup":
        archive_path = create_backup(args.game_dir, args.backup_dir)
        print(archive_path)
        return 0

    if args.command == "restore":
        restore_backup(args.game_dir, args.archive)
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2
