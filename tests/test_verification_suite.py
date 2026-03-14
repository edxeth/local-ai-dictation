from __future__ import annotations

import json
import math
from pathlib import Path

from parakeet.benchmark import load_expected_transcript
from parakeet.cli import main
from parakeet.types import TranscriptionResult


class _FakeEngine:
    _parakeet_device = "cpu"


def test_repo_benchmark_fixture_asset_is_exercised_offline(monkeypatch, repo_fixture_dir: Path, capsys):
    fixture = repo_fixture_dir / "short_16k.wav"

    monkeypatch.setattr("parakeet.benchmark.load_engine", lambda config: _FakeEngine())
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
    assert payload["fixture"] == str(fixture)
    assert payload["expected_text"] == load_expected_transcript(fixture, required=True)
    assert payload["normalized_match"] is True
    assert len(payload["run_ms"]) == 2
    assert math.isclose(payload["total_ms"], payload["load_ms"] + sum(payload["run_ms"]), rel_tol=0, abs_tol=1e-6)
