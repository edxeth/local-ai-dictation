#!/usr/bin/env python3
"""Compatibility wrapper for the packaged Parakeet dictation CLI."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

if SRC.exists():
    sys.path.insert(0, str(SRC))

from parakeet.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["dictation", *sys.argv[1:]]))
