from __future__ import annotations

import json

from parakeet.cli import main
from parakeet.doctor import collect_doctor_report, doctor_exit_code
from parakeet.types import AudioDevice


_DEFAULT_WSL = {
    "is_wsl": False,
    "has_wslg_socket": False,
    "detected_via": [],
}



def _stub_common(monkeypatch):
    monkeypatch.setattr("parakeet.doctor._detect_wsl", lambda: dict(_DEFAULT_WSL))



def test_collect_doctor_report_ok_when_audio_and_runtime_are_ready(monkeypatch):
    _stub_common(monkeypatch)
    monkeypatch.setattr(
        "parakeet.doctor.probe_audio_backend",
        lambda: {"status": "reachable", "transport": "tcp", "detail": "pactl info succeeded"},
    )
    monkeypatch.setattr(
        "parakeet.doctor.list_input_devices",
        lambda: [
            AudioDevice(
                id=2,
                name="Microphone",
                default_sample_rate=48000,
                max_input_channels=1,
                host_api="ALSA",
                is_default_candidate=True,
            )
        ],
    )
    monkeypatch.setattr(
        "parakeet.doctor._collect_clipboard_status",
        lambda: {"status": "ok", "backend": "pyperclip"},
    )
    monkeypatch.setattr(
        "parakeet.doctor._collect_cuda_status",
        lambda: {"available": True, "selected_device": "cuda", "device_name": "NVIDIA Test GPU"},
    )

    report = collect_doctor_report()

    assert report.schema_version == 1
    assert report.model == {
        "checked": False,
        "cache_present": None,
        "model_id": "nvidia/parakeet-tdt-0.6b-v3",
    }
    assert report.status["overall"] == "ok"
    assert report.status["exit_code"] == 0
    assert report.status["issues"] == []
    assert doctor_exit_code(report) == 0



def test_collect_doctor_report_fails_when_pulse_is_unreachable_and_no_devices_exist(monkeypatch):
    _stub_common(monkeypatch)
    monkeypatch.setattr(
        "parakeet.doctor.probe_audio_backend",
        lambda: {
            "status": "unreachable",
            "transport": "unix",
            "detail": "Connection refused",
        },
    )
    monkeypatch.setattr("parakeet.doctor.list_input_devices", lambda: [])
    monkeypatch.setattr(
        "parakeet.doctor._collect_clipboard_status",
        lambda: {"status": "ok", "backend": "pyperclip"},
    )
    monkeypatch.setattr(
        "parakeet.doctor._collect_cuda_status",
        lambda: {"available": True, "selected_device": "cuda", "device_name": "NVIDIA Test GPU"},
    )

    report = collect_doctor_report()
    issue_codes = {issue["code"] for issue in report.status["issues"]}

    assert report.status["overall"] == "fail"
    assert report.status["exit_code"] == 2
    assert issue_codes == {"AUDIO_BACKEND_UNREACHABLE", "AUDIO_NO_INPUT_DEVICE"}
    assert doctor_exit_code(report) == 2



def test_collect_doctor_report_warns_for_clipboard_and_cuda_without_blocking_recording(monkeypatch):
    _stub_common(monkeypatch)
    monkeypatch.setattr(
        "parakeet.doctor.probe_audio_backend",
        lambda: {"status": "reachable", "transport": "tcp", "detail": "pactl info succeeded"},
    )
    monkeypatch.setattr(
        "parakeet.doctor.list_input_devices",
        lambda: [
            AudioDevice(
                id=7,
                name="USB Mic",
                default_sample_rate=44100,
                max_input_channels=1,
                host_api="PulseAudio",
            )
        ],
    )
    monkeypatch.setattr(
        "parakeet.doctor._collect_clipboard_status",
        lambda: {"status": "unavailable", "backend": "pyperclip"},
    )
    monkeypatch.setattr(
        "parakeet.doctor._collect_cuda_status",
        lambda: {
            "available": False,
            "selected_device": "cpu",
            "device_name": None,
            "detail": "CUDA runtime is unavailable",
        },
    )

    report = collect_doctor_report()
    issue_codes = {issue["code"] for issue in report.status["issues"]}

    assert report.status["overall"] == "warn"
    assert report.status["exit_code"] == 3
    assert issue_codes == {"CLIPBOARD_UNAVAILABLE", "CUDA_UNAVAILABLE"}
    assert doctor_exit_code(report) == 3



def test_doctor_command_emits_json_schema(monkeypatch, capsys):
    _stub_common(monkeypatch)
    monkeypatch.setattr(
        "parakeet.doctor.probe_audio_backend",
        lambda: {"status": "reachable", "transport": "tcp", "detail": "pactl info succeeded"},
    )
    monkeypatch.setattr(
        "parakeet.doctor.list_input_devices",
        lambda: [
            AudioDevice(
                id=2,
                name="Microphone",
                default_sample_rate=48000,
                max_input_channels=1,
                host_api="ALSA",
                is_default_candidate=True,
            )
        ],
    )
    monkeypatch.setattr(
        "parakeet.doctor._collect_clipboard_status",
        lambda: {"status": "ok", "backend": "pyperclip"},
    )
    monkeypatch.setattr(
        "parakeet.doctor._collect_cuda_status",
        lambda: {"available": True, "selected_device": "cuda", "device_name": "NVIDIA Test GPU"},
    )

    exit_code = main(["doctor", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["schema_version"] == 1
    assert payload["pulse"] == {
        "status": "reachable",
        "transport": "tcp",
        "detail": "pactl info succeeded",
    }
    assert payload["audio_devices"] == [
        {
            "id": 2,
            "name": "Microphone",
            "default_sample_rate": 48000,
            "max_input_channels": 1,
            "host_api": "ALSA",
            "is_default_candidate": True,
        }
    ]
    assert payload["status"] == {
        "overall": "ok",
        "exit_code": 0,
        "issues": [],
    }
