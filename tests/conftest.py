from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def force_offline_test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the automated test suite deterministic and offline-safe."""
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    monkeypatch.delenv("PULSE_SERVER", raising=False)


@pytest.fixture
def repo_fixture_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures"
