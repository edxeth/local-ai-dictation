"""Top-level CLI entry point for the packaged Parakeet app."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="parakeet",
        description="Packaged Parakeet dictation CLI.",
    )
    subparsers = parser.add_subparsers(dest="command")

    dictation_parser = subparsers.add_parser(
        "dictation",
        help="Run one interactive dictation session.",
        description="Run one interactive dictation session.",
    )
    dictation_parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Verbose diagnostics: device, timings, GPU memory (logs to file unless --log-file=-)",
    )
    dictation_parser.add_argument("--cpu", action="store_true", help="Force CPU inference")
    dictation_parser.add_argument(
        "--no-clipboard",
        action="store_true",
        help="Do not copy transcript to clipboard",
    )
    dictation_parser.add_argument(
        "--log-file",
        default="transcriber.debug.log",
        help="Debug log file (use '-' for stderr)",
    )
    dictation_parser.add_argument(
        "--list-devices", action="store_true", help="List audio input devices and exit"
    )
    dictation_parser.add_argument(
        "--input-device", type=int, default=None, help="PyAudio input device index"
    )
    dictation_parser.set_defaults(handler=_run_dictation_namespace)
    return parser


def _run_dictation_namespace(namespace: argparse.Namespace) -> int:
    from parakeet.dictation import run_dictation

    return run_dictation(namespace)


def run_dictation_argv(argv: Sequence[str] | None = None) -> int:
    from parakeet.dictation import build_parser, run_dictation

    parser = build_parser()
    actual_argv = sys.argv[1:] if argv is None else list(argv)
    namespace = parser.parse_args(actual_argv)
    return run_dictation(namespace)


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv:
        parser = build_parser()
        parser.print_help()
        return 0

    if argv[0].startswith("-") and argv[0] not in {"-h", "--help"}:
        return run_dictation_argv(argv)

    parser = build_parser()
    namespace = parser.parse_args(argv)
    handler = getattr(namespace, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return handler(namespace)


if __name__ == "__main__":
    raise SystemExit(main())
