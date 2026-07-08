"""Bootstrap helpers for the Redmond Evennia game tree."""

from __future__ import annotations

from ._accounts import (
    create_account,
    ensure_superuser,
    list_accounts,
    set_account_password,
    set_account_superuser,
    verify_account_password,
)
from ._backup import (
    create_backup,
    create_postgresql_backup,
    restore_backup,
    run_migrations,
)
from ._backup_contract import backup_list, backup_status
from ._cli import build_parser, main, print_json
from ._env import configure_django, ensure_secret_settings, game_dir_arg
from ._runtime import reserve_local_ports, runtime_state
from ._types import AccountState, BootstrapState
from ._world import (
    current_state,
    diagnostic_state,
    dump_state,
    ensure_seeded_world,
    set_ooc_room_name,
)
from ._world import run_initial_setup

__all__ = [
    "AccountState",
    "BootstrapState",
    "build_parser",
    "backup_list",
    "backup_status",
    "configure_django",
    "current_state",
    "create_account",
    "create_backup",
    "create_postgresql_backup",
    "diagnostic_state",
    "dump_state",
    "ensure_secret_settings",
    "ensure_seeded_world",
    "ensure_superuser",
    "game_dir_arg",
    "list_accounts",
    "main",
    "print_json",
    "reserve_local_ports",
    "restore_backup",
    "run_initial_setup",
    "run_migrations",
    "runtime_state",
    "set_account_password",
    "set_account_superuser",
    "set_ooc_room_name",
    "verify_account_password",
]
