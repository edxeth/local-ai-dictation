from __future__ import annotations

import json
import math
import wave

from parakeet.benchmark import benchmark_fixture
from parakeet.cli import main
from parakeet.types import TranscriptionResult


class _FakeEngine:
    _parakeet_device = "cpu"



def _write_wav(path, *, sample_rate: int = 16000, frames: int = 160):
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frames)



def test_benchmark_fixture_reports_expected_match_and_consistent_arithmetic(tmp_path):
    fixture = tmp_path / "short_16k.wav"
    expected = tmp_path / "short_16k.expected.txt"
    _write_wav(fixture)
    expected.write_text("Hello, WORLD!!\n", encoding="utf-8")

    perf_values = iter([10.0, 10.2, 20.0, 20.1, 30.0, 30.3])

    report = benchmark_fixture(
        fixture,
        runs=2,
        cpu=True,
        check_expected=True,
        perf_counter=lambda: next(perf_values),
        load_engine_fn=lambda config: _FakeEngine(),
        transcribe_wav_fn=lambda engine, path: TranscriptionResult(text="hello world", device="cpu"),
    )

    assert report.schema_version == 1
    assert report.fixture == str(fixture)
    assert report.runs == 2
    assert report.device == "cpu"
    assert math.isclose(report.load_ms, 200.0)
    assert len(report.run_ms) == 2
    assert math.isclose(report.run_ms[0], 100.0)
    assert math.isclose(report.run_ms[1], 300.0)
    assert math.isclose(report.mean_transcribe_ms, 200.0)
    assert math.isclose(report.median_transcribe_ms, 200.0)
    assert math.isclose(report.p95_transcribe_ms, 300.0)
    assert math.isclose(report.total_ms, 600.0)
    assert report.transcript == "hello world"
    assert report.normalized_transcript == "hello world"
    assert report.expected_text == "Hello, WORLD!!\n"
    assert report.normalized_match is True



def test_benchmark_command_emits_json_schema(monkeypatch, tmp_path, capsys):
    fixture = tmp_path / "short_16k.wav"
    expected = tmp_path / "short_16k.expected.txt"
    _write_wav(fixture)
    expected.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        "parakeet.benchmark.load_engine",
        lambda config: _FakeEngine(),
    )
    monkeypatch.setattr(
        "parakeet.benchmark.transcribe_wav",
        lambda engine, path: TranscriptionResult(text="", device="cpu"),
    )

    exit_code = main(
        [
            "benchmark",
            "--fixture",
            str(fixture),
            "--runs",
            "2",
            "--json",
            "--check-expected",
            "--cpu",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["schema_version"] == 1
    assert payload["fixture"] == str(fixture)
    assert payload["runs"] == 2
    assert payload["device"] == "cpu"
    assert len(payload["run_ms"]) == 2
    assert math.isclose(payload["total_ms"], payload["load_ms"] + sum(payload["run_ms"]), rel_tol=0, abs_tol=1e-6)
    assert payload["expected_text"] == ""
    assert payload["normalized_match"] is True



def test_benchmark_command_redirects_noisy_runtime_stdout_away_from_json(monkeypatch, tmp_path, capsys):
    fixture = tmp_path / "short_16k.wav"
    expected = tmp_path / "short_16k.expected.txt"
    _write_wav(fixture)
    expected.write_text("", encoding="utf-8")

    def noisy_load_engine(config):
        print("runtime-info-log")
        return _FakeEngine()

    monkeypatch.setattr("parakeet.benchmark.load_engine", noisy_load_engine)
    monkeypatch.setattr(
        "parakeet.benchmark.transcribe_wav",
        lambda engine, path: TranscriptionResult(text="", device="cpu"),
    )

    exit_code = main(
        [
            "benchmark",
            "--fixture",
            str(fixture),
            "--runs",
            "1",
            "--json",
            "--check-expected",
            "--cpu",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["schema_version"] == 1
    assert "runtime-info-log" not in captured.out
    assert "runtime-info-log" in captured.err



def test_benchmark_command_requires_sidecar_when_check_expected_is_enabled(tmp_path, capsys):
    fixture = tmp_path / "short_16k.wav"
    _write_wav(fixture)

    exit_code = main(
        [
            "benchmark",
            "--fixture",
            str(fixture),
            "--runs",
            "1",
            "--json",
            "--check-expected",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Expected transcript sidecar not found" in captured.err
