# mypy: ignore-errors
"""Connection screens shown before login."""

from pathlib import Path
import random

from evennia import utils

from world.game_text import LOGIN_LEGAL_NOTICE


TITLE_CARD_DIR = Path(__file__).with_name("title_cards")
DEFAULT_TITLE_CARD = """
|b  ____          _                         |n
|b |  _ \\ ___  __| |_ __ ___   ___  _ __   |n
|g | |_) / _ \\/ _` | '_ ` _ \\ / _ \\| '_ \\  |n
|g |  _ <  __/ (_| | | | | | | (_) | | | | |n
|w |_| \\_\\___|\\__,_|_| |_| |_|\\___/|_| |_| |n
""".strip()


def load_title_cards(title_card_dir: Path | None = None) -> list[str]:
    """Load non-empty title-card text files from the configured directory."""
    resolved_dir = TITLE_CARD_DIR if title_card_dir is None else title_card_dir
    title_cards: list[str] = []
    if not resolved_dir.is_dir():
        return title_cards

    for path in sorted(resolved_dir.glob("*.txt")):
        if not path.is_file():
            continue
        title_card = path.read_text(encoding="ascii").strip("\n")
        if title_card:
            title_cards.append(title_card)
    return title_cards


def choose_title_card() -> str:
    """Choose a title card or fall back to the built-in default."""
    title_cards = load_title_cards()
    if not title_cards:
        return DEFAULT_TITLE_CARD
    return random.choice(title_cards)


def connection_screen() -> str:
    """Build the current connection screen for an unlogged-in session."""
    return """
|b==============================================================|n
{}

 {}

 Version {}.

 If you already have an account, type:
      |wconnect <username> <password>|n
 If you need a new account, type:
      |wcreate <username> <password>|n

 Type |whelp|n for more info. Type |wlook|n to re-show this screen.
|b==============================================================|n
""".format(
        choose_title_card(),
        LOGIN_LEGAL_NOTICE,
        utils.get_evennia_version("short"),
    )
