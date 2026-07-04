"""World bootstrap and inspection helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ._env import configure_django, load_game_conf_module
from ._runtime import runtime_state
from ._types import BootstrapState


def _load_game_text() -> Any:
    """Import the Redmond text constants from the game tree."""
    from world import game_text  # type: ignore[import-not-found]

    return game_text


def _database_metadata(game_dir: Path) -> dict[str, Any]:
    """Load non-secret database configuration metadata for one game dir."""
    database_module = load_game_conf_module(game_dir, "_database")
    return dict(database_module.describe_database_config(game_dir=game_dir))


def _database_file_exists(metadata: dict[str, Any]) -> bool | None:
    """Return file-based existence only for SQLite-backed configurations."""
    sqlite_path = metadata.get("sqlite_path")
    if sqlite_path is None:
        return None
    return Path(str(sqlite_path)).exists()


def current_state(game_dir: Path) -> BootstrapState:
    """Read current account and object counts from the migrated database."""
    database = _database_metadata(game_dir)
    configure_django(game_dir, load_evennia=False)

    from evennia.accounts.models import (  # type: ignore[import-untyped]
        AccountDB,
    )
    from evennia.objects.models import (  # type: ignore[import-untyped]
        ObjectDB,
    )

    secret_settings_path = game_dir / "server" / "conf" / "secret_settings.py"
    return BootstrapState(
        account_count=AccountDB.objects.count(),
        object_count=ObjectDB.objects.count(),
        superuser_count=AccountDB.objects.filter(is_superuser=True).count(),
        db_exists=_database_file_exists(database),
        secret_settings_exists=secret_settings_path.exists(),
    )


def ensure_channel(
    key: str,
    aliases: list[str],
    desc: str,
    typeclass_path: str,
):
    """Create or update a named channel."""
    import evennia  # type: ignore[import-untyped]

    matches = evennia.search_channel(key)
    if matches:
        channel = matches[0]
    else:
        channel = evennia.create_channel(
            key=key,
            aliases=aliases,
            desc=desc,
            typeclass=typeclass_path,
        )

    channel.db.desc = desc
    for alias in aliases:
        if alias not in channel.aliases.all():
            channel.aliases.add(alias)
    channel.save()
    return channel


def sync_staff_channel_membership(game_dir: Path, username: str) -> None:
    """Connect or disconnect one account from the staff channel."""
    configure_django(game_dir, load_evennia=True)

    import evennia  # type: ignore[import-untyped]
    from evennia.accounts.models import (  # type: ignore[import-untyped]
        AccountDB,
    )

    account = AccountDB.objects.filter(username__iexact=username).first()
    if account is None:
        raise RuntimeError(f"Account not found: {username}")

    game_text = _load_game_text()
    matches = evennia.search_channel(game_text.STAFF_CHANNEL_KEY)
    if not matches:
        return

    staff_channel = matches[0]
    if account.is_superuser:
        if not staff_channel.has_connection(account):
            staff_channel.connect(account)
    elif staff_channel.has_connection(account):
        staff_channel.disconnect(account)


def ensure_seeded_world(game_dir: Path) -> dict[str, Any]:
    """Apply idempotent Redmond baseline world setup."""
    configure_django(game_dir, load_evennia=True)

    import evennia  # type: ignore[import-untyped]
    from django.conf import settings  # type: ignore[import-untyped]
    from evennia.accounts.models import (  # type: ignore[import-untyped]
        AccountDB,
    )
    from evennia.comms.models import ChannelDB  # type: ignore[import-untyped]
    from evennia.help.filehelp import (  # type: ignore[import-untyped]
        FILE_HELP_ENTRIES,
    )
    from evennia.objects.models import (  # type: ignore[import-untyped]
        ObjectDB,
    )

    game_text = _load_game_text()
    room_matches = evennia.search_object("#2")
    if not room_matches:
        raise RuntimeError("Expected Evennia room #2 after bootstrap.")

    ooc_room = room_matches[0]
    ooc_room.swap_typeclass(
        settings.BASE_ROOM_TYPECLASS,
        clean_attributes=False,
    )
    ooc_room.key = game_text.OOC_ROOM_NAME
    ooc_room.db.desc = game_text.OOC_ROOM_DESC
    ooc_room.attributes.add("room_role", "ooc_hub")
    ooc_room.save()

    public_channel = ensure_channel(
        key=game_text.PUBLIC_CHANNEL_KEY,
        aliases=game_text.PUBLIC_CHANNEL_ALIASES,
        desc=game_text.PUBLIC_CHANNEL_DESC,
        typeclass_path=settings.BASE_CHANNEL_TYPECLASS,
    )
    staff_channel = ensure_channel(
        key=game_text.STAFF_CHANNEL_KEY,
        aliases=game_text.STAFF_CHANNEL_ALIASES,
        desc=game_text.STAFF_CHANNEL_DESC,
        typeclass_path=settings.BASE_CHANNEL_TYPECLASS,
    )

    for account in AccountDB.objects.all():
        if not public_channel.has_connection(account):
            public_channel.connect(account)

    for account in AccountDB.objects.filter(is_superuser=True):
        if not staff_channel.has_connection(account):
            staff_channel.connect(account)

    FILE_HELP_ENTRIES.load()
    legal_matches = [
        entry for entry in FILE_HELP_ENTRIES.all()
        if entry.key.lower().strip() == "legal"
    ]
    if len(legal_matches) != 1:
        raise RuntimeError(
            "Expected exactly one file-backed 'legal' help entry."
        )

    return {
        "account_count": AccountDB.objects.count(),
        "channel_count": ChannelDB.objects.count(),
        "legal_help_count": len(legal_matches),
        "object_count": ObjectDB.objects.count(),
        "ooc_room_key": ooc_room.key,
    }


def set_ooc_room_name(
    game_dir: Path,
    name: str,
) -> dict[str, Any]:
    """Set the baseline OOC room key for local maintenance or verification."""
    configure_django(game_dir, load_evennia=True)

    import evennia  # type: ignore[import-untyped]

    room_matches = evennia.search_object("#2")
    if not room_matches:
        raise RuntimeError("Expected Evennia room #2 after bootstrap.")

    room = room_matches[0]
    room.key = name
    room.save(update_fields=["db_key"])
    return {"ooc_room_key": room.key}


def run_initial_setup(game_dir: Path) -> dict[str, Any]:
    """Create Evennia's baseline world objects without starting services."""
    if current_state(game_dir).initial_world_ready:
        return dump_state(game_dir)

    configure_django(game_dir, load_evennia=True)

    from evennia.server import initial_setup  # type: ignore[import-untyped]
    from evennia.server.models import (  # type: ignore[import-untyped]
        ServerConfig,
    )

    initial_setup.create_objects()
    initial_setup.at_initial_setup()
    initial_setup.collectstatic()
    ServerConfig.objects.conf("last_initial_setup_step", "done")
    return dump_state(game_dir)


def dump_state(game_dir: Path) -> dict[str, Any]:
    """Collect current bootstrap-visible state for tests and debugging."""
    database = _database_metadata(game_dir)
    configure_django(game_dir, load_evennia=True)

    import evennia  # type: ignore[import-untyped]
    from evennia.comms.models import ChannelDB  # type: ignore[import-untyped]
    from evennia.help.filehelp import (  # type: ignore[import-untyped]
        FILE_HELP_ENTRIES,
    )

    state = current_state(game_dir)
    room_matches = evennia.search_object("#2")
    FILE_HELP_ENTRIES.load()
    legal_help_count = len(
        [
            entry for entry in FILE_HELP_ENTRIES.all()
            if entry.key.lower().strip() == "legal"
        ]
    )
    return {
        "account_count": state.account_count,
        "channel_keys": sorted(
            channel.key for channel in ChannelDB.objects.all()
        ),
        "database": database,
        "db_exists": state.db_exists,
        "legal_help_count": legal_help_count,
        "object_count": state.object_count,
        "ooc_room_key": room_matches[0].key if room_matches else None,
        "runtime": runtime_state(game_dir),
        "secret_settings_exists": state.secret_settings_exists,
        "superuser_count": state.superuser_count,
        "world_ready": state.initial_world_ready,
    }


def diagnostic_state(game_dir: Path) -> dict[str, Any]:
    """Collect local diagnostics without assuming a healthy database state."""
    database = _database_metadata(game_dir)
    diagnostics = {
        "database": database,
        "db_exists": _database_file_exists(database),
        "runtime": runtime_state(game_dir),
        "secret_settings_exists": (
            game_dir / "server" / "conf" / "secret_settings.py"
        ).exists(),
    }
    try:
        state = dump_state(game_dir)
    except Exception as exc:  # pragma: no cover - shell path exercise
        diagnostics["database_error"] = f"{type(exc).__name__}: {exc}"
        return diagnostics

    diagnostics.update(state)
    diagnostics["database_error"] = None
    return diagnostics
