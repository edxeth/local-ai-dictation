"""Desktop app launch helpers for the Parakeet bridge GUI."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


class DesktopAppError(RuntimeError):
    """Raised when the desktop GUI cannot be launched."""


DEFAULT_BRIDGE_HOST = "127.0.0.1"
DEFAULT_BRIDGE_PORT = 8765


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def desktop_app_dir(root: Path | None = None) -> Path:
    resolved_root = repo_root() if root is None else root
    return resolved_root / "desktop" / "electrobun"


def bridge_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def bridge_start_command(host: str, port: int) -> str:
    return f"parakeet bridge --host {host} --port {port}"


def ensure_bun_available() -> str:
    bun_path = shutil.which("bun")
    if bun_path is None:
        raise DesktopAppError("Parakeet GUI requires Bun. Install Bun, then rerun `parakeet gui`.")
    return bun_path


def ensure_desktop_app_available(app_dir: Path | None = None) -> Path:
    resolved_app_dir = desktop_app_dir() if app_dir is None else app_dir
    if not resolved_app_dir.exists():
        raise DesktopAppError(f"Parakeet GUI app not found at {resolved_app_dir}")
    package_json = resolved_app_dir / "package.json"
    if not package_json.exists():
        raise DesktopAppError(f"Parakeet GUI package manifest not found at {package_json}")
    return resolved_app_dir


def ensure_gui_dependencies(app_dir: Path, bun_path: str) -> None:
    if (app_dir / "node_modules").exists():
        return
    print(f"Installing Parakeet GUI dependencies in {app_dir}...")
    completed = subprocess.run([bun_path, "install"], cwd=app_dir, check=False)
    if completed.returncode != 0:
        raise DesktopAppError("Failed to install Parakeet GUI dependencies with `bun install`.")


def build_gui_environment(host: str, port: int) -> dict[str, str]:
    env = os.environ.copy()
    env["PARAKEET_BRIDGE_URL"] = bridge_url(host, port)
    env["PARAKEET_BRIDGE_COMMAND"] = bridge_start_command(host, port)
    return env


def bridge_healthy(host: str, port: int, *, timeout: float = 1.0) -> bool:
    health_url = f"{bridge_url(host, port)}/health"
    try:
        with urlopen(health_url, timeout=timeout) as response:
            return int(getattr(response, "status", 200)) == 200
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def wait_for_bridge(host: str, port: int, *, timeout_seconds: float = 10.0, poll_interval: float = 0.25) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if bridge_healthy(host, port, timeout=poll_interval):
            return True
        time.sleep(poll_interval)
    return False


def build_bridge_command(namespace: Any) -> list[str]:
    host = str(getattr(namespace, "host", DEFAULT_BRIDGE_HOST))
    port = int(getattr(namespace, "port", DEFAULT_BRIDGE_PORT))
    command = [
        sys.executable,
        "-m",
        "parakeet.cli",
        "bridge",
        "--host",
        host,
        "--port",
        str(port),
        "--max-silence-ms",
        str(int(getattr(namespace, "max_silence_ms", 1200))),
        "--min-speech-ms",
        str(int(getattr(namespace, "min_speech_ms", 300))),
        "--vad-mode",
        str(int(getattr(namespace, "vad_mode", 2))),
        "--log-file",
        str(getattr(namespace, "log_file", "transcriber.debug.log")),
    ]
    if bool(getattr(namespace, "cpu", False)):
        command.append("--cpu")
    input_device = getattr(namespace, "input_device", None)
    if input_device is not None:
        command.extend(["--input-device", str(input_device)])
    if bool(getattr(namespace, "vad", False)):
        command.append("--vad")
    if not bool(getattr(namespace, "clipboard", True)):
        command.append("--no-clipboard")
    if bool(getattr(namespace, "debug", False)):
        command.append("--debug")
    return command


def _run_gui_process(host: str, port: int) -> int:
    bun_path = ensure_bun_available()
    app_dir = ensure_desktop_app_available()
    ensure_gui_dependencies(app_dir, bun_path)
    completed = subprocess.run(
        [bun_path, "run", "start"],
        cwd=app_dir,
        env=build_gui_environment(host, port),
        check=False,
    )
    return int(completed.returncode)


def _stop_process(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_gui_command(namespace: Any) -> int:
    if bool(getattr(namespace, "bridge", False)):
        return run_full_command(namespace)
    host = str(getattr(namespace, "host", DEFAULT_BRIDGE_HOST))
    port = int(getattr(namespace, "port", DEFAULT_BRIDGE_PORT))
    return _run_gui_process(host, port)


def run_full_command(namespace: Any) -> int:
    host = str(getattr(namespace, "host", DEFAULT_BRIDGE_HOST))
    port = int(getattr(namespace, "port", DEFAULT_BRIDGE_PORT))
    started_bridge = False
    bridge_process: subprocess.Popen[Any] | None = None

    if bridge_healthy(host, port):
        print(f"Reusing existing Parakeet bridge at {bridge_url(host, port)}")
    else:
        bridge_process = subprocess.Popen(
            build_bridge_command(namespace),
            cwd=repo_root(),
            env=os.environ.copy(),
        )
        started_bridge = True
        if not wait_for_bridge(host, port):
            exit_code = bridge_process.poll()
            _stop_process(bridge_process)
            if exit_code is None:
                raise DesktopAppError(
                    f"Parakeet bridge did not become ready at {bridge_url(host, port)} within 10 seconds."
                )
            raise DesktopAppError(f"Parakeet bridge exited before becoming ready (exit code {exit_code}).")

    try:
        return _run_gui_process(host, port)
    finally:
        if started_bridge and bridge_process is not None:
            _stop_process(bridge_process)
