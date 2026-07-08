# mypy: ignore-errors
r"""
Evennia settings for the committed Redmond game directory.

Only override the defaults needed for the Milestone 1 local bootstrap.
"""

from evennia.settings_default import *  # noqa: F403
from server.conf._database import build_database_settings
from server.conf._runtime_env import apply_runtime_env_overrides


COMMAND_DEFAULT_CLASS = "commands.command.MuxCommand"
SERVERNAME = "Redmond"

apply_runtime_env_overrides(globals())

try:
    from server.conf.secret_settings import *  # noqa: F403
except ImportError:
    pass

apply_runtime_env_overrides(globals())


DATABASES = build_database_settings()
