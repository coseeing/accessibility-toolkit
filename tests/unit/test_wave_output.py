import logging
import subprocess
import sys
import types

import accessibility_toolkit.output.wave as wave_module
from accessibility_toolkit.output.wave import DefaultWaveOutput, DefaultWavePlaybackBackend


class FakePlaybackBackend:
    def __init__(self) -> None:
        self.paths: list[str] = []

    def play(self, path: str) -> None:
        self.paths.append(path)


class FailingPlaybackBackend:
    def play(self, path: str) -> None:
        raise OSError(f"cannot play {path}")


def test_default_wave_output_delegates_path() -> None:
    playback = FakePlaybackBackend()
    output = DefaultWaveOutput(playback=playback)

    output.play("/tmp/connected.wav")

    assert playback.paths == ["/tmp/connected.wav"]


def test_default_wave_output_logs_backend_failure(caplog) -> None:
    output = DefaultWaveOutput(playback=FailingPlaybackBackend())

    with caplog.at_level(logging.WARNING):
        output.play("missing.wav")

    assert "Failed to play wave file" in caplog.text


def test_windows_backend_uses_async_filename_playback(monkeypatch) -> None:
    calls = []
    fake_winsound = types.SimpleNamespace(
        SND_FILENAME=1,
        SND_ASYNC=2,
        SND_NODEFAULT=4,
        PlaySound=lambda path, flags: calls.append((path, flags)),
    )
    monkeypatch.setitem(sys.modules, "winsound", fake_winsound)

    DefaultWavePlaybackBackend()._play_windows("connected.wav")

    assert calls == [("connected.wav", 1 | 2 | 4)]


def test_macos_backend_starts_afplay_without_waiting(monkeypatch) -> None:
    calls = []

    def fake_popen(command, **kwargs):
        calls.append((command, kwargs))
        return object()

    monkeypatch.setattr(wave_module.subprocess, "Popen", fake_popen)

    DefaultWavePlaybackBackend()._play_macos("disconnected.wav")

    assert calls[0][0] == ["afplay", "disconnected.wav"]
    assert calls[0][1] == {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }


def test_unsupported_backend_logs_and_returns(monkeypatch, caplog) -> None:
    monkeypatch.setattr(wave_module.sys, "platform", "linux")

    with caplog.at_level(logging.WARNING):
        DefaultWavePlaybackBackend().play("connected.wav")

    assert "Wave output is not supported" in caplog.text
