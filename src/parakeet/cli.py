"""Top-level CLI entry point for the packaged Parakeet app."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from parakeet.dictation import add_cli_arguments


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
    add_cli_arguments(dictation_parser)
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
