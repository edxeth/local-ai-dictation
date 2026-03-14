"""Audio device enumeration helpers for Parakeet."""

from __future__ import annotations

from typing import Any

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
