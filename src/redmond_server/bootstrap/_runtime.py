"""Runtime-only bootstrap diagnostics."""

from __future__ import annotations

import os
from pathlib import Path
import socket
from typing import Any


def _read_pidfile(path: Path) -> int | None:
    """Return the integer pid from a pidfile when it is valid."""
    if not path.exists():
        return None

    raw_value = path.read_text(encoding="ascii").strip()
    if not raw_value:
        return None

    try:
        return int(raw_value)
    except ValueError:
        return None


def _pid_is_running(pid: int | None) -> bool:
    """Return whether a pid currently exists."""
    if pid is None:
        return False

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True

    proc_stat = Path(f"/proc/{pid}/stat")
    if proc_stat.exists():
        fields = proc_stat.read_text(encoding="utf-8").split()
        if len(fields) >= 3 and fields[2] == "Z":
            return False
    return True


def runtime_state(game_dir: Path) -> dict[str, Any]:
    """Inspect local runtime files without requiring Django setup."""
    server_dir = game_dir / "server"
    pidfile_names = ("server.pid", "portal.pid")
    flag_names = (
        "server.restart",
        "portal.restart",
        "server.stop",
        "portal.stop",
    )

    pidfiles: dict[str, dict[str, Any]] = {}
    running_processes = 0
    stale_pidfiles = 0
    for name in pidfile_names:
        path = server_dir / name
        pid = _read_pidfile(path)
        running = _pid_is_running(pid)
        if path.exists() and not running:
            stale_pidfiles += 1
        if running:
            running_processes += 1
        pidfiles[name] = {
            "exists": path.exists(),
            "pid": pid,
            "process_running": running,
        }

    flags = {name: (server_dir / name).exists() for name in flag_names}
    runtime_marker_present = bool(
        any(flags.values()) or any(info["exists"] for info in pidfiles.values())
    )
    return {
        "game_dir": str(game_dir),
        "pidfiles": pidfiles,
        "restart_or_stop_flags": flags,
        "running_process_count": running_processes,
        "runtime_marker_present": runtime_marker_present,
        "stale_pidfile_count": stale_pidfiles,
    }


def reserve_local_ports(count: int) -> list[int]:
    """Allocate a stable set of local ports for one generated game dir."""
    sockets: list[socket.socket] = []
    ports: list[int] = []
    try:
        for _ in range(count):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(("127.0.0.1", 0))
            sockets.append(sock)
            ports.append(sock.getsockname()[1])
    finally:
        for sock in sockets:
            sock.close()
    return ports
