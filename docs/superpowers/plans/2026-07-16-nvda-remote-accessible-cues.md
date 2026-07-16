# NVDA Remote Accessible Connection Cues Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add correctly associated connection-editor labels, reusable asynchronous WAV playback in accessibility-toolkit-core, and NVDA-style connection/control feedback in the NVDA Remote client.

**Architecture:** Keep platform WAV playback behind the existing `WaveOutput.play(path: str)` protocol and pass it through `PlatformProvider`, runtime parts, and `Capabilities`. A focused NVDA Remote cue presenter maps state transitions to packaged WAV files or local `SpeechSequence` output; connection and mode use cases trigger it only on real transitions, while the UI remains a passive state consumer.

**Tech Stack:** Python 3.11+, wxPython, `winsound` on Windows, `afplay` on macOS, setuptools package data, PyInstaller, pytest.

## Global Constraints

- The existing public protocol remains `WaveOutput.play(path: str) -> None`.
- `Capabilities.wave` is optional, just like `Capabilities.tone`.
- `DefaultWaveOutput.play(path)` must be non-blocking; playback failures and unsupported platforms log a warning and return without raising.
- Keep generated beep behavior in `DefaultToneOutput` unchanged.
- Package verbatim `ref/nvda/source/waves/connected.wav` and `ref/nvda/source/waves/disconnected.wav` under `src/apps/nvda_remote/waves/`.
- Preserve NVDA source attribution and GPL v2-or-later licensing information beside the copied assets, including a verbatim `NVDA-COPYING.txt`; resulting distributions must remain GPL-compatible.
- Fixed cue mapping: connected plays `connected.wav`; disconnected plays `disconnected.wav` and speaks `Disconnected`; entering control speaks `Controlling remote computer`; leaving control speaks `Controlling local computer`.
- Play the disconnected wave/speech cue only for `CONNECTED -> IDLE`; `CONNECTING -> IDLE` still cleans up and publishes idle without a disconnected cue.
- Duplicate connected, disconnected, start-control, and stop-control requests must not produce duplicate cues.
- Do not add a TeleNVDA-style sound-versus-tone preference, persistent audio setting, or remote-protocol change.
- Do not forward local cue WAV files to remote peers.
- Preserve unrelated existing worktree changes, especially edits already present in `src/ui/nvda_remote/connection_editor.py` and `tests/unit/test_app_wx.py`.

## File Structure

- `src/ui/nvda_remote/connection_editor.py`: own visible mnemonic labels and their adjacency to editor controls.
- `src/accessibility_toolkit/output/wave.py`: own safe cross-platform file-based WAV playback.
- `src/accessibility_toolkit/output/capabilities.py`: expose optional wave output to applications.
- `src/accessibility_toolkit/runtime/platform.py`: lazily construct default wave output.
- `src/accessibility_toolkit/runtime/output.py`: place wave output in `Capabilities`.
- `src/accessibility_toolkit/runtime/runtime_parts.py`: request and expose wave output during app composition.
- `src/apps/nvda_remote/cues.py`: resolve local cue resources and present wave/speech feedback safely.
- `src/apps/nvda_remote/use_cases/connection.py`: emit connection cues once per real lifecycle transition.
- `src/apps/nvda_remote/use_cases/control_mode.py`: emit control-state speech when a mode transition succeeds.
- `src/apps/nvda_remote/service.py`: compose the cue presenter with connection and control use cases.
- `src/apps/nvda_remote/waves/`: contain the two copied NVDA WAV files, their attribution notice, and NVDA's complete license text.
- `pyproject.toml`, `packaging/windows_apps.spec`, `packaging/macos_apps.spec`: include cue resources in package and executable builds.

---

### Task 1: Associate Visible Connection Editor Labels

**Files:**
- Modify: `src/ui/nvda_remote/connection_editor.py:19-48`
- Modify: `tests/unit/test_nvda_remote_connection_ui.py:75-116`

**Interfaces:**
- Consumes: existing `wx.StaticText`, `wx.TextCtrl`, `wx.SpinCtrl`, and horizontal `wx.BoxSizer` behavior.
- Produces: `ConnectionEditorDialog.field_labels: tuple[tuple[wx.StaticText, wx.Control], ...]` in visual/focus order.

- [ ] **Step 1: Write the failing label-association test**

Add this test beside `test_editor_uses_accessible_names_and_standard_keyboard_defaults`:

```python
def test_editor_pairs_visible_mnemonic_labels_with_fields(monkeypatch):
    editor_module, _group_module = load_editor_ui(monkeypatch)
    dialog = editor_module.ConnectionEditorDialog(None)

    assert [label.GetLabel() for label, _control in dialog.field_labels] == [
        "&Name:",
        "&Host:",
        "&Port:",
        "&Key:",
    ]
    assert [control for _label, control in dialog.field_labels] == [
        dialog.name_ctrl,
        dialog.host_ctrl,
        dialog.port_ctrl,
        dialog.key_ctrl,
    ]

    field_rows = [entry[0] for entry in dialog.panel.sizer.children[:4]]
    for row, (label, control) in zip(field_rows, dialog.field_labels, strict=True):
        assert row.children[0][0] is label
        assert row.children[1][0] is control
```

Expose the fake panel through `dialog.panel`; no fake-wx behavior needs to be invented because `StaticText.GetLabel`, `Panel.sizer`, and `BoxSizer.children` already exist.

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
pytest tests/unit/test_nvda_remote_connection_ui.py::test_editor_pairs_visible_mnemonic_labels_with_fields -v
```

Expected: FAIL with `AttributeError: 'ConnectionEditorDialog' object has no attribute 'field_labels'`.

- [ ] **Step 3: Store mnemonic labels and their associated controls**

In `ConnectionEditorDialog.__init__`, retain the panel and replace the current string/control loop with:

```python
self.panel = wx.Panel(self)
panel = self.panel
sizer = wx.BoxSizer(wx.VERTICAL)
self.field_labels = tuple(
    (wx.StaticText(panel, label=label), control)
    for label, control in (
        ("&Name:", self.name_ctrl),
        ("&Host:", self.host_ctrl),
        ("&Port:", self.port_ctrl),
        ("&Key:", self.key_ctrl),
    )
)
for label, control in self.field_labels:
    row = wx.BoxSizer(wx.HORIZONTAL)
    row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    row.Add(control, 1, wx.EXPAND | wx.ALL, 4)
    sizer.Add(row, 0, wx.EXPAND, 0)
```

The `&` mnemonic and native sibling order follow the same convention used by remotePlusPlus/NVDA's `addLabeledControl`; keep all current `SetName` calls for stable screen-reader names.

- [ ] **Step 4: Run the editor UI tests**

Run:

```bash
pytest tests/unit/test_nvda_remote_connection_ui.py -v
```

Expected: all tests PASS, including field validation, default buttons, focus, and the new label pairing test.

- [ ] **Step 5: Commit the label change**

```bash
git add src/ui/nvda_remote/connection_editor.py tests/unit/test_nvda_remote_connection_ui.py
git commit -m "fix: associate connection editor labels"
```

---

### Task 2: Implement Safe Asynchronous Wave Playback

**Files:**
- Modify: `src/accessibility_toolkit/output/wave.py`
- Create: `tests/unit/test_wave_output.py`

**Interfaces:**
- Consumes: `WaveOutput.play(path: str) -> None` from `accessibility_toolkit.output.interfaces`.
- Produces: `WavePlaybackBackend.play(path: str) -> None`, `DefaultWavePlaybackBackend`, and `DefaultWaveOutput.load_default() -> DefaultWaveOutput`.

- [ ] **Step 1: Write failing delegation and failure-isolation tests**

Create `tests/unit/test_wave_output.py` with:

```python
import logging

from accessibility_toolkit.output.wave import DefaultWaveOutput


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
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```bash
pytest tests/unit/test_wave_output.py -v
```

Expected: collection FAILS because `DefaultWaveOutput` is not defined.

- [ ] **Step 3: Implement the testable output facade and backend protocol**

Replace `src/accessibility_toolkit/output/wave.py` with:

```python
from __future__ import annotations

import logging
import subprocess
import sys
from typing import Protocol


class WavePlaybackBackend(Protocol):
    def play(self, path: str) -> None: ...


class DefaultWavePlaybackBackend:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(__name__)

    def play(self, path: str) -> None:
        if sys.platform == "win32":
            self._play_windows(path)
            return
        if sys.platform == "darwin":
            self._play_macos(path)
            return
        self._logger.warning("Wave output is not supported on this platform")

    @staticmethod
    def _play_windows(path: str) -> None:
        import winsound

        winsound.PlaySound(
            path,
            winsound.SND_FILENAME
            | winsound.SND_ASYNC
            | winsound.SND_NODEFAULT,
        )

    @staticmethod
    def _play_macos(path: str) -> None:
        subprocess.Popen(
            ["afplay", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


class DefaultWaveOutput:
    def __init__(
        self,
        *,
        playback: WavePlaybackBackend | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._logger = logger or logging.getLogger(__name__)
        self._playback = playback or DefaultWavePlaybackBackend(logger=self._logger)

    @classmethod
    def load_default(cls) -> "DefaultWaveOutput":
        return cls()

    def play(self, path: str) -> None:
        try:
            self._playback.play(path)
        except Exception:
            self._logger.warning(
                "Failed to play wave file",
                extra={"path": path},
                exc_info=True,
            )


class LoggingWaveOutput:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(__name__)

    def play(self, path: str) -> None:
        self._logger.info("wave output requested", extra={"path": path})
```

Keep `LoggingWaveOutput` for compatibility with any current direct imports.

- [ ] **Step 4: Run facade tests and verify they pass**

Run:

```bash
pytest tests/unit/test_wave_output.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Add failing platform-backend tests for non-blocking flags**

Append to `tests/unit/test_wave_output.py`:

```python
import sys
import types

import accessibility_toolkit.output.wave as wave_module
from accessibility_toolkit.output.wave import DefaultWavePlaybackBackend


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
```

Also add `import subprocess` at the top of the test module.

- [ ] **Step 6: Run all wave and tone tests**

Run:

```bash
pytest tests/unit/test_wave_output.py tests/unit/test_tone_output.py -v
```

Expected: all tests PASS; existing tone generation behavior remains unchanged.

- [ ] **Step 7: Commit wave playback**

```bash
git add src/accessibility_toolkit/output/wave.py tests/unit/test_wave_output.py
git commit -m "feat: add asynchronous wave output"
```

---

### Task 3: Wire WaveOutput Through Core Runtime Composition

**Files:**
- Modify: `src/accessibility_toolkit/output/capabilities.py`
- Modify: `src/accessibility_toolkit/runtime/platform.py:1-43,97-116,245-316`
- Modify: `src/accessibility_toolkit/runtime/output.py:1-62`
- Modify: `src/accessibility_toolkit/runtime/runtime_parts.py:1-48`
- Modify: `tests/unit/test_runtime_output.py:54-86`
- Modify: `tests/unit/test_runtime_platform.py:1-18,27-43,289-309`
- Modify: `tests/unit/test_runtime_parts.py:1-181`
- Modify: `tests/unit/test_runtime_platform_import.py`
- Modify: `tests/unit/test_functional_package_api.py:11-36`

**Interfaces:**
- Consumes: `DefaultWaveOutput.load_default()` from Task 2.
- Produces: `Capabilities.wave: WaveOutput | None`, `create_wave_output() -> WaveOutput`, `PlatformProvider.create_wave_output() -> WaveOutput`, `AppRuntimeParts.wave_output`, and `build_output_services(..., wave_output=...)`.

- [ ] **Step 1: Write failing capability and output-composition tests**

In `tests/unit/test_runtime_output.py`, extend the base test with `assert services.capabilities.wave is None`, then add:

```python
def test_build_output_services_includes_wave_capability():
    wave_output = object()

    services = build_output_services(
        engine_options_factory=engine_options_factory,
        selected_engine_id="primary",
        wave_output=wave_output,
    )
    try:
        assert services.capabilities.wave is wave_output
    finally:
        services.speaker.shutdown()
```

Run:

```bash
pytest tests/unit/test_runtime_output.py::test_build_output_services_includes_wave_capability -v
```

Expected: FAIL because `build_output_services` does not accept `wave_output`.

- [ ] **Step 2: Add optional wave to Capabilities and output composition**

Change `src/accessibility_toolkit/output/capabilities.py` to import `WaveOutput` and define:

```python
from accessibility_toolkit.output.interfaces import (
    BrailleOutput,
    ToneOutput,
    WaveOutput,
)


@dataclass(frozen=True)
class Capabilities:
    speech: SpeechServicePort
    tone: ToneOutput | None = None
    wave: WaveOutput | None = None
    braille: BrailleOutput | None = None
```

In `src/accessibility_toolkit/runtime/output.py`, import `WaveOutput`, add `wave_output: WaveOutput | None = None` after `tone_output`, and construct:

```python
capabilities=Capabilities(
    speech=speaker,
    tone=tone_output,
    wave=wave_output,
),
```

Run:

```bash
pytest tests/unit/test_runtime_output.py -v
```

Expected: all runtime-output tests PASS.

- [ ] **Step 3: Write failing platform factory tests**

Update imports in `tests/unit/test_runtime_platform.py` to include `create_wave_output`, then add:

```python
class TestCreateWaveOutput:
    def test_returns_default_wave_output(self):
        from accessibility_toolkit.output.wave import DefaultWaveOutput

        wave = create_wave_output()

        assert isinstance(wave, DefaultWaveOutput)
```

Update `test_isolated_import_keeps_output_implementations_lazy` so its forbidden set also contains `accessibility_toolkit.output.wave`.

Run:

```bash
pytest tests/unit/test_runtime_platform.py::TestCreateWaveOutput -v
```

Expected: collection FAILS because `create_wave_output` is missing.

- [ ] **Step 4: Add the lazy platform wave factory**

In `src/accessibility_toolkit/runtime/platform.py`:

```python
from accessibility_toolkit.output import ClipboardService, ToneOutput, WaveOutput

_DefaultToneOutput: Any = None
_DefaultWaveOutput: Any = None
```

Add the lazy loader and public factory:

```python
def _get_default_wave_output_class() -> Any:
    global _DefaultWaveOutput
    if _DefaultWaveOutput is None:
        from accessibility_toolkit.output.wave import DefaultWaveOutput as Output

        _DefaultWaveOutput = Output
    return _DefaultWaveOutput


def create_wave_output() -> WaveOutput:
    return _get_default_wave_output_class().load_default()
```

Extend `PlatformServices`, `PlatformProvider`, and `build_services`:

```python
@dataclass(frozen=True)
class PlatformServices:
    input_capture: InputCapture
    hotkey_capture: HotkeyCapture
    clipboard: ClipboardService
    tone_output: ToneOutput
    wave_output: WaveOutput


class PlatformProvider:
    def create_wave_output(self) -> WaveOutput:
        return create_wave_output()

    def build_services(
        self, hotkey_usage: int = _DEFAULT_HOTKEY_USAGE
    ) -> PlatformServices:
        return PlatformServices(
            input_capture=self.create_input_capture(),
            hotkey_capture=self.create_hotkey_capture(hotkey_usage),
            clipboard=self.create_clipboard_service(),
            tone_output=self.create_tone_output(),
            wave_output=self.create_wave_output(),
        )
```

Run:

```bash
pytest tests/unit/test_runtime_platform.py -v
```

Expected: all platform tests PASS after adding `assert services.wave_output is not None` to the provider test.

- [ ] **Step 5: Write failing runtime-parts wiring tests**

In `tests/unit/test_runtime_parts.py`, add:

```python
class FakeWave:
    def play(self, path):
        del path
```

Extend `FakeProvider.__init__` with `self.wave_output = FakeWave()` and `self.wave_calls = 0`, plus:

```python
def create_wave_output(self):
    self.wave_calls += 1
    return self.wave_output
```

In `test_build_app_runtime_parts_wires_platform_and_output_services`, assert:

```python
assert provider.wave_calls == 1
assert parts.wave_output is provider.wave_output
assert parts.output.capabilities.wave is provider.wave_output
```

Add an exclusion test:

```python
def test_build_app_runtime_parts_can_exclude_wave():
    provider = FakeProvider()

    parts = build_app_runtime_parts(
        provider=provider,
        hotkey_usage=HID.ENTER,
        include_wave=False,
    )
    try:
        assert provider.wave_calls == 0
        assert parts.wave_output is None
        assert parts.output.capabilities.wave is None
    finally:
        parts.output.speaker.shutdown()
```

Run:

```bash
pytest tests/unit/test_runtime_parts.py -v
```

Expected: FAIL because `AppRuntimeParts.wave_output` and `include_wave` do not exist.

- [ ] **Step 6: Add wave selection to runtime parts**

In `src/accessibility_toolkit/runtime/runtime_parts.py`, import `WaveOutput` and use:

```python
@dataclass(frozen=True)
class AppRuntimeParts:
    input_capture: InputCapture
    hotkey_capture: HotkeyCapture
    clipboard: ClipboardService | None
    tone_output: ToneOutput | None
    wave_output: WaveOutput | None
    output: OutputServices
```

Extend `build_app_runtime_parts` with `include_wave: bool = True`, then construct and forward it:

```python
wave_output = provider.create_wave_output() if include_wave else None
output = build_output_services(
    engine_options_factory=provider.default_speech_engine_options,
    selected_engine_id=selected_engine_id or default_engine_id,
    fallback_engine_id=fallback_engine_id,
    tone_output=tone_output,
    wave_output=wave_output,
    on_engine_fallback=on_engine_fallback,
)
return AppRuntimeParts(
    input_capture=input_capture,
    hotkey_capture=hotkey_capture,
    clipboard=clipboard,
    tone_output=tone_output,
    wave_output=wave_output,
    output=output,
)
```

Run:

```bash
pytest tests/unit/test_runtime_parts.py -v
```

Expected: all runtime-parts tests PASS.

- [ ] **Step 7: Update type and public-output regression tests**

Replace `tests/unit/test_runtime_platform_import.py` with:

```python
from typing import get_type_hints

from accessibility_toolkit.output import ToneOutput, WaveOutput
from accessibility_toolkit.runtime.platform import PlatformProvider


def test_platform_provider_tone_factory_uses_the_public_output_type():
    hints = get_type_hints(PlatformProvider.create_tone_output)

    assert hints["return"] is ToneOutput


def test_platform_provider_wave_factory_uses_the_public_output_type():
    hints = get_type_hints(PlatformProvider.create_wave_output)

    assert hints["return"] is WaveOutput
```

In `tests/unit/test_functional_package_api.py`, change the expected output symbols to include the protocol while leaving the runtime export set unchanged:

```python
"accessibility_toolkit.output": {
    "Capabilities",
    "ClipboardService",
    "QueuedService",
    "WaveOutput",
},
```

The module-level `create_wave_output` factory remains an implementation detail of `accessibility_toolkit.runtime.platform`, matching the existing `create_tone_output` convention; do not export either factory from `accessibility_toolkit.runtime`.

Run:

```bash
pytest tests/unit/test_runtime_platform_import.py tests/unit/test_functional_package_api.py -v
```

Expected: all API/type tests PASS.

- [ ] **Step 8: Commit runtime wiring**

```bash
git add src/accessibility_toolkit/output/capabilities.py src/accessibility_toolkit/runtime/platform.py src/accessibility_toolkit/runtime/output.py src/accessibility_toolkit/runtime/runtime_parts.py tests/unit/test_runtime_output.py tests/unit/test_runtime_platform.py tests/unit/test_runtime_parts.py tests/unit/test_runtime_platform_import.py tests/unit/test_functional_package_api.py
git commit -m "feat: expose wave output capability"
```

---

### Task 4: Present NVDA Remote Connection and Control Cues

**Files:**
- Create: `src/apps/nvda_remote/cues.py`
- Modify: `src/apps/nvda_remote/use_cases/connection.py`
- Modify: `src/apps/nvda_remote/use_cases/control_mode.py`
- Modify: `src/apps/nvda_remote/service.py:1-170`
- Create: `tests/unit/test_nvda_remote_cues.py`
- Modify: `tests/unit/test_nvda_remote_use_cases.py:90-135,225-260`
- Modify: `tests/unit/test_nvda_remote_app_service.py:90-205,540-660,790-825`

**Interfaces:**
- Consumes: `Capabilities.wave`, `Capabilities.speech.speak(SpeechSequence)`, and the runtime state enums.
- Produces: `NvdaRemoteCues.connected()`, `disconnected()`, `controlling_remote()`, and `controlling_local()`; optional cue callbacks on the connection/control use cases.

- [ ] **Step 1: Write failing cue-presenter tests**

Create `tests/unit/test_nvda_remote_cues.py`:

```python
from pathlib import Path

from accessibility_toolkit.output import Capabilities
from accessibility_toolkit.output.speech import SpeechSequence
from apps.nvda_remote.cues import NvdaRemoteCues


class FakeWave:
    def __init__(self) -> None:
        self.paths: list[str] = []

    def play(self, path: str) -> None:
        self.paths.append(path)


class FakeSpeech:
    def __init__(self) -> None:
        self.spoken: list[SpeechSequence] = []

    def speak(self, sequence: SpeechSequence) -> None:
        self.spoken.append(sequence)


def test_connection_cues_use_packaged_waves_and_disconnect_speech(tmp_path: Path):
    wave = FakeWave()
    speech = FakeSpeech()
    cues = NvdaRemoteCues(
        Capabilities(speech=speech, wave=wave),
        cue_directory=tmp_path,
    )

    cues.connected()
    cues.disconnected()

    assert wave.paths == [
        str(tmp_path / "connected.wav"),
        str(tmp_path / "disconnected.wav"),
    ]
    assert speech.spoken == [SpeechSequence(items=("Disconnected",))]


def test_control_cues_speak_local_and_remote_state(tmp_path: Path):
    speech = FakeSpeech()
    cues = NvdaRemoteCues(
        Capabilities(speech=speech),
        cue_directory=tmp_path,
    )

    cues.controlling_remote()
    cues.controlling_local()

    assert speech.spoken == [
        SpeechSequence(items=("Controlling remote computer",)),
        SpeechSequence(items=("Controlling local computer",)),
    ]


def test_disconnect_speech_continues_without_wave_output(tmp_path: Path):
    speech = FakeSpeech()
    cues = NvdaRemoteCues(
        Capabilities(speech=speech),
        cue_directory=tmp_path,
    )

    cues.disconnected()

    assert speech.spoken == [SpeechSequence(items=("Disconnected",))]
```

Use a minimal fake speech object because these tests call only `speak`; structural protocol typing does not require unrelated settings methods at runtime.

- [ ] **Step 2: Run cue tests and verify they fail**

Run:

```bash
pytest tests/unit/test_nvda_remote_cues.py -v
```

Expected: collection FAILS because `apps.nvda_remote.cues` does not exist.

- [ ] **Step 3: Implement the cue presenter**

Create `src/apps/nvda_remote/cues.py`:

```python
from __future__ import annotations

import logging
from pathlib import Path

from accessibility_toolkit.output import Capabilities
from accessibility_toolkit.output.speech import SpeechSequence


_logger = logging.getLogger(__name__)


class NvdaRemoteCues:
    def __init__(
        self,
        capabilities: Capabilities,
        *,
        cue_directory: Path | None = None,
    ) -> None:
        self._capabilities = capabilities
        self._cue_directory = cue_directory or Path(__file__).with_name("waves")

    def connected(self) -> None:
        self._play("connected.wav")

    def disconnected(self) -> None:
        self._play("disconnected.wav")
        self._speak("Disconnected")

    def controlling_remote(self) -> None:
        self._speak("Controlling remote computer")

    def controlling_local(self) -> None:
        self._speak("Controlling local computer")

    def _play(self, filename: str) -> None:
        wave = self._capabilities.wave
        if wave is None:
            return
        wave.play(str(self._cue_directory / filename))

    def _speak(self, message: str) -> None:
        try:
            self._capabilities.speech.speak(SpeechSequence(items=(message,)))
        except Exception:
            _logger.warning("Failed to speak NVDA Remote cue", exc_info=True)
```

Wave failures are already isolated by `DefaultWaveOutput`; speech failures are also isolated here so feedback cannot interrupt a completed state transition.

- [ ] **Step 4: Run cue-presenter tests**

Run:

```bash
pytest tests/unit/test_nvda_remote_cues.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Write failing use-case transition tests**

Extend `tests/unit/test_nvda_remote_use_cases.py` so constructors receive explicit cue callbacks and add:

```python
def test_remote_connection_use_case_emits_cues_only_for_real_transitions():
    from apps.nvda_remote.use_cases.connection import RemoteConnectionUseCase

    state = RuntimeState(connection_state=ConnectionState.CONNECTING)
    cues = []
    use_case = RemoteConnectionUseCase(
        state=state,
        exit_active=lambda: None,
        ensure_hotkey_started=lambda: None,
        stop_capture=lambda: None,
        stop_hotkey=lambda: None,
        notify=lambda _event: None,
        on_connected=lambda: cues.append("connected"),
        on_disconnected=lambda: cues.append("disconnected"),
    )

    use_case.handle_connected()
    use_case.handle_connected()
    use_case.handle_disconnected()
    use_case.handle_disconnected()

    state.connection_state = ConnectionState.CONNECTING
    use_case.handle_disconnected()

    assert cues == ["connected", "disconnected"]


def test_control_mode_use_case_emits_transition_speech_callbacks():
    from apps.nvda_remote.use_cases.control_mode import NvdaRemoteControlModeUseCase

    state = RuntimeState(
        connection_state=ConnectionState.CONNECTED,
        control_state=ControlState.CONNECTED,
    )
    cues = []
    use_case = NvdaRemoteControlModeUseCase(
        state=state,
        notify_error=lambda _message: None,
        notify_status=lambda _event: None,
        on_started=lambda: cues.append("remote"),
        on_stopped=lambda: cues.append("local"),
    )

    use_case.start_control()
    use_case.stop_control()

    assert cues == ["remote", "local"]
```

Run:

```bash
pytest tests/unit/test_nvda_remote_use_cases.py::test_remote_connection_use_case_emits_cues_only_for_real_transitions tests/unit/test_nvda_remote_use_cases.py::test_control_mode_use_case_emits_transition_speech_callbacks -v
```

Expected: FAIL because the callback parameters do not exist.

- [ ] **Step 6: Add callback ownership and connection idempotence to use cases**

In `src/apps/nvda_remote/use_cases/connection.py`, import `Callable` and add typed, defaulted callbacks without breaking existing focused callers:

```python
from collections.abc import Callable


class RemoteConnectionUseCase:
    def __init__(
        self,
        *,
        state: RuntimeState,
        exit_active,
        ensure_hotkey_started,
        stop_capture,
        stop_hotkey,
        notify,
        on_connected: Callable[[], None] = lambda: None,
        on_disconnected: Callable[[], None] = lambda: None,
    ) -> None:
        self._state = state
        self._exit_active = exit_active
        self._ensure_hotkey_started = ensure_hotkey_started
        self._stop_capture = stop_capture
        self._stop_hotkey = stop_hotkey
        self._notify = notify
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected

    def handle_connected(self) -> None:
        if self._state.connection_state == ConnectionState.CONNECTED:
            return
        self._state.connection_state = ConnectionState.CONNECTED
        if self._state.control_state != ControlState.CONTROLLING:
            self._state.control_state = ControlState.CONNECTED
            self._exit_active()
            self._ensure_hotkey_started()
        self._on_connected()
        self._notify(RemoteConnectionChanged("connected"))

    def handle_disconnected(self) -> None:
        if self._state.connection_state == ConnectionState.IDLE:
            return
        was_connected = self._state.connection_state == ConnectionState.CONNECTED
        self._stop_capture()
        self._stop_hotkey()
        self._state.connection_state = ConnectionState.IDLE
        self._state.control_state = ControlState.IDLE
        if was_connected:
            self._on_disconnected()
        self._notify(RemoteConnectionChanged("idle"))
```

In `src/apps/nvda_remote/use_cases/control_mode.py`, replace the constructor and transition methods with:

```python
class NvdaRemoteControlModeUseCase:
    def __init__(
        self,
        *,
        state: RuntimeState,
        notify_error: Callable[[str], None],
        notify_status: Callable[[RemoteControlChanged], None],
        on_started: Callable[[], None] = lambda: None,
        on_stopped: Callable[[], None] = lambda: None,
    ) -> None:
        self._state = state
        self._notify_error = notify_error
        self._notify_status = notify_status
        self._on_started = on_started
        self._on_stopped = on_stopped

    def start_control(self) -> None:
        self._state.control_state = ControlState.CONTROLLING
        self._on_started()
        self._notify_status(RemoteControlChanged(ControlState.CONTROLLING.value))

    def stop_control(self) -> None:
        self._state.control_state = ControlState.CONNECTED
        self._on_stopped()
        self._notify_status(RemoteControlChanged(ControlState.CONNECTED.value))
```

Do not add a state guard inside `NvdaRemoteControlModeUseCase`: `InputActivationUseCase.enter_active()` sets `control_state` before `RemoteControlMode.enter()` invokes this use case. `ModeManager.active_mode_id` and `NvdaRemoteAppService.stop_control()` already guard duplicate public start/stop requests, so adding a second guard here would suppress the real cue.

- [ ] **Step 7: Compose cues in the application service**

Import `NvdaRemoteCues` in `src/apps/nvda_remote/service.py`, construct it immediately after storing capabilities, and pass exact callbacks:

```python
self._capabilities = capabilities
self._cues = NvdaRemoteCues(capabilities)

self._control_mode = NvdaRemoteControlModeUseCase(
    state=self.state,
    notify_error=self._notify_error,
    notify_status=self._notify_status_listener,
    on_started=self._cues.controlling_remote,
    on_stopped=self._cues.controlling_local,
)

self._connection = RemoteConnectionUseCase(
    state=self.state,
    exit_active=self._activation.exit_active,
    ensure_hotkey_started=self._ensure_hotkey_started,
    stop_capture=self._stop_capture,
    stop_hotkey=self._stop_hotkey,
    notify=self._status_presenter.notify,
    on_connected=self._cues.connected,
    on_disconnected=self._cues.disconnected,
)
```

- [ ] **Step 8: Add service-level wave and speech assertions**

In `tests/unit/test_nvda_remote_app_service.py`, add:

```python
class FakeWaveService:
    def __init__(self) -> None:
        self.paths = []

    def play(self, path: str) -> None:
        self.paths.append(path)
```

Construct `Capabilities` in `build_service` with `wave=FakeWaveService()`. Add tests:

```python
def test_nvda_remote_service_presents_connection_cues_once():
    service, _transport, _capture, _hotkey, _dispatch_calls = build_service()

    service.state.connection_state = ConnectionState.CONNECTING
    service._on_protocol_event(RemoteSessionConnected())
    service._on_protocol_event(RemoteSessionConnected())
    service._connection.handle_disconnected()
    service._connection.handle_disconnected()

    assert [Path(path).name for path in service._capabilities.wave.paths] == [
        "connected.wav",
        "disconnected.wav",
    ]
    assert service._capabilities.speech.spoken[-1] == SpeechSequence(
        items=("Disconnected",)
    )


def test_nvda_remote_service_presents_control_cues_once():
    service, _transport, _capture, _hotkey, _dispatch_calls = build_service()
    service.state.connection_state = ConnectionState.CONNECTED

    service.start_control()
    service.start_control()
    service.stop_control()
    service.stop_control()

    assert service._capabilities.speech.spoken[-2:] == [
        SpeechSequence(items=("Controlling remote computer",)),
        SpeechSequence(items=("Controlling local computer",)),
    ]
```

Add imports for `Path` and `SpeechSequence`. Update the existing missing-tone test replacement capability to preserve `wave=service._capabilities.wave` so that test isolates only tone behavior.

- [ ] **Step 9: Run all NVDA Remote use-case and service tests**

Run:

```bash
pytest tests/unit/test_nvda_remote_cues.py tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_app_service.py -v
```

Expected: all tests PASS, including existing event ordering and F11 mode behavior.

- [ ] **Step 10: Commit cue behavior**

```bash
git add src/apps/nvda_remote/cues.py src/apps/nvda_remote/use_cases/connection.py src/apps/nvda_remote/use_cases/control_mode.py src/apps/nvda_remote/service.py tests/unit/test_nvda_remote_cues.py tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_app_service.py
git commit -m "feat: announce NVDA Remote state changes"
```

---

### Task 5: Package NVDA Cue Assets and Licensing Notice

**Files:**
- Create: `src/apps/nvda_remote/waves/connected.wav` (verbatim copy)
- Create: `src/apps/nvda_remote/waves/disconnected.wav` (verbatim copy)
- Create: `src/apps/nvda_remote/waves/NOTICE.md`
- Create: `src/apps/nvda_remote/waves/NVDA-COPYING.txt` (verbatim copy)
- Modify: `pyproject.toml:23-25`
- Modify: `packaging/windows_apps.spec:12-73`
- Modify: `packaging/macos_apps.spec:12-80`
- Modify: `tests/unit/test_distribution_packaging.py`
- Modify: `tests/unit/test_functional_package_api.py:66-72`

**Interfaces:**
- Consumes: source assets at `ref/nvda/source/waves/connected.wav` and `ref/nvda/source/waves/disconnected.wav`.
- Produces: runtime resource directory `apps/nvda_remote/waves` in source installs, wheels, and Windows/macOS PyInstaller outputs.

- [ ] **Step 1: Write failing asset provenance and package-data tests**

Append to `tests/unit/test_distribution_packaging.py`:

```python
def test_nvda_remote_wave_assets_match_nvda_sources_and_include_notice():
    app_waves = REPOSITORY_ROOT / "src" / "apps" / "nvda_remote" / "waves"
    nvda_waves = REPOSITORY_ROOT / "ref" / "nvda" / "source" / "waves"

    assert (app_waves / "connected.wav").read_bytes() == (
        nvda_waves / "connected.wav"
    ).read_bytes()
    assert (app_waves / "disconnected.wav").read_bytes() == (
        nvda_waves / "disconnected.wav"
    ).read_bytes()
    assert (app_waves / "NVDA-COPYING.txt").read_bytes() == (
        REPOSITORY_ROOT / "ref" / "nvda" / "copying.txt"
    ).read_bytes()
    notice = (app_waves / "NOTICE.md").read_text(encoding="utf-8")
    assert "NVDA" in notice
    assert "GPL-2.0-or-later" in notice


def test_pyinstaller_specs_include_nvda_remote_wave_assets():
    for relative_path in (
        "packaging/windows_apps.spec",
        "packaging/macos_apps.spec",
    ):
        spec_text = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        assert '"apps/nvda_remote/waves"' in spec_text
        assert 'settings.get("datas", [])' in spec_text
```

Extend `test_package_data_uses_output_speech_windows_path` in `tests/unit/test_functional_package_api.py` to load the root `pyproject.toml` and assert:

```python
root_data = tomllib.loads(
    (Path(__file__).parents[2] / "pyproject.toml").read_text()
)["tool"]["setuptools"]["package-data"]
assert root_data["apps.nvda_remote"] == [
    "waves/*.wav",
    "waves/NOTICE.md",
    "waves/NVDA-COPYING.txt",
]
```

- [ ] **Step 2: Run packaging tests and verify they fail**

Run:

```bash
pytest tests/unit/test_distribution_packaging.py::test_nvda_remote_wave_assets_match_nvda_sources_and_include_notice tests/unit/test_distribution_packaging.py::test_pyinstaller_specs_include_nvda_remote_wave_assets tests/unit/test_functional_package_api.py::test_package_data_uses_output_speech_windows_path -v
```

Expected: FAIL because the app wave directory and package-data declarations do not exist.

- [ ] **Step 3: Copy the two approved NVDA assets verbatim**

The WAV files cannot be represented safely in a text patch, and the license must remain verbatim. Copy only the three approved source files:

```bash
mkdir -p src/apps/nvda_remote/waves
cp ref/nvda/source/waves/connected.wav src/apps/nvda_remote/waves/connected.wav
cp ref/nvda/source/waves/disconnected.wav src/apps/nvda_remote/waves/disconnected.wav
cp ref/nvda/copying.txt src/apps/nvda_remote/waves/NVDA-COPYING.txt
cmp ref/nvda/source/waves/connected.wav src/apps/nvda_remote/waves/connected.wav
cmp ref/nvda/source/waves/disconnected.wav src/apps/nvda_remote/waves/disconnected.wav
cmp ref/nvda/copying.txt src/apps/nvda_remote/waves/NVDA-COPYING.txt
```

Expected: all three `cmp` commands exit 0 with no output.

- [ ] **Step 4: Add the exact attribution notice**

Create `src/apps/nvda_remote/waves/NOTICE.md`:

```markdown
# NVDA Remote cue assets

`connected.wav` and `disconnected.wav` are verbatim copies from the NVDA project:

- Source: `source/waves/connected.wav` and `source/waves/disconnected.wav`
- Project: <https://github.com/nvaccess/nvda>
- Copyright: NV Access Limited and NVDA contributors
- License: GNU General Public License v2 or later (`GPL-2.0-or-later`)

NVDA's authoritative licensing information is included beside these assets as
`NVDA-COPYING.txt` and is also available upstream:
<https://github.com/nvaccess/nvda/blob/master/copying.txt>.
```

- [ ] **Step 5: Include resources in setuptools package data**

Add this entry to the root `pyproject.toml` package-data table:

```toml
"apps.nvda_remote" = ["waves/*.wav", "waves/NOTICE.md", "waves/NVDA-COPYING.txt"]
```

Do not add these application resources to `packages/accessibility-toolkit-core/pyproject.toml`; the core wheel contains the reusable player, while the root application distribution owns NVDA's cue assets.

- [ ] **Step 6: Include resources in both PyInstaller specs**

In both `packaging/windows_apps.spec` and `packaging/macos_apps.spec`, define:

```python
NVDA_REMOTE_WAVES = SRC / "apps" / "nvda_remote" / "waves"
```

Add this key to only the `nvda_remote` entry in `APPS`:

```python
"datas": [(str(NVDA_REMOTE_WAVES), "apps/nvda_remote/waves")],
```

Change the `Analysis` construction in both specs from `datas=[]` to:

```python
datas=settings.get("datas", []),
```

- [ ] **Step 7: Run focused packaging tests**

Run:

```bash
pytest tests/unit/test_distribution_packaging.py tests/unit/test_functional_package_api.py -v
```

Expected: all distribution and API/package-data tests PASS.

- [ ] **Step 8: Commit assets and packaging**

```bash
git add src/apps/nvda_remote/waves pyproject.toml packaging/windows_apps.spec packaging/macos_apps.spec tests/unit/test_distribution_packaging.py tests/unit/test_functional_package_api.py
git commit -m "build: package NVDA Remote cue sounds"
```

---

### Task 6: Verify Runtime Integration and Full Regression Suite

**Files:**
- Modify: `tests/unit/test_app_wx.py`
- Verify: all files changed in Tasks 1-5

**Interfaces:**
- Consumes: `AppRuntimeParts.wave_output` and `Capabilities.wave` from Task 3.
- Produces: verified NVDA Remote runtime wiring with no regressions in other applications.

- [ ] **Step 1: Add explicit NVDA Remote runtime wiring coverage**

In the existing NVDA Remote `build_runtime` test in `tests/unit/test_app_wx.py`, define a fake wave and include it in fake runtime parts:

```python
class FakeWaveOutput:
    def __init__(self) -> None:
        self.paths = []

    def play(self, path: str) -> None:
        self.paths.append(path)


wave_output = FakeWaveOutput()
capabilities = types.SimpleNamespace(
    speech=speaker,
    tone=tone_output,
    wave=wave_output,
)
```

Return `wave_output=wave_output` from the fake `build_app_runtime_parts` result and assert:

```python
assert runtime.app_service.capabilities.wave is wave_output
```

Leave access8graph and key-echo fixtures unchanged because they do not read `Capabilities.wave`.

- [ ] **Step 2: Run all focused affected tests**

Run:

```bash
pytest \
  tests/unit/test_nvda_remote_connection_ui.py \
  tests/unit/test_wave_output.py \
  tests/unit/test_tone_output.py \
  tests/unit/test_runtime_output.py \
  tests/unit/test_runtime_platform.py \
  tests/unit/test_runtime_platform_import.py \
  tests/unit/test_runtime_parts.py \
  tests/unit/test_functional_package_api.py \
  tests/unit/test_distribution_packaging.py \
  tests/unit/test_nvda_remote_cues.py \
  tests/unit/test_nvda_remote_use_cases.py \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_app_wx.py \
  -v
```

Expected: all focused tests PASS.

- [ ] **Step 3: Run the complete repository suite**

Run:

```bash
pytest tests/unit tests/integration -v
```

Expected: all unit and integration tests PASS with no collection errors, failures, or errors.

- [ ] **Step 4: Verify source and packaging integrity**

Run:

```bash
git diff --check
cmp ref/nvda/source/waves/connected.wav src/apps/nvda_remote/waves/connected.wav
cmp ref/nvda/source/waves/disconnected.wav src/apps/nvda_remote/waves/disconnected.wav
cmp ref/nvda/copying.txt src/apps/nvda_remote/waves/NVDA-COPYING.txt
```

Expected: all commands exit 0; `git diff --check` and all three `cmp` commands produce no output.

- [ ] **Step 5: Commit the runtime wiring test**

```bash
git add tests/unit/test_app_wx.py
git commit -m "test: verify NVDA Remote wave wiring"
```

## Completion Checklist

- [ ] Visible `&Name:`, `&Host:`, `&Port:`, and `&Key:` labels are paired with the intended controls.
- [ ] `WaveOutput` is concrete, asynchronous, failure-safe, and available through runtime capabilities.
- [ ] Connected/disconnected WAV cues and local/remote control speech fire once per actual transition.
- [ ] Missing optional wave output does not interrupt state transitions or required speech.
- [ ] NVDA WAV assets and `NVDA-COPYING.txt` are byte-identical to the approved references and carry GPL attribution.
- [ ] Setuptools and both PyInstaller specs include the cue directory.
- [ ] Focused and full test suites pass.
