from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time


PRODUCT_ROOT = Path(__file__).resolve().parents[1]
GAME_SOURCE = PRODUCT_ROOT / "src" / "redmond_server" / "game"
PYTHONPATH_DIR = str(PRODUCT_ROOT / "src")
PYTHON_BIN = sys.executable
TEST_PASSWORD_INPUT_ENV = "REDMOND_TEST_PASSWORD_INPUT"
WRAPPER_DISABLE_DEFAULT_CONFIG_ENV = (
    "REDMOND_WRAPPER_DISABLE_DEFAULT_CONFIG"
)


def run_command(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        args,
        cwd=cwd,
        env=full_env,
        check=True,
        text=True,
        input=input_text,
        capture_output=True,
    )


def build_env(game_dir: Path) -> dict[str, str]:
    return {
        "EVENNIA_SUPERUSER_EMAIL": "admin@example.com",
        "EVENNIA_SUPERUSER_USERNAME": "admin",
        "PYTHONPATH": PYTHONPATH_DIR,
        "REDMOND_GAME_DIR": str(game_dir),
        WRAPPER_DISABLE_DEFAULT_CONFIG_ENV: "1",
    }


def load_state(game_dir: Path) -> dict[str, object]:
    result = run_command(
        [
            PYTHON_BIN,
            "-m",
            "redmond_server.bootstrap",
            "state",
            "--game-dir",
            str(game_dir),
        ],
        cwd=PRODUCT_ROOT,
        env={"PYTHONPATH": PYTHONPATH_DIR},
    )
    return json.loads(result.stdout)


def load_doctor(
    game_dir: Path,
    *,
    env: dict[str, str] | None = None,
) -> dict[str, object]:
    result = run_command(
        [
            PYTHON_BIN,
            "-m",
            "redmond_server.bootstrap",
            "doctor",
            "--game-dir",
            str(game_dir),
        ],
        cwd=PRODUCT_ROOT,
        env={"PYTHONPATH": PYTHONPATH_DIR, **(env or {})},
    )
    return json.loads(result.stdout)


def load_runtime_state(game_dir: Path) -> dict[str, object]:
    result = run_command(
        [
            PYTHON_BIN,
            "-m",
            "redmond_server.bootstrap",
            "runtime-state",
            "--game-dir",
            str(game_dir),
        ],
        cwd=PRODUCT_ROOT,
        env={"PYTHONPATH": PYTHONPATH_DIR},
    )
    return json.loads(result.stdout)


def load_backup_status(
    game_dir: Path,
    *,
    env: dict[str, str] | None = None,
) -> dict[str, object]:
    result = run_command(
        [
            PYTHON_BIN,
            "-m",
            "redmond_server.bootstrap",
            "backup-status",
            "--game-dir",
            str(game_dir),
        ],
        cwd=PRODUCT_ROOT,
        env={"PYTHONPATH": PYTHONPATH_DIR, **(env or {})},
    )
    return json.loads(result.stdout)


def load_backup_create(
    game_dir: Path,
    *,
    env: dict[str, str] | None = None,
) -> dict[str, object]:
    result = run_command(
        [
            PYTHON_BIN,
            "-m",
            "redmond_server.bootstrap",
            "backup-create",
            "--game-dir",
            str(game_dir),
        ],
        cwd=PRODUCT_ROOT,
        env={"PYTHONPATH": PYTHONPATH_DIR, **(env or {})},
    )
    return json.loads(result.stdout)


def load_accounts(game_dir: Path) -> list[dict[str, object]]:
    result = run_command(
        [
            PYTHON_BIN,
            "-m",
            "redmond_server.bootstrap",
            "account-list",
            "--game-dir",
            str(game_dir),
        ],
        cwd=PRODUCT_ROOT,
        env={"PYTHONPATH": PYTHONPATH_DIR},
    )
    payload = json.loads(result.stdout)
    accounts = payload["accounts"]
    assert isinstance(accounts, list)
    return [dict(item) for item in accounts]


def account_password_matches(
    game_dir: Path,
    username: str,
    password: str,
) -> bool:
    result = run_command(
        [
            PYTHON_BIN,
            "-m",
            "redmond_server.bootstrap",
            "account-verify-password",
            "--username",
            username,
            "--game-dir",
            str(game_dir),
        ],
        cwd=PRODUCT_ROOT,
        env={
            "PYTHONPATH": PYTHONPATH_DIR,
            TEST_PASSWORD_INPUT_ENV: "1",
        },
        input_text=password + "\n",
    )
    payload = json.loads(result.stdout)
    return bool(payload["password_matches"])


def require_list(state: dict[str, object], key: str) -> list[str]:
    value = state[key]
    assert isinstance(value, list)
    return [str(item) for item in value]


def require_int(state: dict[str, object], key: str) -> int:
    value = state[key]
    assert isinstance(value, int)
    return value


def overwrite_room_name(game_dir: Path, new_name: str) -> None:
    run_command(
        [
            PYTHON_BIN,
            "-m",
            "redmond_server.bootstrap",
            "set-ooc-room-name",
            "--name",
            new_name,
            "--game-dir",
            str(game_dir),
        ],
        cwd=PRODUCT_ROOT,
        env={"PYTHONPATH": PYTHONPATH_DIR},
    )


def create_game_dir() -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="redmond-game-"))
    game_dir = temp_root / "game"
    shutil.copytree(GAME_SOURCE, game_dir)
    sanitize_game_dir(game_dir)
    return game_dir


def sanitize_game_dir(game_dir: Path) -> None:
    runtime_paths = [
        game_dir / "server" / "evennia.db3",
        game_dir / "server" / "conf" / "secret_settings.py",
        game_dir / "server" / "server.pid",
        game_dir / "server" / "portal.pid",
        game_dir / "server" / "server.restart",
        game_dir / "server" / "portal.restart",
        game_dir / "server" / "server.stop",
        game_dir / "server" / "portal.stop",
    ]
    runtime_dirs = [
        game_dir / "server" / "logs",
        game_dir / "server" / "backups",
        game_dir / "server" / ".static",
        game_dir / "server" / ".media",
    ]

    for path in runtime_paths:
        if path.exists():
            path.unlink()
    for path in runtime_dirs:
        if path.exists():
            shutil.rmtree(path)


def cleanup_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    proc.send_signal(signal.SIGKILL)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        time.sleep(0.1)
