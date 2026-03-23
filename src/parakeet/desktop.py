"""Desktop app launch helpers for the Parakeet bridge GUI."""

from __future__ import annotations

import hashlib
import json
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


def ensure_windows_interop_command(command_name: str) -> str:
    command_path = shutil.which(command_name)
    if command_path is None:
        raise DesktopAppError(f"Windows staging requires `{command_name}` to be available from WSL.")
    return command_path


def run_text_command(command: list[str]) -> str:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        raise DesktopAppError(stderr or f"Command failed: {' '.join(command)}")
    return completed.stdout.strip()


def read_windows_env_var(name: str) -> str:
    cmd_exe = ensure_windows_interop_command("cmd.exe")
    value = run_text_command([cmd_exe, "/c", "echo", f"%{name}%"])
    if not value or value == f"%{name}%":
        raise DesktopAppError(f"Windows environment variable `{name}` is not available from WSL.")
    return value.splitlines()[-1].strip()


def wsl_path_from_windows(path: str) -> Path:
    wslpath = ensure_windows_interop_command("wslpath")
    return Path(run_text_command([wslpath, "-u", path]))


def windows_path_from_wsl(path: Path) -> str:
    wslpath = ensure_windows_interop_command("wslpath")
    return run_text_command([wslpath, "-w", str(path)])


def windows_stage_root() -> Path:
    local_appdata = read_windows_env_var("LOCALAPPDATA")
    return wsl_path_from_windows(local_appdata) / "ParakeetDictation" / "staging"


def stage_windows_desktop_app(app_dir: Path | None = None) -> dict[str, str]:
    source_app_dir = ensure_desktop_app_available(app_dir)
    source_root = source_app_dir.parents[2]
    digest = hashlib.sha256(str(source_root).encode("utf-8")).hexdigest()[:12]
    stage_root = windows_stage_root() / f"{source_root.name}-{digest}"
    stage_app_dir = stage_root / "desktop" / "electrobun"
    if stage_root.exists():
        shutil.rmtree(stage_root)
    stage_app_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source_app_dir,
        stage_app_dir,
        ignore=shutil.ignore_patterns("node_modules", ".tmp-check", "dist"),
    )
    return {
        "source_app_dir": str(source_app_dir),
        "stage_root": str(stage_root),
        "desktop_app_dir": str(stage_app_dir),
        "windows_stage_root": windows_path_from_wsl(stage_root),
        "windows_desktop_app_dir": windows_path_from_wsl(stage_app_dir),
    }


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


def run_gui_stage_command(namespace: Any) -> int:
    payload = stage_windows_desktop_app()
    if bool(getattr(namespace, "json_output", False)):
        print(json.dumps(payload))
        return 0
    print(f"Staged desktop app at {payload['desktop_app_dir']}")
    print(payload["windows_desktop_app_dir"])
    return 0


def ensure_windows_bun_available() -> str:
    cmd_exe = ensure_windows_interop_command("cmd.exe")
    output = run_text_command([cmd_exe, "/d", "/c", "where", "bun"])
    bun_path = output.splitlines()[0].strip() if output else ""
    if not bun_path:
        raise DesktopAppError("Windows packaging requires `bun.exe` to be available on the Windows PATH.")
    return bun_path


def find_windows_powershell() -> str | None:
    powershell_path = shutil.which("powershell.exe")
    if powershell_path is not None:
        return powershell_path
    fallback = Path("/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")
    if fallback.exists():
        return str(fallback)
    return None


def run_windows_in_dir(windows_dir: str, commands: list[str]) -> None:
    powershell_path = find_windows_powershell()
    if powershell_path is not None:
        escaped_dir = windows_dir.replace("'", "''")
        script_parts = [f"Set-Location -LiteralPath '{escaped_dir}'"]
        for command in commands:
            script_parts.append(command)
            script_parts.append("if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }")
        completed = subprocess.run(
            [
                powershell_path,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "; ".join(script_parts),
            ],
            check=False,
        )
    else:
        cmd_exe = ensure_windows_interop_command("cmd.exe")
        completed = subprocess.run(
            [cmd_exe, "/c", f"cd /d {windows_dir} && {' && '.join(commands)}"],
            check=False,
        )
    if completed.returncode != 0:
        raise DesktopAppError(f"Windows command failed in {windows_dir}: {' && '.join(commands)}")


def collect_windows_package_artifacts(app_dir: Path) -> dict[str, str]:
    build_dir = app_dir / "build" / "stable-win-x64"
    if not build_dir.exists():
        raise DesktopAppError(f"Windows build output not found at {build_dir}")

    installer_path = next(build_dir.glob("*-Setup.exe"), None)
    if installer_path is None:
        raise DesktopAppError(f"Windows installer not found in {build_dir}")

    metadata_path = next(build_dir.glob("*-Setup.metadata.json"), None)
    if metadata_path is None:
        raise DesktopAppError(f"Windows installer metadata not found in {build_dir}")

    archive_path = next(build_dir.glob("*-Setup.tar.zst"), None)
    if archive_path is None:
        raise DesktopAppError(f"Windows installer archive not found in {build_dir}")

    zip_path = next((app_dir / "artifacts").glob("stable-win-x64-*-Setup.zip"), None)
    if zip_path is None:
        raise DesktopAppError(f"Windows packaged artifact zip not found in {app_dir / 'artifacts'}")

    return {
        "build_dir": str(build_dir),
        "windows_build_dir": windows_path_from_wsl(build_dir),
        "installer_path": str(installer_path),
        "windows_installer_path": windows_path_from_wsl(installer_path),
        "setup_archive_path": str(archive_path),
        "windows_setup_archive_path": windows_path_from_wsl(archive_path),
        "metadata_path": str(metadata_path),
        "windows_metadata_path": windows_path_from_wsl(metadata_path),
        "artifact_zip_path": str(zip_path),
        "windows_artifact_zip_path": windows_path_from_wsl(zip_path),
    }


def run_gui_package_command(namespace: Any) -> int:
    ensure_windows_bun_available()
    payload = stage_windows_desktop_app()
    windows_app_dir = payload["windows_desktop_app_dir"]
    run_windows_in_dir(windows_app_dir, ["bun install", "bunx electrobun build --env=stable"])
    payload.update(collect_windows_package_artifacts(Path(payload["desktop_app_dir"])))
    if bool(getattr(namespace, "json_output", False)):
        print(json.dumps(payload))
        return 0
    print(f"Packaged Windows desktop app at {payload['installer_path']}")
    print(payload["windows_installer_path"])
    return 0


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
