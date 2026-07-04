# mypy: ignore-errors
r"""
Evennia settings for the committed Redmond game directory.

Only override the defaults needed for the Milestone 1 local bootstrap.
"""

from evennia.settings_default import *  # noqa: F403
from server.conf._database import build_database_settings


COMMAND_DEFAULT_CLASS = "commands.command.MuxCommand"
SERVERNAME = "Redmond"


try:
    from server.conf.secret_settings import *  # noqa: F403
except ImportError:
    print("secret_settings.py file not found or failed to import.")


DATABASES = build_database_settings()
