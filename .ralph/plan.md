# Execution Plan: Implement Parakeet Dictation Modernization and Diagnostics

## Source Inputs
- Derived from **SPEC input only**.
- Immutable source planning document: `.pi/plans/specs/7abfbf14.md` (`Parakeet Dictation Modernization and Diagnostics`).
- Current repository signals at planning time: `README.md`, `requirements.txt`, `transcriber.py`, and no existing `pyproject.toml` or `tests/` tree.
- Assumptions derived conservatively from SPEC-only input:
  - milestone 1 is the active delivery target;
  - `parakeet serve` remains out of scope for milestone 1;
  - a temporary `transcriber.py` compatibility wrapper is acceptable during migration;
  - deterministic fixture-based tests must be introduced because live microphone verification is not suitable as the primary Ralph completion gate.

## Objective
Implement the milestone-1 modernization defined by the source SPEC: convert the current single-file Python dictation script into a packaged CLI with explicit diagnostics (`doctor`, `devices`), deterministic benchmarking, fixture-backed correctness checks, and optional WebRTC-VAD auto-stop while preserving the user-controlled recording lifecycle.

`.ralph/items.json` is the source of truth for feature-level execution status. Progress is complete only when every item there is verified end-to-end and marked `passes=true`.

## Scope In
- Add `pyproject.toml` and establish a `parakeet` console entry point.
- Introduce `src/parakeet/` modules for CLI, audio, model, doctor, config, output, benchmark, errors, and types.
- Preserve or explicitly replace current `transcriber.py` behavior via a compatibility wrapper during migration.
- Implement deterministic JSON contracts and exit-code behavior for `parakeet devices` and `parakeet doctor`.
- Implement optional `--check-model-cache` behavior for doctor without model download or full model load.
- Implement transcript normalization and fixture sidecar expectations for deterministic correctness checks.
- Implement `parakeet benchmark` for prerecorded WAV fixtures only.
- Add CI-safe automated tests and fixture assets.
- Implement WebRTC-VAD auto-stop without violating the manual-start lifecycle rule.
- Update README usage and verification guidance to reflect the packaged CLI.

## Scope Out
- `parakeet serve` or any long-lived daemon/service implementation.
- Native Windows or macOS support.
- GUI, tray, hotkey, or desktop automation integrations.
- Always-on listening or automatic startup behavior.
- Cloud/off-box transcription.
- Rewriting or relaxing the source SPEC.

## Constraints
- Preserve the immutable source SPEC unchanged.
- Work in small, fresh-context-safe increments: one `.ralph/items.json` item per iteration.
- One commit per completed item.
- One append-only progress entry per iteration in `.ralph/progress.md`.
- Never mark `passes=true` without executed verification evidence.
- No bypasses, no failure masking, and no weakening tests/checks to force green status.
- Keep `parakeet doctor` fast and side-effect free by default: no model load and no downloads.
- Use prerecorded fixtures, mocks, and deterministic tests as primary verification; live microphone checks remain secondary/manual.
- Keep lifecycle user-controlled: no microphone access before explicit start, and no hidden background startup.

## Prioritization Strategy
Choose work by risk, dependency weight, and architectural leverage rather than list order.

Priority heuristic:
1. Foundation and migration safety (`pyproject.toml`, package skeleton, compatibility wrapper, shared types/errors).
2. High-risk infrastructure and contracts (`devices`, `doctor`, JSON schemas, exit codes, backend probing).
3. Deterministic verification substrate (normalization, fixtures, benchmark path, automated tests).
4. Behavior-sensitive UX features (VAD, output adapters, docs updates).
5. Cleanup or polish only after the architectural and verification spine is solid.

If an item reveals that a previously passing item regressed, update only `passes`/`regression_notes` in `.ralph/items.json`, fix the regression, and keep the loop scoped to a single item.

## Completion Definition
The execution bundle is complete only when:
- every item in `.ralph/items.json` is `passes=true`;
- all applicable verification gates pass with exit code `0`;
- the repo contains the packaged CLI, deterministic tests, benchmark fixtures, and milestone-1 functionality described in the source SPEC;
- `.ralph/progress.md` contains one concise append-only entry per completed iteration;
- source planning docs remain unchanged;
- the final iteration can honestly end with `<promise>COMPLETE</promise>` under the rules in `.ralph/prompt.md`.
