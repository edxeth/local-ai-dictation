from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from parakeet.cli import main
import parakeet.desktop as desktop


class _FakeCompletedProcess:
    def __init__(self, returncode: int = 0):
        self.returncode = returncode


class _FakePopen:
    def __init__(self, command, **kwargs):
        self.command = command
        self.cwd = kwargs.get("cwd")
        self.env = kwargs.get("env")
        self.returncode = None
        self.terminate_calls = 0
        self.kill_calls = 0
        self.wait_timeouts: list[float | None] = []

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminate_calls += 1
        self.returncode = 0

    def wait(self, timeout=None):
        self.wait_timeouts.append(timeout)
        if self.returncode is None:
            self.returncode = 0
        return self.returncode

    def kill(self):
        self.kill_calls += 1
        self.returncode = -9


class _PopenFactory:
    def __init__(self):
        self.calls: list[_FakePopen] = []

    def __call__(self, command, **kwargs):
        process = _FakePopen(command, **kwargs)
        self.calls.append(process)
        return process


def test_gui_subcommand_dispatches_to_desktop_launcher(monkeypatch):
    calls: list[SimpleNamespace] = []

    def _fake_run_gui(namespace):
        calls.append(namespace)
        return 0

    monkeypatch.setattr("parakeet.desktop.run_gui_command", _fake_run_gui)

    assert main(["gui"]) == 0
    assert len(calls) == 1
    assert calls[0].command == "gui"
    assert calls[0].bridge is False
    assert calls[0].host == "127.0.0.1"
    assert calls[0].port == 8765


def test_gui_stage_subcommand_dispatches_to_desktop_stager(monkeypatch):
    calls: list[SimpleNamespace] = []

    def _fake_stage(namespace):
        calls.append(namespace)
        return 0

    monkeypatch.setattr("parakeet.desktop.run_gui_stage_command", _fake_stage)

    assert main(["gui-stage", "--json"]) == 0
    assert len(calls) == 1
    assert calls[0].command == "gui-stage"
    assert calls[0].json_output is True


def test_gui_bridge_flag_delegates_to_full_command(monkeypatch):
    monkeypatch.setattr("parakeet.desktop.run_full_command", lambda namespace: 7)

    namespace = SimpleNamespace(host="127.0.0.1", port=8765, bridge=True)

    assert desktop.run_gui_command(namespace) == 7


def test_full_command_starts_bridge_then_gui_and_cleans_up(monkeypatch):
    popen_factory = _PopenFactory()
    monkeypatch.setattr(desktop, "bridge_healthy", lambda host, port: False)
    monkeypatch.setattr(desktop, "wait_for_bridge", lambda host, port: True)
    monkeypatch.setattr(desktop, "_run_gui_process", lambda host, port: 0)
    monkeypatch.setattr(desktop, "repo_root", lambda: Path("/tmp/parakeet"))
    monkeypatch.setattr(desktop.subprocess, "Popen", popen_factory)

    namespace = SimpleNamespace(
        host="127.0.0.1",
        port=8765,
        cpu=True,
        input_device="Mic 1",
        vad=True,
        max_silence_ms=1600,
        min_speech_ms=400,
        vad_mode=3,
        clipboard=False,
        debug=True,
        log_file="bridge.log",
    )

    assert desktop.run_full_command(namespace) == 0
    assert len(popen_factory.calls) == 1
    process = popen_factory.calls[0]
    assert process.cwd == Path("/tmp/parakeet")
    assert process.command[:4] == [desktop.sys.executable, "-m", "parakeet.cli", "bridge"]
    assert "--cpu" in process.command
    assert "--vad" in process.command
    assert "--no-clipboard" in process.command
    assert "--debug" in process.command
    assert process.terminate_calls == 1
    assert process.kill_calls == 0


def test_full_command_reuses_existing_bridge(monkeypatch, capsys):
    monkeypatch.setattr(desktop, "bridge_healthy", lambda host, port: True)
    monkeypatch.setattr(desktop, "_run_gui_process", lambda host, port: 0)
    monkeypatch.setattr(desktop.subprocess, "Popen", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not spawn bridge")))

    namespace = SimpleNamespace(host="127.0.0.1", port=8765)

    assert desktop.run_full_command(namespace) == 0
    captured = capsys.readouterr()
    assert "Reusing existing Parakeet bridge" in captured.out


def test_stage_windows_desktop_app_copies_desktop_folder(monkeypatch, tmp_path: Path):
    repo_root = tmp_path / "repo"
    app_dir = repo_root / "desktop" / "electrobun"
    (app_dir / "src").mkdir(parents=True)
    (app_dir / "package.json").write_text('{"name":"parakeet-electrobun"}')
    (app_dir / "src" / "index.ts").write_text("console.log('hello');")
    (app_dir / "node_modules").mkdir()
    (app_dir / "node_modules" / "ignored.txt").write_text("ignore me")
    (app_dir / ".tmp-check").mkdir()
    (app_dir / ".tmp-check" / "ignored.txt").write_text("ignore me")

    stage_root = tmp_path / "mnt" / "c" / "Users" / "dev" / "AppData" / "Local" / "ParakeetDictation" / "staging"
    monkeypatch.setattr(desktop, "windows_stage_root", lambda: stage_root)
    monkeypatch.setattr(desktop, "windows_path_from_wsl", lambda path: f"C:\\stage\\{path.name}")

    payload = desktop.stage_windows_desktop_app(app_dir)
    staged_app_dir = Path(payload["desktop_app_dir"])

    assert staged_app_dir == next(stage_root.glob("*/desktop/electrobun"))
    assert (staged_app_dir / "package.json").exists()
    assert (staged_app_dir / "src" / "index.ts").read_text() == "console.log('hello');"
    assert not (staged_app_dir / "node_modules").exists()
    assert not (staged_app_dir / ".tmp-check").exists()
    assert payload["windows_desktop_app_dir"].startswith("C:\\stage\\")
