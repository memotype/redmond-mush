"""Bootstrap environment and Django setup helpers."""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import secrets
import stat
import sys
from types import ModuleType

DEFAULT_SETTINGS_MODULE = "server.conf.settings"
SECRET_PLACEHOLDER = "__REDMOND_SECRET_KEY__"
DEFAULT_TELNET_PORT = 4000
DEFAULT_WEBSERVER_PROXY_PORT = 4001
DEFAULT_WEBSOCKET_CLIENT_PORT = 4002
DEFAULT_SSL_PORT = 4003
DEFAULT_SSH_PORT = 4004
DEFAULT_INTERNAL_WEBSERVER_PORT = 4005
DEFAULT_AMP_PORT = 4006


def game_dir_arg(raw_path: str) -> Path:
    """Parse and validate a game directory CLI argument."""
    path = Path(raw_path).resolve()
    if not path.exists():
        raise argparse.ArgumentTypeError(f"Game dir does not exist: {path}")
    return path


def ensure_secret_settings(game_dir: Path) -> Path:
    """Create secret settings from the tracked template if missing."""
    conf_dir = game_dir / "server" / "conf"
    template_path = conf_dir / "secret_settings.example.py"
    target_path = conf_dir / "secret_settings.py"
    if target_path.exists():
        return target_path

    template_text = template_path.read_text(encoding="ascii")
    secret_key = secrets.token_urlsafe(48)
    target_text = template_text.replace(SECRET_PLACEHOLDER, secret_key)
    target_text += "\n"
    target_text += f"TELNET_PORTS = [{DEFAULT_TELNET_PORT}]\n"
    target_text += (
        "WEBSERVER_PORTS = "
        f"[({DEFAULT_WEBSERVER_PROXY_PORT}, "
        f"{DEFAULT_INTERNAL_WEBSERVER_PORT})]\n"
    )
    target_text += (
        "WEBSOCKET_CLIENT_PORT = "
        f"{DEFAULT_WEBSOCKET_CLIENT_PORT}\n"
    )
    target_text += f"SSL_PORTS = [{DEFAULT_SSL_PORT}]\n"
    target_text += f"SSH_PORTS = [{DEFAULT_SSH_PORT}]\n"
    target_text += f"AMP_PORT = {DEFAULT_AMP_PORT}\n"
    target_path.write_text(target_text, encoding="ascii")
    target_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return target_path


def load_game_conf_module(game_dir: Path, module_name: str) -> ModuleType:
    """Load one game-dir config module without importing the whole package."""
    module_path = game_dir / "server" / "conf" / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(
        f"redmond_game_conf_{module_name}_{abs(hash(module_path))}",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load config module: {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure_django(game_dir: Path, *, load_evennia: bool) -> None:
    """Initialize Django and, optionally, Evennia for the given game dir."""
    os.chdir(game_dir)
    game_dir_text = str(game_dir)
    if game_dir_text not in sys.path:
        sys.path.insert(0, game_dir_text)
    os.environ["DJANGO_SETTINGS_MODULE"] = DEFAULT_SETTINGS_MODULE

    import django  # type: ignore[import-untyped]

    django.setup()
    if load_evennia:
        import evennia  # type: ignore[import-untyped]

        evennia._init()
