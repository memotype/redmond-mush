"""Password input helpers for operator-facing bootstrap commands."""

from __future__ import annotations

import getpass
import os
import sys
from typing import TextIO


TEST_PASSWORD_INPUT_ENV = "REDMOND_TEST_PASSWORD_INPUT"


def _test_mode_enabled() -> bool:
    """Return whether stdin-only password test mode is enabled."""
    return os.environ.get(TEST_PASSWORD_INPUT_ENV) == "1"


def _read_password_from_stdin(stdin: TextIO) -> str:
    """Read a single password value from stdin for explicit test mode."""
    password = stdin.readline()
    if password == "":
        raise RuntimeError(
            "Password input test mode requires a password on stdin."
        )
    return password.rstrip("\r\n")


def read_password(
    prompt: str,
    *,
    confirm: bool,
    stdin: TextIO | None = None,
    is_tty: bool | None = None,
    getpass_func=None,
) -> str:
    """Read one password via secure prompt or stdin-only test mode."""
    resolved_stdin = sys.stdin if stdin is None else stdin
    resolved_is_tty = (
        resolved_stdin.isatty() if is_tty is None else is_tty
    )
    resolved_getpass = (
        getpass.getpass if getpass_func is None else getpass_func
    )

    if _test_mode_enabled():
        return _read_password_from_stdin(resolved_stdin)

    if not resolved_is_tty:
        raise RuntimeError(
            "Password input requires an interactive terminal. "
            f"Use {TEST_PASSWORD_INPUT_ENV}=1 and pipe the password on stdin "
            "only for automated tests."
        )

    password = resolved_getpass(prompt)
    if not confirm:
        return password

    confirmation = resolved_getpass("Confirm password: ")
    if password != confirmation:
        raise RuntimeError("Password confirmation did not match.")
    return password
