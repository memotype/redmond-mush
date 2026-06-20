# mypy: ignore-errors
"""Connection screens shown before login."""

from django.conf import settings

from evennia import utils

from world.game_text import LOGIN_LEGAL_NOTICE


CONNECTION_SCREEN = """
|b==============================================================|n
 Welcome to |g{}|n, version {}!

 {}

 If you already have an account, type:
      |wconnect <username> <password>|n
 If you need a new account, type:
      |wcreate <username> <password>|n

 Type |whelp|n for more info. Type |wlook|n to re-show this screen.
|b==============================================================|n
""".format(
    settings.SERVERNAME,
    utils.get_evennia_version("short"),
    LOGIN_LEGAL_NOTICE,
)
