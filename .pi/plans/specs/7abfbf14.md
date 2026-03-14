---
id: 7abfbf14
type: spec
title: Parakeet Dictation Modernization and Diagnostics
tags:
  - parakeet-dictation
  - modernization
  - diagnostics
  - performance
  - vad
  - autoresearch
status: open
created_at: 2026-03-14T10:18:36.556Z
modified_at: 2026-03-14T10:18:36.556Z
assigned_to_session: null
agent_rules: MUST update checklist done booleans during execution, not after
  completion. MUST edit only fields and sections explicitly allowed by the
  active instruction.
worktree:
  enabled: true
  branch: feat/todo-parakeet-dictation-modernization-and-diagnostics
ralph_loop_mode: off
links:
  root_abs: /home/devkit/projects/parakeet-dictation
  prds: []
  specs: []
  todos: []
checklist: []
---

# Summary
Modernize `parakeet-dictation` from a single-file prototype into a packaged, testable CLI with explicit diagnostics, deterministic benchmarking, and optional automatic stop using **WebRTC VAD**, while preserving a **strict user-controlled lifecycle**.

This refinement locks in the following decisions:
- `parakeet serve` remains **phase-2 only** and is not part of the first implementation milestone.
- `parakeet doctor` **MUST NOT load the model by default**.
- Transcript verification for tests and benchmarks uses **normalized exact match**.
- VAD implementation uses a **WebRTC VAD backend** behind a small internal interface.

## Related documents and code links
- Standalone spec: no PRD was selected for this request, so this spec is the root planning document.
- This spec file: `.pi/plans/specs/7abfbf14.md`.
- Baseline implementation: `README.md`, `transcriber.py`, `requirements.txt`.
- Follow-on planning artifact: create a `todo` document derived from this spec and link it back here so the spec/todo relationship becomes bidirectional.
- Cross-link contract for the future todo: include this spec path in the todo markdown body, and include the todo path back in this spec's follow-up refinement body section when that todo exists.
- Future expansion rule: if scope grows into desktop automation or OS integrations, create a PRD and cross-link that PRD to this spec and the derived todo.

## Problem statement
The current implementation works as an MVP, but it has four structural weaknesses:
1. audio failures are hard to diagnose on Linux/WSL because users only see low-level PortAudio/ALSA errors;
2. dictation flow is fully manual and tightly coupled to terminal input handling;
3. the codebase is a single script, which makes feature work and testing expensive;
4. performance work is not benchmark-driven yet, so latency changes are hard to compare and optimize.

## Goals
1. Preserve the current Linux/WSL microphone dictation workflow while making failures self-explanatory.
2. Keep lifecycle user-controlled: recording begins only after explicit user action, and no background process starts without explicit user intent.
3. Add a first-class diagnostics path for audio, WSL/Pulse, CUDA, clipboard, and local model readiness.
4. Add optional silence-based stop without removing the current default manual start/stop flow.
5. Refactor into testable modules and package the project with a stable `parakeet` entry point.
6. Add deterministic benchmarking so `autoresearch-create` can optimize latency against a stable workload.

## Non-goals
- Native Windows support.
- macOS support.
- Automatic startup at login.
- Always-on microphone listening.
- GUI/tray/global-hotkey work in the first implementation milestone.
- Full daemon/service semantics in the first implementation milestone.

## Scope boundaries
### In scope for milestone 1
- Packaging via `pyproject.toml` with a console entry point.
- Internal refactor from `transcriber.py` into modules under `src/parakeet/`.
- `parakeet dictation`, `parakeet doctor`, `parakeet devices`, and `parakeet benchmark`.
- WebRTC-VAD-based auto-stop.
- Deterministic fixture-based tests and benchmark harness.
- Clear error classification and WSL/Pulse remediation guidance.

### Explicitly out of scope for milestone 1
- `parakeet serve` implementation.
- Desktop automation or global hotkeys.
- Continuous streaming partial results over sockets.
- Cloud/off-box transcription.

## Architecture decisions
1. **Packaging**: migrate to `pyproject.toml` and install a `parakeet` console script.
2. **Repository layout**: use `src/parakeet/` for application code and `tests/` for automated verification.
3. **Compatibility**: keep `transcriber.py` as a thin compatibility wrapper during migration, forwarding to `parakeet dictation` behavior until removal is explicitly planned.
4. **VAD**: use a WebRTC VAD backend via a narrow interface so the command behavior is stable even if the underlying wheel package changes.
5. **Doctor safety**: `parakeet doctor` checks environment and local readiness only by default; it does not trigger model download or full model load.
6. **Benchmark determinism**: benchmark and optimization loops operate on prerecorded WAV fixtures only, never live microphone input.
7. **Verification strictness**: transcript quality is evaluated by normalized exact match with a documented normalization function.

## Target repository layout
```text
pyproject.toml
README.md
transcriber.py                 # temporary compatibility wrapper
src/parakeet/__init__.py
src/parakeet/cli.py
src/parakeet/audio.py
src/parakeet/doctor.py
src/parakeet/errors.py
src/parakeet/model.py
src/parakeet/output.py
src/parakeet/config.py
src/parakeet/benchmark.py
src/parakeet/types.py
tests/
  fixtures/
    short_16k.wav
    short_16k.expected.txt
  test_config.py
  test_doctor.py
  test_devices.py
  test_benchmark.py
  test_normalization.py
```

## Internal module responsibilities
### `src/parakeet/types.py`
Define stable internal data models, preferably frozen dataclasses or typed dictionaries:
- `AudioDevice`
- `DoctorIssue`
- `DoctorReport`
- `BenchmarkReport`
- `DictationConfig`
- `TranscriptionResult`
- `VadBackend` protocol/interface
- `TranscriptionEngine` protocol/interface

### `src/parakeet/errors.py`
Define application-level exceptions and issue codes. Minimum issue/code set:
- `AUDIO_BACKEND_UNREACHABLE`
- `AUDIO_NO_INPUT_DEVICE`
- `AUDIO_DEVICE_NOT_FOUND`
- `AUDIO_DEVICE_AMBIGUOUS`
- `AUDIO_SAMPLE_RATE_UNSUPPORTED`
- `CLIPBOARD_UNAVAILABLE`
- `CUDA_UNAVAILABLE`
- `MODEL_CACHE_MISSING`
- `MODEL_IMPORT_FAILED`
- `MODEL_TRANSCRIBE_FAILED`

### `src/parakeet/audio.py`
Owns:
- PyAudio device enumeration
- device resolution by id or name
- microphone capture
- sample-rate validation and resampling
- WSL/Pulse/ALSA backend probing
- VAD framing for auto-stop mode

Required public functions/interfaces:
- `list_input_devices() -> list[AudioDevice]`
- `resolve_input_device(selector: str | int | None) -> AudioDevice | None`
- `record_until_manual_stop(config: DictationConfig) -> bytes`
- `record_until_vad_stop(config: DictationConfig, vad: VadBackend) -> bytes`
- `probe_audio_backend() -> dict`

### `src/parakeet/model.py`
Owns:
- model id constant: `nvidia/parakeet-tdt-0.6b-v3`
- CPU/GPU selection
- local cache readiness checks
- model load/warmup
- transcription from PCM/WAV input

Required public functions/interfaces:
- `check_model_cache() -> dict`
- `load_engine(config: DictationConfig) -> TranscriptionEngine`
- `warmup(engine: TranscriptionEngine) -> None`
- `transcribe_wav(engine: TranscriptionEngine, path: str) -> TranscriptionResult`

Implementation rules:
- inference path MUST use `torch.inference_mode()`;
- model download MUST NOT be triggered by `doctor` default mode;
- benchmark code MAY choose between temporary WAV and in-memory input, but the selected path must remain consistent within a benchmark run.

### `src/parakeet/doctor.py`
Owns collection and classification of readiness signals.

Required public functions/interfaces:
- `collect_doctor_report(check_model_cache: bool = False) -> DoctorReport`
- `render_doctor_text(report: DoctorReport) -> str`
- `doctor_exit_code(report: DoctorReport) -> int`

### `src/parakeet/output.py`
Owns transcript emission:
- text rendering
- JSON rendering
- file writes
- clipboard copy

### `src/parakeet/config.py`
Owns config parsing, environment variable mapping, and precedence resolution.

### `src/parakeet/benchmark.py`
Owns fixture-based timing and transcript verification.

## CLI contract
### `parakeet dictation`
Purpose: run one explicit dictation session.

Supported flags:
- `--cpu` — force CPU inference.
- `--input-device <selector>` — numeric id or case-insensitive exact device name.
- `--vad` — enable VAD-driven auto-stop.
- `--max-silence-ms <int>` — silence duration required to auto-stop; default `1200`.
- `--min-speech-ms <int>` — minimum cumulative voiced duration before VAD stop becomes eligible; default `300`.
- `--vad-mode <0|1|2|3>` — WebRTC aggressiveness; default `2`.
- `--format text|json` — transcript output format; default `text`.
- `--output-file <path>` — optional transcript file destination.
- `--clipboard` / `--no-clipboard` — enable or disable clipboard copy; default enabled.
- `--debug` — verbose diagnostics/logging.

Session control rules:
- startup MUST display instructions;
- default manual controls remain `Enter` to start and `Enter` to stop;
- if `--vad` is enabled, `Enter` starts recording and either `Enter` or VAD stop may end recording;
- if no speech is detected, VAD MUST NOT auto-stop the session; the user retains manual control;
- the microphone MUST NOT be opened before the explicit start action.

### `parakeet devices`
Purpose: enumerate usable input devices.

Flags:
- `--json`

Behavior:
- MUST list only devices with `max_input_channels > 0`;
- MUST return a stable order sorted by device id;
- MUST mark a best-effort default candidate when identifiable.

### `parakeet doctor`
Purpose: diagnose whether dictation can work in the current environment.

Flags:
- `--json`
- `--check-model-cache` — verify local cache/import readiness only; no network and no model load.

Behavior:
- default mode MUST NOT load the model;
- default mode MUST NOT download anything;
- default mode MUST complete quickly and focus on actionable readiness checks.

### `parakeet benchmark`
Purpose: measure deterministic transcription latency on prerecorded fixtures.

Supported flags:
- `--fixture <path>` — required local WAV file.
- `--runs <int>` — positive integer, default `5`.
- `--json`
- `--cpu`
- `--check-expected` — require a sidecar expected transcript and compute normalized exact match.

Behavior:
- MUST reject non-local or missing fixture paths;
- MUST not access the microphone;
- MUST use the same engine instance for all warm runs in a single invocation;
- MUST emit timing fields sufficient for `autoresearch-create`;
- if `--check-expected` is set and the sidecar file is missing, MUST fail deterministically with a non-zero exit code.

### Phase-2 only: `parakeet serve`
`parakeet serve` remains part of the long-term roadmap, but it is not part of milestone 1. This spec only constrains it as follows:
- it MUST be opt-in;
- it MUST not start automatically;
- it MUST preserve the user-controlled lifecycle requirement.

## Config contract
Config file location:
- `~/.config/parakeet-dictation/config.toml`

Precedence order:
1. CLI flags
2. environment variables
3. config file
4. built-in defaults

Environment variable mapping:
- `PARAKEET_CPU`
- `PARAKEET_INPUT_DEVICE`
- `PARAKEET_VAD`
- `PARAKEET_MAX_SILENCE_MS`
- `PARAKEET_MIN_SPEECH_MS`
- `PARAKEET_VAD_MODE`
- `PARAKEET_FORMAT`
- `PARAKEET_OUTPUT_FILE`
- `PARAKEET_CLIPBOARD`
- `PARAKEET_DEBUG`

Config file schema for milestone 1:
```toml
cpu = false
input_device = ""
vad = false
max_silence_ms = 1200
min_speech_ms = 300
vad_mode = 2
format = "text"
output_file = ""
clipboard = true
debug = false
```

## JSON interface contracts
### `parakeet doctor --json`
Top-level shape:
```json
{
  "schema_version": 1,
  "platform": {"system": "Linux", "release": "..."},
  "wsl": {
    "is_wsl": true,
    "has_wslg_socket": false,
    "detected_via": ["proc_version", "env"]
  },
  "env": {
    "pulse_server": "tcp:172.17.128.1",
    "display": "172.17.128.1:0.0",
    "wayland_display": null
  },
  "pulse": {
    "status": "reachable",
    "transport": "tcp",
    "detail": "pactl info succeeded"
  },
  "audio_devices": [
    {
      "id": 2,
      "name": "Microphone",
      "default_sample_rate": 48000,
      "max_input_channels": 1,
      "host_api": "ALSA",
      "is_default_candidate": true
    }
  ],
  "clipboard": {"status": "ok", "backend": "pyperclip"},
  "cuda": {"available": true, "selected_device": "cuda", "device_name": "NVIDIA ..."},
  "model": {"checked": false, "cache_present": null, "model_id": "nvidia/parakeet-tdt-0.6b-v3"},
  "status": {
    "overall": "ok",
    "exit_code": 0,
    "issues": []
  }
}
```

Enumerated values:
- `pulse.status`: `reachable | unreachable | not_configured | binary_missing | unknown`
- `pulse.transport`: `unix | tcp | none | unknown`
- `clipboard.status`: `ok | missing | unavailable`
- `status.overall`: `ok | warn | fail`

Exit code mapping:
- `0`: recording prerequisites available
- `2`: recording blocked (`AUDIO_BACKEND_UNREACHABLE` or `AUDIO_NO_INPUT_DEVICE`)
- `3`: degraded but usable (for example clipboard unavailable or CUDA unavailable while CPU remains usable)

### `parakeet devices --json`
Top-level shape:
```json
{
  "schema_version": 1,
  "devices": [
    {
      "id": 2,
      "name": "Microphone",
      "default_sample_rate": 48000,
      "max_input_channels": 1,
      "host_api": "ALSA",
      "is_default_candidate": true
    }
  ]
}
```

If no devices are found, `devices` MUST be an empty array, not `null`.

### `parakeet benchmark --json`
Top-level shape:
```json
{
  "schema_version": 1,
  "fixture": "tests/fixtures/short_16k.wav",
  "runs": 5,
  "device": "cuda",
  "load_ms": 1234.5,
  "run_ms": [210.1, 208.7, 211.0, 209.8, 208.9],
  "mean_transcribe_ms": 209.7,
  "median_transcribe_ms": 209.8,
  "p95_transcribe_ms": 211.0,
  "total_ms": 2283.0,
  "transcript": "example transcript",
  "normalized_transcript": "example transcript",
  "expected_text": "example transcript",
  "normalized_match": true
}
```

Rules:
- `load_ms` is measured once per invocation;
- `run_ms` length MUST equal `runs`;
- `total_ms` MUST equal `load_ms + sum(run_ms)`;
- if no expected sidecar file is found and `--check-expected` is not set, `expected_text` MUST be `null` and `normalized_match` MUST be `null`.

## Device resolution rules
`--input-device` resolution is deterministic:
1. if the selector parses as an integer, match by device id;
2. otherwise perform case-insensitive exact name match;
3. if zero matches are found, fail with `AUDIO_DEVICE_NOT_FOUND` and list available devices;
4. if multiple exact-name matches are found, fail with `AUDIO_DEVICE_AMBIGUOUS` and list conflicting ids.

No substring matching is allowed in milestone 1.

## Doctor classification rules
### WSL detection
A session is considered WSL if any of the following hold:
- `WSL_DISTRO_NAME` is set;
- `/proc/version` contains `Microsoft` or `microsoft`;
- `/proc/sys/kernel/osrelease` contains `microsoft`.

### WSLg socket detection
`has_wslg_socket = true` if `/mnt/wslg/PulseServer` exists.

### Pulse reachability
Pulse status classification order:
1. if `pactl` binary is missing, return `binary_missing`;
2. if `PULSE_SERVER` is unset and `/mnt/wslg/PulseServer` does not exist, return `not_configured`;
3. if `PULSE_SERVER` starts with `unix:` or the WSLg socket exists, attempt `pactl info` with a short timeout;
4. if `PULSE_SERVER` starts with `tcp:`, attempt `pactl info` with a short timeout;
5. classify success as `reachable`, connection refusal/timeouts as `unreachable`, and all other probe failures as `unknown`.

### Doctor issue creation
Minimum issue mapping:
- zero enumerated input devices -> `AUDIO_NO_INPUT_DEVICE`
- pulse unreachable and zero devices -> `AUDIO_BACKEND_UNREACHABLE`
- clipboard backend missing -> `CLIPBOARD_UNAVAILABLE`
- CUDA unavailable while CPU fallback exists -> `CUDA_UNAVAILABLE` with overall `warn`
- `--check-model-cache` requested and local model cache/import missing -> `MODEL_CACHE_MISSING` or `MODEL_IMPORT_FAILED`

## VAD design
### Backend
- milestone 1 backend name: `webrtc`
- implementation MUST use a WebRTC VAD-compatible Python package
- backend implementation MUST be isolated behind a small interface so the CLI contract does not depend on a specific wheel name

### Audio framing
- VAD processing sample rate: `16000` Hz
- channel count: mono only
- frame size: `30 ms` frames
- PCM format: signed 16-bit little-endian

If the input device rate is not 16kHz, the capture pipeline MUST resample to 16kHz before VAD evaluation and before model input if the chosen transcription path requires it.

### Stop logic
Auto-stop eligibility begins only after cumulative voiced duration reaches `min_speech_ms`.

Once eligible, recording auto-stops when consecutive non-voiced frames reach or exceed `max_silence_ms`.

Behavioral rules:
- VAD MUST never auto-start recording.
- If zero voiced frames are detected, the session remains manual-stop only.
- Manual stop via `Enter` MUST always be available even when `--vad` is enabled.
- Empty audio buffers MUST be treated as a valid edge case and reported cleanly.

## Transcript normalization contract
Normalized exact match uses this deterministic normalization function:
1. apply Unicode NFKC normalization;
2. lowercase the string;
3. replace all non-alphanumeric characters with spaces;
4. collapse consecutive whitespace to a single space;
5. trim leading and trailing whitespace.

Two transcripts are considered equal only if their normalized forms are byte-for-byte identical.

## Benchmark contract
### Fixture naming
For a fixture `tests/fixtures/name.wav`, the optional expected transcript sidecar is:
- `tests/fixtures/name.expected.txt`

### Measurement rules
- one invocation loads the engine once;
- one invocation runs exactly `runs` warm transcriptions against the same fixture;
- `load_ms` measures engine creation only;
- each element of `run_ms` measures one complete transcription pass only;
- benchmark output MUST be generated from local files only;
- benchmark MUST fail fast if the fixture is unreadable or not a WAV file supported by the input path.

### Benchmark use in optimization
`autoresearch-create` MUST optimize against `mean_transcribe_ms` or `total_ms` from the benchmark JSON output, not against ad hoc manual measurements.

## Output behavior
- text mode MUST print a human-readable transcript to stdout;
- json mode MUST print exactly one JSON object to stdout;
- if `--output-file` is provided, the rendered transcript output MUST also be written to that file;
- clipboard copy remains orthogonal to output format and is controlled by `--clipboard` / `--no-clipboard`.

If clipboard copy fails:
- dictation MUST still succeed;
- the failure MUST become a warning, not a hard error;
- text mode SHOULD emit a concise warning only in debug mode.

## Constraints
- Python 3.10+ remains the baseline.
- Linux and WSL2 remain the supported platforms.
- User-controlled lifecycle is mandatory.
- Existing README workflows should continue to work during migration.
- Runtime dependency growth should remain minimal and justified.
- `parakeet doctor` default mode must stay fast and side-effect free.
- No optimization may be accepted if it materially degrades normalized exact-match correctness on fixtures.

## Edge cases
- No default audio device is configured.
- Pulse server is configured but unreachable.
- `pactl` is not installed.
- PyAudio lists zero input devices.
- A requested device disappears between listing and capture.
- Multiple devices share the same human-readable name.
- A device supports 48kHz but not 16kHz and needs resampling.
- Clipboard tool is missing or inaccessible.
- CUDA is installed but the selected runtime falls back to CPU.
- The local model cache is absent and network download would otherwise be required.
- A user enables VAD but never speaks.
- A fixture transcript differs only by punctuation/casing and should still pass normalized exact match.
- A benchmark fixture exists but its `.expected.txt` sidecar does not.
- `transcriber.py` compatibility wrapper diverges from `parakeet dictation` behavior during migration.

## Deterministic verification criteria
Implementation is complete only when all criteria below are satisfied:
1. `parakeet doctor --json` returns the documented object shape with `schema_version = 1` and stable required keys.
2. `parakeet devices --json` returns an object with `schema_version = 1` and `devices` as an array, including the empty-array case.
3. `parakeet benchmark --json --fixture tests/fixtures/short_16k.wav --runs 5` returns `run_ms` with length `5` and `total_ms = load_ms + sum(run_ms)` within normal floating-point tolerance.
4. Transcript normalization is covered by unit tests proving that punctuation-only and case-only differences still match, while lexical differences do not.
5. A simulated no-device environment produces `AUDIO_NO_INPUT_DEVICE` and exit code `2` from doctor.
6. A simulated unreachable Pulse environment produces `AUDIO_BACKEND_UNREACHABLE` and exit code `2` from doctor.
7. A simulated clipboard failure produces `CLIPBOARD_UNAVAILABLE` and exit code `3` or warning-level `status.overall = warn`, while dictation remains usable.
8. Default dictation mode opens the microphone only after explicit start input and still requires explicit manual stop when `--vad` is not set.
9. With `--vad`, auto-stop occurs only after voiced audio has been detected and the configured silence window has elapsed.
10. With `--vad` and no voiced frames, recording does not auto-stop.
11. Config precedence is covered by tests proving CLI flags override environment variables, environment variables override config file values, and config file values override defaults.
12. `transcriber.py` compatibility behavior is tested at least once during the migration window or explicitly removed from scope in a later spec revision.

## Validation strategy
### Unit tests
- normalization function
- config precedence
- device selector resolution
- doctor issue classification
- exit code mapping

### Integration tests
- `doctor --json` shape
- `devices --json` shape
- benchmark JSON output shape and arithmetic consistency
- benchmark expected-transcript sidecar loading

### Manual tests
- WSL with reachable Pulse backend
- WSL with unreachable Pulse backend
- Linux host with working microphone
- VAD stop behavior with spoken utterance
- manual-stop fallback when no speech is detected

### CI rules
- CI MUST run only fixture-based and mocked tests by default.
- Live-microphone tests MUST be opt-in/manual.
- Tests MUST not require network downloads.

## `autoresearch-create` instructions
User wording may refer to this as `autosearch-create`; the relevant skill name in this environment is `autoresearch-create`.
Use the `autoresearch-create` skill only after `parakeet benchmark` and fixture-based correctness tests exist.

Recommended loop definition:
- **Goal**: reduce end-to-end fixture transcription latency while preserving normalized exact-match correctness.
- **Primary metric**: `total_ms` from `parakeet benchmark --json` on a fixed local fixture set.
- **Secondary metrics**: `mean_transcribe_ms`, warm-start consistency, peak GPU memory, and normalized match rate.
- **Files in scope**: `src/parakeet/`, benchmark harness, fixtures, fixture expectations, and related tests.
- **Constraints**: no always-on recording, no hidden background startup, no correctness regressions on deterministic fixtures.

Required optimization harness direction:
- create `autoresearch.md` describing the exact fixture set, constraints, metric, and in-scope files;
- create `autoresearch.sh` that runs `parakeet benchmark --fixture tests/fixtures/short_16k.wav --runs 5 --json` and emits a metric line derived from `total_ms`;
- create `autoresearch.checks.sh` once automated tests for doctor/devices/benchmark exist;
- use prerecorded fixtures only; never use live microphone capture inside the experiment loop.

## Delivery sequencing
1. add `pyproject.toml`, package structure, and `transcriber.py` compatibility wrapper;
2. implement typed internal models and error codes;
3. implement `devices` and `doctor` with JSON contracts and deterministic exit codes;
4. implement benchmark command and fixture-based verification;
5. implement WebRTC-VAD auto-stop for dictation;
6. optionally revisit phase-2 `serve` in a new spec revision or linked follow-on spec.

## Follow-on document requirements
After this spec is accepted, create a `todo` document that:
- links back to this spec in its markdown body;
- breaks work into packaging, typed errors/models, diagnostics, benchmark, VAD, and compatibility milestones;
- preserves the user-controlled lifecycle requirement as a non-negotiable constraint;
- treats `parakeet serve` as phase-2 only unless a new spec revises that decision.
