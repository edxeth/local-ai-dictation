"""Benchmark helpers for deterministic transcript normalization and fixture sidecars."""

from __future__ import annotations

from pathlib import Path
import unicodedata


def normalize_transcript(text: str) -> str:
    """Normalize transcript text using the milestone-1 exact-match contract."""
    normalized = unicodedata.normalize("NFKC", text).lower()
    alnum_or_space = "".join(character if character.isalnum() else " " for character in normalized)
    return " ".join(alnum_or_space.split())


def expected_sidecar_path(fixture_path: str | Path) -> Path:
    """Return the expected-transcript sidecar path for a WAV fixture."""
    return Path(fixture_path).with_suffix(".expected.txt")


def load_expected_transcript(
    fixture_path: str | Path,
    *,
    required: bool = False,
) -> str | None:
    """Load the raw expected transcript sidecar for a fixture if present."""
    sidecar_path = expected_sidecar_path(fixture_path)
    if not sidecar_path.is_file():
        if required:
            raise FileNotFoundError(f"Expected transcript sidecar not found: {sidecar_path}")
        return None
    return sidecar_path.read_text(encoding="utf-8")


def load_normalized_expected_transcript(
    fixture_path: str | Path,
    *,
    required: bool = False,
) -> str | None:
    """Load and normalize the expected transcript sidecar for a fixture if present."""
    transcript = load_expected_transcript(fixture_path, required=required)
    if transcript is None:
        return None
    return normalize_transcript(transcript)


def normalized_exact_match(actual: str, expected: str) -> bool:
    """Compare two transcripts using the deterministic normalization contract."""
    return normalize_transcript(actual) == normalize_transcript(expected)
