"""Audio device enumeration helpers for Parakeet."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Mapping

from parakeet.types import AudioDevice


PyAudioModule = Any


def _load_pyaudio_module(pyaudio_module: PyAudioModule | None = None) -> PyAudioModule:
    if pyaudio_module is not None:
        return pyaudio_module

    import pyaudio

    return pyaudio


def _default_input_device_id(pa: Any) -> int | None:
    try:
        info = pa.get_default_input_device_info()
    except Exception:
        return None

    try:
        return int(info.get("index"))
    except Exception:
        return None


def _host_api_name(pa: Any, info: dict[str, Any]) -> str:
    try:
        host_api_index = int(info.get("hostApi", -1))
        host_api_info = pa.get_host_api_info_by_index(host_api_index)
        return str(host_api_info.get("name", "unknown"))
    except Exception:
        return "unknown"


def list_input_devices(pyaudio_module: PyAudioModule | None = None) -> list[AudioDevice]:
    pyaudio_module = _load_pyaudio_module(pyaudio_module)
    pa = pyaudio_module.PyAudio()
    try:
        default_input_id = _default_input_device_id(pa)
        devices: list[AudioDevice] = []
        for index in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(index)
            max_input_channels = int(info.get("maxInputChannels", 0))
            if max_input_channels <= 0:
                continue

            device_id = int(info.get("index", index))
            devices.append(
                AudioDevice(
                    id=device_id,
                    name=str(info.get("name", "unknown")),
                    default_sample_rate=int(info.get("defaultSampleRate", 0)),
                    max_input_channels=max_input_channels,
                    host_api=_host_api_name(pa, info),
                    is_default_candidate=(default_input_id is not None and device_id == default_input_id),
                )
            )

        return sorted(devices, key=lambda device: device.id)
    finally:
        pa.terminate()


_CONNECTION_FAILURE_MARKERS = (
    "connection refused",
    "connection failure",
    "failed to connect",
    "timed out",
    "timeout",
)


def _classify_probe_failure(output: str) -> str:
    lowered = output.lower()
    if any(marker in lowered for marker in _CONNECTION_FAILURE_MARKERS):
        return "unreachable"
    return "unknown"


def probe_audio_backend(
    *,
    env: Mapping[str, str] | None = None,
    pactl_timeout: float = 1.5,
    wslg_socket_path: Path = Path("/mnt/wslg/PulseServer"),
) -> dict[str, str]:
    source = os.environ if env is None else env
    pulse_server = source.get("PULSE_SERVER")
    has_wslg_socket = wslg_socket_path.exists()

    if pulse_server and pulse_server.startswith("tcp:"):
        transport = "tcp"
    elif (pulse_server and pulse_server.startswith("unix:")) or has_wslg_socket:
        transport = "unix"
    elif pulse_server:
        transport = "unknown"
    else:
        transport = "none"

    pactl_path = shutil.which("pactl")
    if pactl_path is None:
        return {
            "status": "binary_missing",
            "transport": transport,
            "detail": "pactl binary is not installed",
        }

    if not pulse_server and not has_wslg_socket:
        return {
            "status": "not_configured",
            "transport": "none",
            "detail": "PULSE_SERVER is unset and the WSLg Pulse socket is unavailable",
        }

    if transport == "unknown":
        return {
            "status": "unknown",
            "transport": "unknown",
            "detail": f"Unsupported PULSE_SERVER transport: {pulse_server}",
        }

    probe_env = dict(source)
    if not pulse_server and has_wslg_socket:
        probe_env["PULSE_SERVER"] = f"unix:{wslg_socket_path}"

    try:
        completed = subprocess.run(
            [pactl_path, "info"],
            capture_output=True,
            env=probe_env,
            text=True,
            timeout=pactl_timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "unreachable",
            "transport": transport,
            "detail": f"pactl info timed out after {pactl_timeout:.1f}s",
        }
    except OSError as exc:
        return {
            "status": "unknown",
            "transport": transport,
            "detail": str(exc),
        }

    if completed.returncode == 0:
        return {
            "status": "reachable",
            "transport": transport,
            "detail": "pactl info succeeded",
        }

    combined_output = "\n".join(part for part in [completed.stdout.strip(), completed.stderr.strip()] if part)
    status = _classify_probe_failure(combined_output)
    return {
        "status": status,
        "transport": transport,
        "detail": combined_output or f"pactl info exited with status {completed.returncode}",
    }
