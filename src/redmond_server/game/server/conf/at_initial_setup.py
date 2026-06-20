# mypy: ignore-errors
"""Keep Evennia first-start hooks thin for Redmond bootstrap."""


def at_initial_setup() -> None:
    """Leave Redmond setup to explicit bootstrap scripts."""
    return None
