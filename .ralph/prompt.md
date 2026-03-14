# Ralph Loop Prompt: Implement Parakeet Dictation Modernization and Diagnostics

## Goal
Implement milestone 1 from the immutable source SPEC `.pi/plans/specs/7abfbf14.md`: migrate the current repo from a single-file Python dictation script into a packaged `parakeet` CLI with deterministic diagnostics, fixture-based benchmarking, contract tests, and optional WebRTC-VAD auto-stop, while preserving a strict user-controlled lifecycle.

Current repo signals at bundle creation time:
- primary runtime files: `README.md`, `requirements.txt`, `transcriber.py`
- no `pyproject.toml` yet
- no `tests/` tree yet
- source planning doc is a SPEC, not a PRD

You are operating in a fresh context window. Do not rely on prior chat history.

## Context Inputs
First read these files with the read tool:
- `.ralph/plan.md`
- `.ralph/items.json`
- `.ralph/progress.md`

Then read these source and implementation files to re-establish project context:
- `.pi/plans/specs/7abfbf14.md` (immutable source SPEC; do not edit it)
- `README.md`
- `requirements.txt`
- `transcriber.py`
- any existing `pyproject.toml`, `src/parakeet/**`, and `tests/**` files relevant to the selected item

Treat `.ralph/items.json` as the source of truth for item status. Treat `.ralph/progress.md` as append-only execution history.

## Fresh-Context Startup
1. Run `pwd` and confirm you are in the project root.
2. Run `git log --oneline -10` to understand the most recent changes.
3. Run `git status --short` to understand the current working tree.
4. Reconstruct state from files and git history, not from prior chat.
5. Re-check the current repo shape before coding: inspect whether `pyproject.toml`, `tests/`, package modules, or benchmark fixtures now exist.
6. Restate the single item you are choosing, why it is highest priority by risk/dependencies/architectural impact, and what verification evidence will be required before you can mark it done.

## Single-Item Iteration Protocol
- Work on exactly one highest-priority item where `passes=false`.
- Prioritize by risk, dependencies, and architectural impact, not by list order.
- Do not bundle nearby tasks, cleanup, or “while I’m here” changes from a second item into the same iteration.
- Keep the repo in a clean, mergeable state by the end of the iteration.
- Make exactly one git commit for the single item worked on.
- Update `.ralph/items.json` only by changing `passes` and, if needed, `regression_notes`.
- Do not delete items.
- Do not rewrite any item's `description` or `steps`.
- If a previously passing item regresses, set its `passes` back to `false` and explain the regression in `regression_notes`.
- If the chosen item proves too large, narrow your implementation approach, but do not start a second item in the same iteration.

## Stack-Aware Verification Gates
First identify the project's canonical verification commands from repository config in this order:
1. `pyproject.toml`
2. `Makefile`
3. `tox.ini`, `noxfile.py`, `pytest.ini`, or other Python tooling config
4. CI config or repo scripts
5. `README.md` usage/verification instructions

If canonical commands exist, use them and record them in `.ralph/progress.md`. If they do not exist yet, use the concrete fallback gates below for this Python CLI repo.

### Concrete fallback gates for this repo
Use `./.venv/bin/python` when present; otherwise use `python3` only if the virtualenv interpreter is unavailable.

**Environment sanity gate**
- `./.venv/bin/python -V`

**Static/syntax gate**
- `./.venv/bin/python -m compileall transcriber.py src tests`
- If `src/` or `tests/` do not exist yet, limit the command to existing paths but do not silently drop syntax checking for files you changed.

**Unit/integration gate**
- If `tests/` exists or the current item adds automated tests: `./.venv/bin/python -m pytest -q`
- If the current item creates the first automated tests, this gate becomes mandatory before the item can pass.

**Packaging gate**
- Once `pyproject.toml` exists: `./.venv/bin/python -m pip install -e .`
- If a build backend and `build` module are configured, also run: `./.venv/bin/python -m build`

**CLI contract smoke gates**
Run the command(s) relevant to the item once the packaged CLI exists:
- `./.venv/bin/parakeet devices --json`
- `./.venv/bin/parakeet doctor --json`
- `./.venv/bin/parakeet doctor --check-model-cache --json`
- `./.venv/bin/parakeet benchmark --fixture tests/fixtures/short_16k.wav --runs 2 --json --check-expected`

**Targeted contract gates**
- For configuration work, run tests proving CLI > env > config > defaults precedence.
- For diagnostics work, run tests/mocks that exercise ok/warn/fail classification and exit-code mapping.
- For VAD work, run automated tests or controlled input tests that prove voiced-audio eligibility, silence-triggered stop, and no-speech manual-stop fallback.
- For README/doc work, run the relevant command examples you update so the docs are evidence-backed.

Every applicable gate must pass with exit code `0` before the item can be considered done.

## No-Bypass Rules
- Do not skip checks.
- Do not weaken tests or delete tests to get green results.
- Do not use bypass flags or failure masking patterns such as `--no-verify`, `|| true`, swallowing exceptions, or suppressing non-zero exit codes.
- Do not claim success without executed evidence from the required checks.
- Do not mark `passes=true` unless the item's verification steps have been satisfied end-to-end.

## Source-Doc Protection
- Do not edit source planning docs unless the user explicitly instructs you to do so.
- The immutable source planning doc for this loop is `.pi/plans/specs/7abfbf14.md`.
- Update only implementation files and the Ralph execution artifacts unless explicit instructions say otherwise.
- `README.md` is implementation documentation, not a protected source planning doc, so it may be updated when relevant to the chosen item.

## Progress File Rules
- Append exactly one concise entry to `.ralph/progress.md` per iteration.
- Treat `.ralph/progress.md` as append-only; never rewrite, truncate, or clean up prior entries.
- Each entry must include:
  - item worked on
  - key decisions
  - files changed
  - verification commands run and outcomes
  - notes for the next fresh-context iteration
- Keep entries concise and factual.

## Loop Control Promise Contract
- End the iteration with exactly one control tag on the last non-empty line.
- Emit `<promise>NEXT</promise>` only when exactly one item was completed, fully verified, recorded in `.ralph/items.json`, logged in `.ralph/progress.md`, and committed.
- Emit `<promise>COMPLETE</promise>` only when all items in `.ralph/items.json` are `passes=true` and all required verification gates pass fully with no bypass.
- Do not emit any other control promise.
- Do not stop early without either finishing one item completely or completing the entire plan.

## Additional Ralph Discipline For This Repo
- Bias toward fresh-context-safe, small, verifiable increments.
- Favor foundational risk first: packaging, shared contracts, diagnostics, benchmark/test substrate, then VAD and docs.
- Keep the loop monolithic: single repo, single item, single commit, single progress entry.
- Use git history plus Ralph artifacts to understand prior work rather than relying on memory.
- Preserve the user-controlled lifecycle: no microphone access before explicit user start, no automatic background startup, and no accidental drift toward `serve`/daemon scope.
- Treat deterministic fixture-based verification as the main completion mechanism; live microphone checks are secondary/manual evidence only.
