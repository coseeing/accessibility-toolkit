# Tone Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real default-device tone playback and make `nvda_remote` play incoming NVDA Remote-compatible `type: "tone"` messages locally.

**Architecture:** Keep tone separate from speech. Add `RemoteMessageType.TONE`, route it through `MessageRouter` into the app/output layer, and implement a standalone tone backend that generates WAV bytes without importing NVDA runtime modules. Runtime composition injects the default tone backend into `nvda_remote` and `access8graph`.

**Tech Stack:** Python 3.11, stdlib `wave`/`struct`/`math`, stdlib platform playback (`winsound` on Windows, `afplay` subprocess on macOS), pytest.

---

### File Structure

| File | Responsibility |
|---|---|
| `src/interop/protocol/messages.py` | Add NVDA Remote-compatible `RemoteMessageType.TONE = "tone"` |
| `src/interop/protocol/routing/message_router.py` | Validate and route remote tone messages |
| `src/application/services.py` | Add optional tone handling to `OutputManager` |
| `src/adapters/outputs/tone.py` | Generate tone WAV bytes and play them through the default platform output |
| `src/bootstrap/platform.py` | Add `create_tone_output()` factory |
| `src/apps/nvda_remote/service.py` | Route incoming remote `tone` messages to local `OutputCapabilities.tone` |
| `src/apps/nvda_remote/main.py` | Inject default tone backend into `nvda_remote` runtime |
| `src/apps/access8graph/main.py` | Inject default tone backend into `access8graph` runtime |
| `tests/unit/test_message_router.py` | Protocol/router coverage for valid and invalid tone messages |
| `tests/unit/test_output_manager.py` | Output manager tone handling |
| `tests/unit/test_tone_output.py` | Tone normalization, WAV generation, and playback failure behavior |
| `tests/unit/test_bootstrap_platform.py` | Factory coverage for default tone output |
| `tests/unit/test_nvda_remote_app_service.py` | App service routes remote tone into local tone output |
| `tests/unit/test_app_wx.py` | Runtime composition injects tone output where expected |

---

### Task 1: Add Protocol and Router Tests for `tone`

**Files:**
- Modify: `tests/unit/test_message_router.py`

- [ ] **Step 1: Add a router helper that includes `on_tone`**

Near the top of `tests/unit/test_message_router.py`, after `FakeClipboard`, add:

```python
def build_router(seen):
    return MessageRouter(
        on_speech=lambda speech: seen.append(("speech", speech)),
        on_cancel=lambda: seen.append(("cancel", None)),
        on_pause=lambda paused: seen.append(("pause", paused)),
        on_clipboard=lambda text: seen.append(("clipboard", text)),
        on_tone=lambda hz, length, left, right: seen.append(
            ("tone", hz, length, left, right)
        ),
        on_status=lambda event: seen.append(("status", event)),
    )
```

Then replace every local `MessageRouter(...)` construction in this file that appends to `seen` with:

```python
router = build_router(seen)
```

For the `test_sequence_routes_from_router_to_backend_through_output_manager` construction, include `on_tone=lambda hz, length, left, right: None` in the existing explicit constructor.

- [ ] **Step 2: Add valid tone routing tests**

Append these tests to `tests/unit/test_message_router.py`:

```python
def test_remote_message_type_includes_nvda_remote_tone_value() -> None:
    assert RemoteMessageType.TONE.value == "tone"


def test_router_dispatches_tone_message() -> None:
    seen = []
    router = build_router(seen)

    router.handle_message(
        {
            "type": "tone",
            "hz": 440,
            "length": 80,
            "left": 25,
            "right": 75,
        }
    )

    assert seen == [("tone", 440.0, 80, 25, 75)]


def test_router_clamps_tone_balance_and_non_negative_duration() -> None:
    seen = []
    router = build_router(seen)

    router.handle_message(
        {
            "type": "tone",
            "hz": -10,
            "length": -5,
            "left": -20,
            "right": 250,
        }
    )

    assert seen == [("tone", 0.0, 0, 0, 100)]
```

- [ ] **Step 3: Add invalid tone payload tests**

Append these tests to `tests/unit/test_message_router.py`:

```python
def test_router_reports_missing_tone_field_as_invalid_message() -> None:
    seen = []
    router = build_router(seen)
    payload = {"type": "tone", "hz": 440, "length": 80, "left": 50}

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            {
                "kind": "invalid_message",
                "reason": "tone_fields_must_be_numeric",
                "payload": payload,
            },
        )
    ]


def test_router_reports_non_numeric_tone_field_as_invalid_message() -> None:
    seen = []
    router = build_router(seen)
    payload = {
        "type": "tone",
        "hz": "high",
        "length": 80,
        "left": 50,
        "right": 50,
    }

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            {
                "kind": "invalid_message",
                "reason": "tone_fields_must_be_numeric",
                "payload": payload,
            },
        )
    ]
```

- [ ] **Step 4: Run the focused router tests and verify failure**

Run:

```bash
python3 -m pytest tests/unit/test_message_router.py -k "tone or router_dispatches_speech_and_clipboard" -v
```

Expected: FAIL because `RemoteMessageType.TONE` and `MessageRouter.on_tone` do not exist yet.

- [ ] **Step 5: Commit failing tests**

Run:

```bash
git add tests/unit/test_message_router.py
git commit -m "test: add remote tone router coverage"
```

---

### Task 2: Implement `RemoteMessageType.TONE` and Router Dispatch

**Files:**
- Modify: `src/interop/protocol/messages.py`
- Modify: `src/interop/protocol/routing/message_router.py`
- Test: `tests/unit/test_message_router.py`

- [ ] **Step 1: Add the protocol enum value**

In `src/interop/protocol/messages.py`, add `TONE = "tone"` after `PAUSE_SPEECH`:

```python
    SPEAK = "speak"
    CANCEL = "cancel"
    PAUSE_SPEECH = "pause_speech"
    TONE = "tone"
    SET_CLIPBOARD_TEXT = "set_clipboard_text"
```

- [ ] **Step 2: Add tone callback and validation helpers**

Replace `src/interop/protocol/routing/message_router.py` with:

```python
from collections.abc import Callable
from typing import Any

from interop.speech.speech_sequence import SpeechSequence
from interop.protocol.messages import RemoteMessageType


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _coerce_float(payload: dict[str, Any], field_name: str) -> float:
    value = payload.get(field_name)
    if isinstance(value, bool):
        raise ValueError(field_name)
    return float(value)


def _coerce_int(payload: dict[str, Any], field_name: str) -> int:
    value = payload.get(field_name)
    if isinstance(value, bool):
        raise ValueError(field_name)
    return int(value)


class MessageRouter:
    def __init__(
        self,
        on_speech: Callable[[SpeechSequence], None],
        on_cancel: Callable[[], None],
        on_pause: Callable[[bool], None],
        on_clipboard: Callable[[str], None],
        on_tone: Callable[[float, int, int, int], None],
        on_status: Callable[[dict[str, Any]], None],
    ) -> None:
        self._on_speech = on_speech
        self._on_cancel = on_cancel
        self._on_pause = on_pause
        self._on_clipboard = on_clipboard
        self._on_tone = on_tone
        self._on_status = on_status

    def handle_message(self, payload: dict[str, Any]) -> None:
        match payload.get("type"):
            case RemoteMessageType.SPEAK.value:
                self._on_speech(SpeechSequence.from_remote_payload(payload))
            case RemoteMessageType.CANCEL.value:
                self._on_cancel()
            case RemoteMessageType.PAUSE_SPEECH.value:
                self._handle_pause_message(payload)
            case RemoteMessageType.TONE.value:
                self._handle_tone_message(payload)
            case RemoteMessageType.SET_CLIPBOARD_TEXT.value:
                self._handle_clipboard_message(payload)
            case _:
                self._on_status(
                    {
                        "kind": "remote",
                        "type": payload.get("type"),
                        "payload": payload,
                    }
                )

    def _handle_clipboard_message(self, payload: dict[str, Any]) -> None:
        text = payload.get("text")
        if not isinstance(text, str):
            self._on_status(
                {
                    "kind": "invalid_message",
                    "reason": "clipboard_text_must_be_string",
                    "payload": payload,
                }
            )
            return
        self._on_clipboard(text)

    def _handle_pause_message(self, payload: dict[str, Any]) -> None:
        switch = payload.get("switch")
        if not isinstance(switch, bool):
            self._on_status(
                {
                    "kind": "invalid_message",
                    "reason": "pause_switch_must_be_bool",
                    "payload": payload,
                }
            )
            return
        self._on_pause(switch)

    def _handle_tone_message(self, payload: dict[str, Any]) -> None:
        try:
            hz = max(0.0, _coerce_float(payload, "hz"))
            length = max(0, _coerce_int(payload, "length"))
            left = _clamp_int(_coerce_int(payload, "left"), 0, 100)
            right = _clamp_int(_coerce_int(payload, "right"), 0, 100)
        except (TypeError, ValueError):
            self._on_status(
                {
                    "kind": "invalid_message",
                    "reason": "tone_fields_must_be_numeric",
                    "payload": payload,
                }
            )
            return
        self._on_tone(hz, length, left, right)
```

- [ ] **Step 3: Run router tests**

Run:

```bash
python3 -m pytest tests/unit/test_message_router.py -v
```

Expected: PASS.

- [ ] **Step 4: Run serializer tests to confirm speech behavior is unchanged**

Run:

```bash
python3 -m pytest tests/unit/test_protocol_serializer.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit implementation**

Run:

```bash
git add src/interop/protocol/messages.py src/interop/protocol/routing/message_router.py tests/unit/test_message_router.py
git commit -m "feat: route remote tone messages"
```

---

### Task 3: Add Output Layer and `nvda_remote` Tone Handling

**Files:**
- Create: `tests/unit/test_output_manager.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`
- Modify: `src/application/services.py`
- Modify: `src/apps/nvda_remote/service.py`

- [ ] **Step 1: Create output manager tone tests**

Create `tests/unit/test_output_manager.py` with:

```python
from application.services import OutputManager
from interop.speech.speech_sequence import SpeechSequence


class FakeSpeech:
    def __init__(self) -> None:
        self.spoken = []
        self.cancelled = 0
        self.paused = []

    def speak(self, sequence: SpeechSequence) -> None:
        self.spoken.append(sequence)

    def cancel(self) -> None:
        self.cancelled += 1

    def pause(self, is_paused: bool) -> None:
        self.paused.append(is_paused)


class FakeClipboard:
    def __init__(self) -> None:
        self.text = ""

    def set_text(self, text: str) -> None:
        self.text = text

    def get_text(self) -> str:
        return self.text


class FakeTone:
    def __init__(self) -> None:
        self.calls = []

    def beep(self, hz: float, length: int, left: int = 50, right: int = 50) -> None:
        self.calls.append((hz, length, left, right))


def test_output_manager_routes_tone_to_tone_output() -> None:
    tone = FakeTone()
    manager = OutputManager(FakeSpeech(), FakeClipboard(), tone_output=tone)

    manager.handle_tone(440.0, 80, 25, 75)

    assert tone.calls == [(440.0, 80, 25, 75)]


def test_output_manager_tone_is_noop_without_tone_output() -> None:
    manager = OutputManager(FakeSpeech(), FakeClipboard())

    manager.handle_tone(440.0, 80, 50, 50)
```

- [ ] **Step 2: Extend `nvda_remote` service test fakes**

In `tests/unit/test_nvda_remote_app_service.py`, add this import:

```python
from interop.protocol.routing.message_router import MessageRouter
```

In `tests/unit/test_nvda_remote_app_service.py`, add this fake near the existing fake classes:

```python
class FakeToneService:
    def __init__(self) -> None:
        self.calls = []

    def beep(self, hz: float, length: int, left: int = 50, right: int = 50) -> None:
        self.calls.append((hz, length, left, right))
```

Update the `build_service` helper so it creates and passes a fake tone:

```python
tone = FakeToneService()
service = NvdaRemoteAppService(
    transport=transport,
    input_capture=capture,
    hotkey_capture=hotkey,
    clipboard=clipboard,
    outputs=OutputCapabilities(speech=FakeSpeechService(), tone=tone),
    main_thread_dispatch=dispatch,
)
return service, transport, capture, hotkey, dispatch_calls
```

- [ ] **Step 3: Add remote tone service tests**

Append these tests to `tests/unit/test_nvda_remote_app_service.py`:

```python
def test_nvda_remote_service_routes_remote_tone_into_tone_output():
    service, transport, _capture, _hotkey, _dispatch_calls = build_service()
    service.bind()

    transport.message_handler(
        {
            "type": RemoteMessageType.TONE.value,
            "hz": 440,
            "length": 80,
            "left": 25,
            "right": 75,
        }
    )

    assert service._outputs.tone.calls == [(440.0, 80, 25, 75)]


def test_nvda_remote_service_ignores_remote_tone_when_tone_output_is_missing():
    service, transport, _capture, _hotkey, _dispatch_calls = build_service()
    service._outputs = OutputCapabilities(speech=service._outputs.speech)
    service.router = MessageRouter(
        on_speech=service._outputs.speech.speak,
        on_cancel=service._outputs.speech.cancel,
        on_pause=service._outputs.speech.pause,
        on_clipboard=service.clipboard.set_text,
        on_tone=service._handle_tone,
        on_status=service._on_status,
    )
    service.bind()

    transport.message_handler(
        {
            "type": RemoteMessageType.TONE.value,
            "hz": 440,
            "length": 80,
            "left": 25,
            "right": 75,
        }
    )
```

- [ ] **Step 4: Run focused tests and verify failure**

Run:

```bash
python3 -m pytest tests/unit/test_output_manager.py tests/unit/test_nvda_remote_app_service.py -k "tone or routes_remote_speech" -v
```

Expected: FAIL because `OutputManager.handle_tone`, `MessageRouter.on_tone` call sites, and `NvdaRemoteAppService._handle_tone` are not implemented yet.

- [ ] **Step 5: Implement output manager tone support**

In `src/application/services.py`, update imports:

```python
from adapters.outputs.interfaces import SpeechOutput, ToneOutput
```

Change `OutputManager.__init__` to:

```python
class OutputManager:
    def __init__(
        self,
        speech_output: SpeechOutput,
        clipboard: ClipboardService,
        tone_output: ToneOutput | None = None,
    ) -> None:
        self.speech_output = speech_output
        self.clipboard = clipboard
        self.tone_output = tone_output
```

Add this method after `handle_pause`:

```python
    def handle_tone(
        self,
        hz: float,
        length: int,
        left: int = 50,
        right: int = 50,
    ) -> None:
        if self.tone_output is None:
            return
        self.tone_output.beep(hz, length, left, right)
```

- [ ] **Step 6: Implement `nvda_remote` tone handling**

In `src/apps/nvda_remote/service.py`, update the `MessageRouter` construction in `__init__` to include:

```python
            on_tone=self._handle_tone,
```

Add this method near `_handle_transport_message`:

```python
    def _handle_tone(
        self,
        hz: float,
        length: int,
        left: int = 50,
        right: int = 50,
    ) -> None:
        tone = self._outputs.tone
        if tone is None:
            return
        tone.beep(hz, length, left, right)
```

- [ ] **Step 7: Update remaining `MessageRouter` constructors**

Run:

```bash
rg -n "MessageRouter\\(" src tests
```

Every constructor must pass `on_tone`. Use `lambda hz, length, left, right: None` in tests that do not care about tone.

- [ ] **Step 8: Run focused tests**

Run:

```bash
python3 -m pytest tests/unit/test_output_manager.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_message_router.py -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

Run:

```bash
git add src/application/services.py src/apps/nvda_remote/service.py tests/unit/test_output_manager.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_message_router.py
git commit -m "feat: handle remote tones in output layer"
```

---

### Task 4: Implement Real Tone WAV Generation and Playback Backend

**Files:**
- Create: `tests/unit/test_tone_output.py`
- Modify: `src/adapters/outputs/tone.py`

- [ ] **Step 1: Add tone backend tests**

Create `tests/unit/test_tone_output.py` with:

```python
import logging
import wave
from io import BytesIO

from adapters.outputs.tone import (
    SAMPLE_RATE,
    DefaultToneOutput,
    generate_beep_wav,
    normalize_beep_parameters,
)


class FakePlaybackBackend:
    def __init__(self) -> None:
        self.calls = []

    def play(self, wav_data: bytes) -> None:
        self.calls.append(wav_data)


class FailingPlaybackBackend:
    def play(self, wav_data: bytes) -> None:
        raise RuntimeError("audio failed")


def test_normalize_beep_parameters_clamps_balance_and_non_negative_values() -> None:
    params = normalize_beep_parameters(-10, -5, -20, 250)

    assert params.hz == 0.0
    assert params.length == 0
    assert params.left == 0
    assert params.right == 100


def test_generate_beep_wav_creates_stereo_16_bit_wav() -> None:
    params = normalize_beep_parameters(440, 100, 25, 75)

    wav_data = generate_beep_wav(params)

    with wave.open(BytesIO(wav_data), "rb") as wav_file:
        assert wav_file.getnchannels() == 2
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == SAMPLE_RATE
        assert wav_file.getnframes() == SAMPLE_RATE // 10


def test_default_tone_output_plays_generated_wav() -> None:
    playback = FakePlaybackBackend()
    output = DefaultToneOutput(playback=playback)

    output.beep(440, 100, 25, 75)

    assert len(playback.calls) == 1
    assert playback.calls[0].startswith(b"RIFF")


def test_default_tone_output_skips_zero_length_tone() -> None:
    playback = FakePlaybackBackend()
    output = DefaultToneOutput(playback=playback)

    output.beep(440, 0, 50, 50)

    assert playback.calls == []


def test_default_tone_output_logs_backend_failures(caplog) -> None:
    output = DefaultToneOutput(playback=FailingPlaybackBackend())

    with caplog.at_level(logging.WARNING):
        output.beep(440, 100, 50, 50)

    assert "Failed to play tone" in caplog.text
```

- [ ] **Step 2: Run tone backend tests and verify failure**

Run:

```bash
python3 -m pytest tests/unit/test_tone_output.py -v
```

Expected: FAIL because the tone backend functions and classes do not exist yet.

- [ ] **Step 3: Implement tone generation and default playback**

Replace `src/adapters/outputs/tone.py` with:

```python
from __future__ import annotations

import logging
import math
import os
import struct
import subprocess
import sys
import tempfile
import threading
import wave
from dataclasses import dataclass
from io import BytesIO
from typing import Protocol

SAMPLE_RATE = 44100
BITS_PER_SAMPLE = 16
CHANNELS = 2
MAX_AMPLITUDE = 32767


class WavePlaybackBackend(Protocol):
    def play(self, wav_data: bytes) -> None: ...


@dataclass(frozen=True)
class BeepParameters:
    hz: float
    length: int
    left: int = 50
    right: int = 50


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def normalize_beep_parameters(
    hz: float,
    length: int,
    left: int = 50,
    right: int = 50,
) -> BeepParameters:
    return BeepParameters(
        hz=max(0.0, float(hz)),
        length=max(0, int(length)),
        left=_clamp_int(int(left), 0, 100),
        right=_clamp_int(int(right), 0, 100),
    )


def generate_beep_wav(params: BeepParameters) -> bytes:
    sample_count = int(SAMPLE_RATE * params.length / 1000)
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(BITS_PER_SAMPLE // 8)
        wav_file.setframerate(SAMPLE_RATE)
        for index in range(sample_count):
            phase = 2.0 * math.pi * params.hz * index / SAMPLE_RATE
            sample = int(math.sin(phase) * MAX_AMPLITUDE)
            left_sample = int(sample * params.left / 100)
            right_sample = int(sample * params.right / 100)
            wav_file.writeframesraw(struct.pack("<hh", left_sample, right_sample))
    return buffer.getvalue()


class DefaultWavePlaybackBackend:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(__name__)

    def play(self, wav_data: bytes) -> None:
        if sys.platform == "win32":
            self._play_windows(wav_data)
            return
        if sys.platform == "darwin":
            self._play_macos(wav_data)
            return
        self._logger.warning("Tone output is not supported on this platform")

    def _play_windows(self, wav_data: bytes) -> None:
        import winsound

        winsound.PlaySound(wav_data, winsound.SND_MEMORY)

    def _play_macos(self, wav_data: bytes) -> None:
        fd, path = tempfile.mkstemp(suffix=".wav")
        with os.fdopen(fd, "wb") as file:
            file.write(wav_data)
        process = subprocess.Popen(
            ["afplay", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        def cleanup() -> None:
            process.wait()
            try:
                os.remove(path)
            except OSError:
                self._logger.debug("Failed to remove temporary tone file", exc_info=True)

        threading.Thread(target=cleanup, daemon=True).start()


class DefaultToneOutput:
    def __init__(
        self,
        *,
        playback: WavePlaybackBackend | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._logger = logger or logging.getLogger(__name__)
        self._playback = playback or DefaultWavePlaybackBackend(logger=self._logger)

    @classmethod
    def load_default(cls) -> "DefaultToneOutput":
        return cls()

    def beep(
        self,
        hz: float,
        length: int,
        left: int = 50,
        right: int = 50,
    ) -> None:
        try:
            params = normalize_beep_parameters(hz, length, left, right)
        except (TypeError, ValueError):
            self._logger.warning(
                "Invalid tone parameters",
                extra={"hz": hz, "length": length, "left": left, "right": right},
            )
            return
        if params.hz <= 0 or params.length <= 0:
            return
        try:
            self._playback.play(generate_beep_wav(params))
        except Exception:
            self._logger.warning("Failed to play tone", exc_info=True)
```

- [ ] **Step 4: Run tone backend tests**

Run:

```bash
python3 -m pytest tests/unit/test_tone_output.py -v
```

Expected: PASS.

- [ ] **Step 5: Run access8graph output tests**

Run:

```bash
python3 -m pytest tests/unit/test_access8graph_output.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/adapters/outputs/tone.py tests/unit/test_tone_output.py
git commit -m "feat: add default tone output backend"
```

---

### Task 5: Compose Tone Backend into Runtime Factories

**Files:**
- Modify: `tests/unit/test_bootstrap_platform.py`
- Modify: `tests/unit/test_app_wx.py`
- Modify: `src/bootstrap/platform.py`
- Modify: `src/apps/nvda_remote/main.py`
- Modify: `src/apps/access8graph/main.py`

- [ ] **Step 1: Add platform factory tests**

In `tests/unit/test_bootstrap_platform.py`, add `create_tone_output` to the import list:

```python
from bootstrap.platform import (
    create_input_capture,
    create_hotkey_capture,
    create_clipboard_service,
    create_tone_output,
    default_speech_backend_id,
    default_speech_backend_options,
)
```

Append:

```python
class TestCreateToneOutput:
    def test_returns_default_tone_output(self):
        from adapters.outputs.tone import DefaultToneOutput

        tone = create_tone_output()

        assert isinstance(tone, DefaultToneOutput)
```

- [ ] **Step 2: Update `nvda_remote` runtime composition test**

In `tests/unit/test_app_wx.py`, inside `test_nvda_remote_main_build_runtime_composes_app_service_and_gui`, add this fake class after `FakeClipboard`:

```python
class FakeToneOutput:
    def __init__(self) -> None:
        self.calls = []

    def beep(self, hz, length, left=50, right=50):
        self.calls.append((hz, length, left, right))
```

After the existing `monkeypatch.setattr(nvda_remote_main, "create_clipboard_service", lambda: FakeClipboard())`, add:

```python
tone_output = FakeToneOutput()
monkeypatch.setattr(nvda_remote_main, "create_tone_output", lambda: tone_output)
```

After `assert runtime.app_service.outputs.speech is runtime.output_service`, add:

```python
assert runtime.app_service.outputs.tone is tone_output
```

- [ ] **Step 3: Add `access8graph` runtime composition test**

Append this test to `tests/unit/test_app_wx.py`:

```python
def test_access8graph_main_build_runtime_injects_tone_output(monkeypatch):
    install_fake_wx(monkeypatch)
    access8graph_main = importlib.import_module("apps.access8graph.main")

    class FakeOutputScheduler:
        pass

    class FakeSpeechService:
        def __init__(self, *, backend_options, selected_backend_id, scheduler=None):
            self.backend_options = backend_options
            self.selected_backend_id = selected_backend_id
            self.scheduler = scheduler

    class FakeQueuedOutputService:
        def __init__(self, *, speech):
            self.speech = speech

    class FakeKeyboardCapture:
        pass

    class FakeHotkeyCapture:
        def __init__(self) -> None:
            self.started = 0

        def start(self):
            self.started += 1

    class FakeToneOutput:
        def __init__(self) -> None:
            self.calls = []

        def beep(self, hz, length, left=50, right=50):
            self.calls.append((hz, length, left, right))

    class FakeKeyboardInputService:
        def __init__(self, capture, handler):
            self.capture = capture
            self.handler = handler

    class FakeAppService:
        enter_usage = HID.F11

        def __init__(self, *, hotkey_capture, input_capture, outputs, main_thread_dispatch):
            self.hotkey_capture = hotkey_capture
            self.input_capture = input_capture
            self._outputs = outputs
            self.main_thread_dispatch = main_thread_dispatch
            self.attached_input_service = None
            self.bind_calls = 0

        def attach_input_service(self, input_service):
            self.attached_input_service = input_service

        def bind(self):
            self.bind_calls += 1

    class FakeApp:
        dispatch = staticmethod(lambda callback: callback())

        def __init__(self, controller):
            self.controller = controller

    tone_output = FakeToneOutput()

    monkeypatch.setattr(access8graph_main, "OutputScheduler", FakeOutputScheduler)
    monkeypatch.setattr(access8graph_main, "SpeechService", FakeSpeechService)
    monkeypatch.setattr(access8graph_main, "QueuedOutputService", FakeQueuedOutputService)
    monkeypatch.setattr(access8graph_main, "KeyboardInputService", FakeKeyboardInputService)
    monkeypatch.setattr(access8graph_main, "Access8GraphAppService", FakeAppService)
    monkeypatch.setattr(access8graph_main, "create_input_capture", lambda: FakeKeyboardCapture())
    monkeypatch.setattr(access8graph_main, "create_hotkey_capture", lambda usage=HID.F11: FakeHotkeyCapture())
    monkeypatch.setattr(access8graph_main, "create_tone_output", lambda: tone_output)
    monkeypatch.setattr(access8graph_main, "default_speech_backend_options", lambda scheduler: ("backend",))
    monkeypatch.setattr(access8graph_main, "default_speech_backend_id", lambda: "pyttsx3")
    monkeypatch.setitem(
        sys.modules,
        "ui.access8graph.app",
        types.SimpleNamespace(Access8GraphApp=FakeApp),
    )

    runtime = access8graph_main.build_runtime()

    assert runtime.app_service._outputs.speech is runtime.output_service
    assert runtime.app_service._outputs.tone is tone_output
    assert runtime.tone_output is tone_output
    assert runtime.hotkey_capture.started == 1
    assert runtime.app_service.bind_calls == 1
    assert runtime.app.controller is runtime.app_service
```

- [ ] **Step 4: Run focused runtime tests and verify failure**

Run:

```bash
python3 -m pytest tests/unit/test_bootstrap_platform.py tests/unit/test_app_wx.py -k "tone or build_runtime" -v
```

Expected: FAIL because `create_tone_output` is not defined and runtimes do not inject tone yet.

- [ ] **Step 5: Add platform tone factory**

In `src/bootstrap/platform.py`, add this import near the existing output imports:

```python
from adapters.outputs.tone import DefaultToneOutput
```

Add this public factory after `create_clipboard_service()`:

```python
def create_tone_output() -> DefaultToneOutput:
    return DefaultToneOutput.load_default()
```

- [ ] **Step 6: Inject tone into `nvda_remote` runtime**

In `src/apps/nvda_remote/main.py`, import the factory:

```python
from bootstrap.platform import (
    create_input_capture,
    create_hotkey_capture,
    create_clipboard_service,
    create_tone_output,
    default_speech_backend_options,
    default_speech_backend_id,
)
```

Add `tone_output` to `NvdaRemoteRuntime`:

```python
    tone_output: object
```

In `build_runtime()`, create and inject it:

```python
    tone_output = create_tone_output()
```

Then update `OutputCapabilities`:

```python
        outputs=OutputCapabilities(
            speech=output_service,
            tone=tone_output,
        ),
```

And include it in the returned runtime:

```python
        tone_output=tone_output,
```

- [ ] **Step 7: Inject tone into `access8graph` runtime**

In `src/apps/access8graph/main.py`, import `create_tone_output`:

```python
from bootstrap.platform import (
    create_hotkey_capture,
    create_input_capture,
    create_tone_output,
    default_speech_backend_id,
    default_speech_backend_options,
)
```

Add `tone_output` to `Access8GraphRuntime`:

```python
    tone_output: object
```

In `build_runtime()`, create and inject it:

```python
    tone_output = create_tone_output()
```

Then update `OutputCapabilities`:

```python
        outputs=OutputCapabilities(speech=output_service, tone=tone_output),
```

And include it in the returned runtime:

```python
        tone_output=tone_output,
```

- [ ] **Step 8: Run focused runtime tests**

Run:

```bash
python3 -m pytest tests/unit/test_bootstrap_platform.py tests/unit/test_app_wx.py -k "tone or build_runtime" -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

Run:

```bash
git add src/bootstrap/platform.py src/apps/nvda_remote/main.py src/apps/access8graph/main.py tests/unit/test_bootstrap_platform.py tests/unit/test_app_wx.py
git commit -m "feat: compose default tone output"
```

---

### Task 6: Final Verification and Documentation Check

**Files:**
- Verify only; no planned source changes.

- [ ] **Step 1: Confirm no NVDA runtime imports were added**

Run:

```bash
rg -n "import config|import extensionPoints|import nvwave|NVDAHelper|logHandler" src/adapters/outputs/tone.py src
```

Expected: no matches in `src/adapters/outputs/tone.py`. Existing unrelated references in docs or vendored references do not block this task.

- [ ] **Step 2: Confirm speech serialization was not changed for tone**

Run:

```bash
rg -n "BeepCommand|ToneCommand|tone" src/interop/speech src/interop/protocol/serializer.py
```

Expected: no matches for `BeepCommand` or `ToneCommand`; `serializer.py` should still only have special handling for `type == "speak"`.

- [ ] **Step 3: Run focused unit tests**

Run:

```bash
python3 -m pytest tests/unit/test_message_router.py tests/unit/test_protocol_serializer.py tests/unit/test_output_manager.py tests/unit/test_tone_output.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_access8graph_output.py tests/unit/test_bootstrap_platform.py -v
```

Expected: PASS.

- [ ] **Step 4: Run full test suite**

Run:

```bash
python3 -m pytest tests/unit tests/integration -v
```

Expected: PASS.

- [ ] **Step 5: Commit final test-only adjustments if needed**

If Step 4 required test expectation updates without behavior changes, commit them:

```bash
git add tests
git commit -m "test: align tone runtime expectations"
```

If no files changed, do not create an empty commit.

---

### Implementation Notes

- Keep remote tone protocol compatible with NVDA Remote: the message type is exactly `tone`, with `hz`, `length`, `left`, and `right`.
- Keep tone out of `SpeechSequence`; the serializer should not need tone-specific hooks.
- Do not add tone configuration or UI.
- The tone backend tests must never play audio; use injected fake playback backends.
- Runtime tone injection should be optional from the app service perspective because tests and future apps may construct `OutputCapabilities` without `tone`.
