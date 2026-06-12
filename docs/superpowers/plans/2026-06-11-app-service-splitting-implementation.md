# App Service Splitting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `NvdaRemoteAppService` and `KeyEchoAppService` into thin app facades plus focused use cases, while unifying state-transition hotkeys behind one mapping-based mechanism and preserving current UI behavior.

**Architecture:** Keep the existing UI/controller surface stable, but move business rules out of the current app service classes into dedicated use-case modules. Add a reusable state-transition hotkey pattern to both apps so `nvda_remote` and `key_echo` stop hard-coding mode-toggle keys inside general event handlers. Preserve current bootstrap/runtime wiring and avoid redesigning transport, output architecture, or typed events in this phase.

**Tech Stack:** Python 3.12+, pytest, monkeypatch, wxPython shell integration, existing `KeyboardInputService`, `RemoteSession`, `MessageRouter`, `SpeechService`

---

## Planned File Structure

### New files

- `src/apps/nvda_remote/facade.py`
  - Thin UI-facing facade for `nvda_remote`
- `src/apps/nvda_remote/use_cases/__init__.py`
- `src/apps/nvda_remote/use_cases/connection.py`
  - Connection/disconnection orchestration
- `src/apps/nvda_remote/use_cases/control_mode.py`
  - Start/stop control rules
- `src/apps/nvda_remote/use_cases/input_forwarding.py`
  - Remote key forwarding and local suppression rules
- `src/apps/nvda_remote/use_cases/speech_settings.py`
  - Speech backend/voice/rate/pitch/volume control
- `src/apps/nvda_remote/use_cases/state_transition_hotkeys.py`
  - Mapping-based state-transition hotkey evaluation
- `src/apps/key_echo/facade.py`
  - Thin UI-facing facade for `key_echo`
- `src/apps/key_echo/use_cases/__init__.py`
- `src/apps/key_echo/use_cases/echo_control.py`
  - Start/stop echo lifecycle rules
- `src/apps/key_echo/use_cases/echo_input.py`
  - Keydown-to-speech behavior
- `src/apps/key_echo/use_cases/speech_settings.py`
  - Speech backend/voice/rate/pitch/volume control
- `src/apps/key_echo/use_cases/state_transition_hotkeys.py`
  - Mapping-based state-transition hotkey evaluation
- `tests/unit/test_nvda_remote_use_cases.py`
  - Unit tests for `nvda_remote` use cases
- `tests/unit/test_key_echo_use_cases.py`
  - Unit tests for `key_echo` use cases

### Modified files

- `src/apps/nvda_remote/service.py`
  - Compatibility wrapper or re-export to preserve import surface
- `src/apps/key_echo/service.py`
  - Compatibility wrapper or re-export to preserve import surface
- `src/apps/nvda_remote/main.py`
  - Instantiate facade instead of monolithic service
- `src/apps/key_echo/main.py`
  - Instantiate facade instead of monolithic service
- `tests/unit/test_nvda_remote_app_service.py`
  - Adjust imports and assert facade-compatible behavior
- `tests/unit/test_key_echo_app_service.py`
  - Add `Enter` hotkey expectations and adapt facade surface
- `tests/unit/test_app_wx.py`
  - Verify main/runtime wiring still composes the UI against the facade

---

### Task 1: Add failing tests for unified state-transition hotkeys

**Files:**
- Modify: `tests/unit/test_nvda_remote_app_service.py`
- Modify: `tests/unit/test_key_echo_app_service.py`
- Create: `tests/unit/test_nvda_remote_use_cases.py`
- Create: `tests/unit/test_key_echo_use_cases.py`

- [ ] **Step 1: Add facade-level regression tests for hotkey behavior**

Add to `tests/unit/test_nvda_remote_app_service.py`:

```python
def test_nvda_remote_service_f11_toggles_control_on_keydown_only():
    service, _transport, capture, hotkey, _dispatch_calls = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.state.control_state = service.state.control_state.SUSPENDED

    keydown_decision = service.handle_key_event(
        KeyEvent(vk=0x7A, scan=87, extended=False, pressed=True)
    )
    keyup_decision = service.handle_key_event(
        KeyEvent(vk=0x7A, scan=87, extended=False, pressed=False)
    )

    assert keydown_decision == KeyEventDecision.SUPPRESS
    assert keyup_decision == KeyEventDecision.SUPPRESS
    assert service.state.control_state == service.state.control_state.CONTROLLING
    assert capture.started == 1
    assert hotkey.stopped == 1
```

Add to `tests/unit/test_key_echo_app_service.py`:

```python
def test_key_echo_app_service_starts_echo_on_enter_keydown() -> None:
    capture = FakeCapture()
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output))
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)

    decision = service.handle_key_event(
        KeyEvent(vk=0x0D, scan=28, extended=False, pressed=True)
    )

    assert decision == KeyEventDecision.SUPPRESS
    assert capture.start_calls == 1
    assert service.is_echo_running() is True
    assert speech_output.spoken == []


def test_key_echo_app_service_enter_keyup_does_not_duplicate_start() -> None:
    capture = FakeCapture()
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output))
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)

    service.handle_key_event(KeyEvent(vk=0x0D, scan=28, extended=False, pressed=True))
    decision = service.handle_key_event(
        KeyEvent(vk=0x0D, scan=28, extended=False, pressed=False)
    )

    assert decision == KeyEventDecision.SUPPRESS
    assert capture.start_calls == 1
```

- [ ] **Step 2: Add new use-case-level failing tests**

Create `tests/unit/test_nvda_remote_use_cases.py`:

```python
from adapters.inputs.base import KeyEventDecision
from interop.key.key_event import KeyEvent

from apps.nvda_remote.use_cases.state_transition_hotkeys import (
    NvdaRemoteHotkeyAction,
    NvdaRemoteStateTransitionHotkeyUseCase,
)


def test_nvda_hotkey_use_case_maps_f11_keydown_to_toggle_control():
    use_case = NvdaRemoteStateTransitionHotkeyUseCase(
        mapping={0x7A: NvdaRemoteHotkeyAction.TOGGLE_CONTROL}
    )

    action = use_case.match(KeyEvent(vk=0x7A, scan=87, extended=False, pressed=True))

    assert action == NvdaRemoteHotkeyAction.TOGGLE_CONTROL


def test_nvda_hotkey_use_case_ignores_f11_keyup():
    use_case = NvdaRemoteStateTransitionHotkeyUseCase(
        mapping={0x7A: NvdaRemoteHotkeyAction.TOGGLE_CONTROL}
    )

    action = use_case.match(KeyEvent(vk=0x7A, scan=87, extended=False, pressed=False))

    assert action is None
```

Create `tests/unit/test_key_echo_use_cases.py`:

```python
from interop.key.key_event import KeyEvent

from apps.key_echo.use_cases.state_transition_hotkeys import (
    KeyEchoHotkeyAction,
    KeyEchoStateTransitionHotkeyUseCase,
)


def test_key_echo_hotkey_use_case_maps_enter_to_start_echo():
    use_case = KeyEchoStateTransitionHotkeyUseCase(
        mapping={
            0x0D: KeyEchoHotkeyAction.START_ECHO,
            0x1B: KeyEchoHotkeyAction.STOP_ECHO,
        }
    )

    action = use_case.match(KeyEvent(vk=0x0D, scan=28, extended=False, pressed=True))

    assert action == KeyEchoHotkeyAction.START_ECHO


def test_key_echo_hotkey_use_case_maps_escape_to_stop_echo():
    use_case = KeyEchoStateTransitionHotkeyUseCase(
        mapping={
            0x0D: KeyEchoHotkeyAction.START_ECHO,
            0x1B: KeyEchoHotkeyAction.STOP_ECHO,
        }
    )

    action = use_case.match(KeyEvent(vk=0x1B, scan=1, extended=False, pressed=True))

    assert action == KeyEchoHotkeyAction.STOP_ECHO


def test_key_echo_hotkey_use_case_ignores_keyup():
    use_case = KeyEchoStateTransitionHotkeyUseCase(
        mapping={
            0x0D: KeyEchoHotkeyAction.START_ECHO,
            0x1B: KeyEchoHotkeyAction.STOP_ECHO,
        }
    )

    action = use_case.match(KeyEvent(vk=0x1B, scan=1, extended=False, pressed=False))

    assert action is None
```

- [ ] **Step 3: Run targeted tests and verify failure**

Run:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_key_echo_app_service.py \
  tests/unit/test_nvda_remote_use_cases.py \
  tests/unit/test_key_echo_use_cases.py -v
```

Expected:

- FAIL because the new `use_cases` modules do not exist yet
- FAIL because `KeyEchoAppService` does not start echo on `Enter`
- FAIL because `NvdaRemoteAppService` currently passes `F11` through while suspended

- [ ] **Step 4: Commit the failing tests**

```bash
git add \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_key_echo_app_service.py \
  tests/unit/test_nvda_remote_use_cases.py \
  tests/unit/test_key_echo_use_cases.py
git commit -m "test: cover app facade hotkey transitions"
```

### Task 2: Implement state-transition hotkey use cases for both apps

**Files:**
- Create: `src/apps/nvda_remote/use_cases/__init__.py`
- Create: `src/apps/nvda_remote/use_cases/state_transition_hotkeys.py`
- Create: `src/apps/key_echo/use_cases/__init__.py`
- Create: `src/apps/key_echo/use_cases/state_transition_hotkeys.py`
- Test: `tests/unit/test_nvda_remote_use_cases.py`
- Test: `tests/unit/test_key_echo_use_cases.py`

- [ ] **Step 1: Implement `nvda_remote` hotkey use case**

Write `src/apps/nvda_remote/use_cases/state_transition_hotkeys.py`:

```python
from enum import StrEnum

from interop.key.key_event import KeyEvent


class NvdaRemoteHotkeyAction(StrEnum):
    TOGGLE_CONTROL = "toggle_control"


class NvdaRemoteStateTransitionHotkeyUseCase:
    def __init__(self, *, mapping: dict[int, NvdaRemoteHotkeyAction]) -> None:
        self._mapping = dict(mapping)

    @classmethod
    def default(cls) -> "NvdaRemoteStateTransitionHotkeyUseCase":
        return cls(mapping={0x7A: NvdaRemoteHotkeyAction.TOGGLE_CONTROL})

    def match(self, event: KeyEvent) -> NvdaRemoteHotkeyAction | None:
        if not event.pressed:
            return None
        return self._mapping.get(event.vk)
```

- [ ] **Step 2: Implement `key_echo` hotkey use case**

Write `src/apps/key_echo/use_cases/state_transition_hotkeys.py`:

```python
from enum import StrEnum

from interop.key.key_event import KeyEvent


class KeyEchoHotkeyAction(StrEnum):
    START_ECHO = "start_echo"
    STOP_ECHO = "stop_echo"


class KeyEchoStateTransitionHotkeyUseCase:
    def __init__(self, *, mapping: dict[int, KeyEchoHotkeyAction]) -> None:
        self._mapping = dict(mapping)

    @classmethod
    def default(cls) -> "KeyEchoStateTransitionHotkeyUseCase":
        return cls(
            mapping={
                0x0D: KeyEchoHotkeyAction.START_ECHO,
                0x1B: KeyEchoHotkeyAction.STOP_ECHO,
            }
        )

    def match(self, event: KeyEvent) -> KeyEchoHotkeyAction | None:
        if not event.pressed:
            return None
        return self._mapping.get(event.vk)
```

- [ ] **Step 3: Add package `__init__` exports**

Write `src/apps/nvda_remote/use_cases/__init__.py`:

```python
from apps.nvda_remote.use_cases.state_transition_hotkeys import (
    NvdaRemoteHotkeyAction,
    NvdaRemoteStateTransitionHotkeyUseCase,
)
```

Write `src/apps/key_echo/use_cases/__init__.py`:

```python
from apps.key_echo.use_cases.state_transition_hotkeys import (
    KeyEchoHotkeyAction,
    KeyEchoStateTransitionHotkeyUseCase,
)
```

- [ ] **Step 4: Run targeted use-case tests**

Run:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/unit/test_nvda_remote_use_cases.py \
  tests/unit/test_key_echo_use_cases.py -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  src/apps/nvda_remote/use_cases/__init__.py \
  src/apps/nvda_remote/use_cases/state_transition_hotkeys.py \
  src/apps/key_echo/use_cases/__init__.py \
  src/apps/key_echo/use_cases/state_transition_hotkeys.py \
  tests/unit/test_nvda_remote_use_cases.py \
  tests/unit/test_key_echo_use_cases.py
git commit -m "feat: add state transition hotkey use cases"
```

### Task 3: Extract speech settings use cases for both apps

**Files:**
- Create: `src/apps/nvda_remote/use_cases/speech_settings.py`
- Create: `src/apps/key_echo/use_cases/speech_settings.py`
- Modify: `tests/unit/test_nvda_remote_use_cases.py`
- Modify: `tests/unit/test_key_echo_use_cases.py`

- [ ] **Step 1: Add failing speech settings tests**

Add to `tests/unit/test_nvda_remote_use_cases.py`:

```python
class FakeSpeech:
    def __init__(self):
        self.backend_id = "nvda_controller"
        self.voice_id = None
        self.rate = None
        self.pitch = None
        self.volume = None

    def get_backend_options(self):
        return (("nvda_controller", "NVDA Controller"),)

    def get_selected_backend(self):
        return self.backend_id

    def set_backend(self, backend_id):
        self.backend_id = backend_id

    def list_voices(self):
        return ()

    def get_voice(self):
        return self.voice_id

    def set_voice(self, voice_id):
        self.voice_id = voice_id

    def get_rate(self):
        return self.rate

    def set_rate(self, value):
        self.rate = value

    def get_pitch(self):
        return self.pitch

    def set_pitch(self, value):
        self.pitch = value

    def get_volume(self):
        return self.volume

    def set_volume(self, value):
        self.volume = value


def test_nvda_speech_settings_use_case_proxies_backend_and_voice_controls():
    from apps.nvda_remote.use_cases.speech_settings import NvdaRemoteSpeechSettingsUseCase

    speech = FakeSpeech()
    saved = []
    use_case = NvdaRemoteSpeechSettingsUseCase(
        speech=speech,
        on_backend_changed=saved.append,
    )

    use_case.set_backend("pyttsx3")
    use_case.set_voice("voice-2")
    use_case.set_rate(120)

    assert speech.get_selected_backend() == "pyttsx3"
    assert speech.get_voice() == "voice-2"
    assert speech.get_rate() == 120
    assert saved == ["pyttsx3"]
```

Mirror the same pattern for `key_echo` in `tests/unit/test_key_echo_use_cases.py`.

- [ ] **Step 2: Implement `nvda_remote` speech settings use case**

Write `src/apps/nvda_remote/use_cases/speech_settings.py`:

```python
from collections.abc import Callable

from application.output_service import SpeechOutputService


class NvdaRemoteSpeechSettingsUseCase:
    def __init__(
        self,
        *,
        speech: SpeechOutputService,
        on_backend_changed: Callable[[str], None] | None = None,
    ) -> None:
        self._speech = speech
        self._on_backend_changed = on_backend_changed

    def get_backend_options(self) -> tuple[tuple[str, str], ...]:
        return self._speech.get_backend_options()

    def get_selected_backend(self) -> str:
        return self._speech.get_selected_backend()

    def set_backend(self, backend_id: str) -> None:
        self._speech.set_backend(backend_id)
        if self._on_backend_changed is not None:
            self._on_backend_changed(backend_id)

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return self._speech.list_voices()

    def get_voice(self) -> str | None:
        return self._speech.get_voice()

    def set_voice(self, voice_id: str) -> None:
        self._speech.set_voice(voice_id)

    def get_rate(self) -> int | None:
        return self._speech.get_rate()

    def set_rate(self, value: int) -> None:
        self._speech.set_rate(value)

    def get_pitch(self) -> int | None:
        return self._speech.get_pitch()

    def set_pitch(self, value: int) -> None:
        self._speech.set_pitch(value)

    def get_volume(self) -> int | None:
        return self._speech.get_volume()

    def set_volume(self, value: int) -> None:
        self._speech.set_volume(value)
```

- [ ] **Step 3: Implement `key_echo` speech settings use case**

Write `src/apps/key_echo/use_cases/speech_settings.py`:

```python
from application.output_service import SpeechOutputService


class KeyEchoSpeechSettingsUseCase:
    def __init__(self, *, speech: SpeechOutputService) -> None:
        self._speech = speech

    def get_backend_options(self) -> tuple[tuple[str, str], ...]:
        return self._speech.get_backend_options()

    def get_selected_backend(self) -> str:
        return self._speech.get_selected_backend()

    def set_backend(self, backend_id: str) -> None:
        self._speech.set_backend(backend_id)

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return self._speech.list_voices()

    def get_voice(self) -> str | None:
        return self._speech.get_voice()

    def set_voice(self, voice_id: str) -> None:
        self._speech.set_voice(voice_id)

    def get_rate(self) -> int | None:
        return self._speech.get_rate()

    def set_rate(self, value: int) -> None:
        self._speech.set_rate(value)

    def get_pitch(self) -> int | None:
        return self._speech.get_pitch()

    def set_pitch(self, value: int) -> None:
        self._speech.set_pitch(value)

    def get_volume(self) -> int | None:
        return self._speech.get_volume()

    def set_volume(self, value: int) -> None:
        self._speech.set_volume(value)
```

- [ ] **Step 4: Run speech settings tests**

Run:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/unit/test_nvda_remote_use_cases.py \
  tests/unit/test_key_echo_use_cases.py -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  src/apps/nvda_remote/use_cases/speech_settings.py \
  src/apps/key_echo/use_cases/speech_settings.py \
  tests/unit/test_nvda_remote_use_cases.py \
  tests/unit/test_key_echo_use_cases.py
git commit -m "feat: add app speech settings use cases"
```

### Task 4: Extract control-mode and echo-control use cases

**Files:**
- Create: `src/apps/nvda_remote/use_cases/control_mode.py`
- Create: `src/apps/key_echo/use_cases/echo_control.py`
- Modify: `tests/unit/test_nvda_remote_use_cases.py`
- Modify: `tests/unit/test_key_echo_use_cases.py`

- [ ] **Step 1: Add failing control lifecycle tests**

Add to `tests/unit/test_nvda_remote_use_cases.py`:

```python
from application.state import ConnectionState, ControlState, RuntimeState


class FakeRunningCapture:
    def __init__(self):
        self.running = False
        self.started = 0
        self.stopped = 0

    def start(self):
        self.started += 1
        self.running = True

    def stop(self):
        self.stopped += 1
        self.running = False


class FakeRunningHotkey(FakeRunningCapture):
    pass


def test_control_mode_use_case_start_control_starts_capture_and_stops_hotkey():
    from apps.nvda_remote.use_cases.control_mode import NvdaRemoteControlModeUseCase

    state = RuntimeState(
        connection_state=ConnectionState.CONNECTED,
        control_state=ControlState.SUSPENDED,
    )
    input_capture = FakeRunningCapture()
    hotkey_capture = FakeRunningHotkey()
    hotkey_capture.running = True

    use_case = NvdaRemoteControlModeUseCase(
        state=state,
        input_capture=input_capture,
        hotkey_capture=hotkey_capture,
        notify_error=lambda _message: None,
        notify_status=lambda _status: None,
    )

    use_case.start_control()

    assert state.control_state == ControlState.CONTROLLING
    assert input_capture.started == 1
    assert hotkey_capture.stopped == 1
```

Add to `tests/unit/test_key_echo_use_cases.py`:

```python
def test_echo_control_use_case_start_and_stop_echo():
    from apps.key_echo.use_cases.echo_control import KeyEchoControlUseCase

    class FakeInputService:
        def __init__(self):
            self.running = False
            self.started = 0
            self.stopped = 0

        def start(self):
            self.started += 1
            self.running = True

        def stop(self):
            self.stopped += 1
            self.running = False

    statuses = []
    input_service = FakeInputService()
    use_case = KeyEchoControlUseCase(
        input_service=input_service,
        notify_status=statuses.append,
    )

    use_case.start_echo()
    use_case.stop_echo()

    assert input_service.started == 1
    assert input_service.stopped == 1
    assert statuses == [
        {"kind": "echo", "state": "running"},
        {"kind": "echo", "state": "stopped"},
    ]
```

- [ ] **Step 2: Implement `NvdaRemoteControlModeUseCase`**

Write `src/apps/nvda_remote/use_cases/control_mode.py`:

```python
from collections.abc import Callable
from typing import Any

from application.state import ConnectionState, ControlState, RuntimeState


class NvdaRemoteControlModeUseCase:
    def __init__(
        self,
        *,
        state: RuntimeState,
        input_capture: Any,
        hotkey_capture: Any,
        notify_error: Callable[[str], None],
        notify_status: Callable[[dict[str, str]], None],
    ) -> None:
        self._state = state
        self._input_capture = input_capture
        self._hotkey_capture = hotkey_capture
        self._notify_error = notify_error
        self._notify_status = notify_status

    def start_control(self) -> None:
        if self._hotkey_capture.running:
            self._hotkey_capture.stop()
        try:
            if not self._input_capture.running:
                self._input_capture.start()
        except Exception as error:
            if self._state.connection_state != ConnectionState.IDLE:
                try:
                    if not self._hotkey_capture.running:
                        self._hotkey_capture.start()
                except Exception:
                    pass
            self._notify_error(str(error))
            return
        self._state.control_state = ControlState.CONTROLLING
        self._notify_status({"kind": "control", "state": ControlState.CONTROLLING.value})

    def stop_control(self) -> None:
        if self._input_capture.running:
            self._input_capture.stop()
        self._state.control_state = ControlState.SUSPENDED
        if self._state.connection_state != ConnectionState.IDLE and not self._hotkey_capture.running:
            try:
                self._hotkey_capture.start()
            except Exception as error:
                self._notify_error(str(error))
        self._notify_status({"kind": "control", "state": ControlState.SUSPENDED.value})
```

- [ ] **Step 3: Implement `KeyEchoControlUseCase`**

Write `src/apps/key_echo/use_cases/echo_control.py`:

```python
from collections.abc import Callable

from application.keyboard import KeyboardInputService


class KeyEchoControlUseCase:
    def __init__(
        self,
        *,
        input_service: KeyboardInputService,
        notify_status: Callable[[dict[str, str]], None],
    ) -> None:
        self._input_service = input_service
        self._notify_status = notify_status

    def start_echo(self) -> None:
        if not self._input_service.running:
            self._input_service.start()
        self._notify_status({"kind": "echo", "state": "running"})

    def stop_echo(self) -> None:
        if self._input_service.running:
            self._input_service.stop()
        self._notify_status({"kind": "echo", "state": "stopped"})

    def is_running(self) -> bool:
        return self._input_service.running
```

- [ ] **Step 4: Run lifecycle tests**

Run:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/unit/test_nvda_remote_use_cases.py \
  tests/unit/test_key_echo_use_cases.py -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  src/apps/nvda_remote/use_cases/control_mode.py \
  src/apps/key_echo/use_cases/echo_control.py \
  tests/unit/test_nvda_remote_use_cases.py \
  tests/unit/test_key_echo_use_cases.py
git commit -m "feat: add app control lifecycle use cases"
```

### Task 5: Extract input-forwarding and echo-input use cases

**Files:**
- Create: `src/apps/nvda_remote/use_cases/input_forwarding.py`
- Create: `src/apps/key_echo/use_cases/echo_input.py`
- Modify: `tests/unit/test_nvda_remote_use_cases.py`
- Modify: `tests/unit/test_key_echo_use_cases.py`

- [ ] **Step 1: Add failing input-behavior tests**

Add to `tests/unit/test_nvda_remote_use_cases.py`:

```python
def test_input_forwarding_use_case_sends_remote_key_when_controlling():
    from apps.nvda_remote.use_cases.input_forwarding import NvdaRemoteInputForwardingUseCase

    sent = []
    use_case = NvdaRemoteInputForwardingUseCase(
        is_connected=lambda: True,
        is_controlling=lambda: True,
        send_key=lambda payload: sent.append(payload),
        on_local_stop=lambda: None,
    )
    event = KeyEvent(vk=65, scan=30, extended=False, pressed=True)

    decision = use_case.handle(event)

    assert decision == KeyEventDecision.SUPPRESS
    assert sent == [event.to_remote_payload()]
```

Add to `tests/unit/test_key_echo_use_cases.py`:

```python
def test_echo_input_use_case_speaks_vk_text_on_keydown():
    from apps.key_echo.use_cases.echo_input import KeyEchoInputUseCase

    calls = []
    use_case = KeyEchoInputUseCase(
        cancel=lambda: calls.append(("cancel", None)),
        speak=lambda sequence: calls.append(("speak", sequence)),
    )

    decision = use_case.handle(KeyEvent(vk=65, scan=30, extended=False, pressed=True))

    assert decision == KeyEventDecision.SUPPRESS
    assert calls[0] == ("cancel", None)
    assert calls[1][0] == "speak"
```

- [ ] **Step 2: Implement `NvdaRemoteInputForwardingUseCase`**

Write `src/apps/nvda_remote/use_cases/input_forwarding.py`:

```python
from collections.abc import Callable

from adapters.inputs.base import KeyEventDecision
from interop.key.key_event import KeyEvent


class NvdaRemoteInputForwardingUseCase:
    def __init__(
        self,
        *,
        is_connected: Callable[[], bool],
        is_controlling: Callable[[], bool],
        send_key: Callable[[dict[str, int | bool | None]], None],
        on_local_stop: Callable[[], None],
        local_stop_vk: int = 0x7A,
    ) -> None:
        self._is_connected = is_connected
        self._is_controlling = is_controlling
        self._send_key = send_key
        self._on_local_stop = on_local_stop
        self._local_stop_vk = local_stop_vk
        self._suppressed_keyups: set[int] = set()

    def handle(self, event: KeyEvent) -> KeyEventDecision:
        if not event.pressed and event.vk in self._suppressed_keyups:
            self._suppressed_keyups.discard(event.vk)
            return KeyEventDecision.SUPPRESS
        if not self._is_connected():
            return KeyEventDecision.PASS_THROUGH
        if event.vk == self._local_stop_vk and self._is_controlling():
            if event.pressed:
                self._on_local_stop()
                self._suppressed_keyups.add(event.vk)
            return KeyEventDecision.SUPPRESS
        if not self._is_controlling():
            return KeyEventDecision.PASS_THROUGH
        self._send_key(event.to_remote_payload())
        return KeyEventDecision.SUPPRESS

    def clear(self) -> None:
        self._suppressed_keyups.clear()
```

- [ ] **Step 3: Implement `KeyEchoInputUseCase`**

Write `src/apps/key_echo/use_cases/echo_input.py`:

```python
from collections.abc import Callable

from adapters.inputs.base import KeyEventDecision
from interop.key.key_event import KeyEvent
from interop.speech.speech_sequence import SpeechSequence


class KeyEchoInputUseCase:
    def __init__(
        self,
        *,
        cancel: Callable[[], None],
        speak: Callable[[SpeechSequence], None],
    ) -> None:
        self._cancel = cancel
        self._speak = speak

    def handle(self, event: KeyEvent) -> KeyEventDecision:
        if event.pressed:
            self._cancel()
            self._speak(SpeechSequence(items=(f"VK {event.vk}",)))
        return KeyEventDecision.SUPPRESS
```

- [ ] **Step 4: Run input-behavior tests**

Run:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/unit/test_nvda_remote_use_cases.py \
  tests/unit/test_key_echo_use_cases.py -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  src/apps/nvda_remote/use_cases/input_forwarding.py \
  src/apps/key_echo/use_cases/echo_input.py \
  tests/unit/test_nvda_remote_use_cases.py \
  tests/unit/test_key_echo_use_cases.py
git commit -m "feat: add app input behavior use cases"
```

### Task 6: Introduce facades and preserve service compatibility

**Files:**
- Create: `src/apps/nvda_remote/facade.py`
- Create: `src/apps/key_echo/facade.py`
- Modify: `src/apps/nvda_remote/service.py`
- Modify: `src/apps/key_echo/service.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`
- Modify: `tests/unit/test_key_echo_app_service.py`

- [ ] **Step 1: Implement `NvdaRemoteAppFacade`**

Write `src/apps/nvda_remote/facade.py` with these core pieces:

```python
from collections.abc import Callable
from typing import Any

from adapters.inputs.base import HotkeyCapture, InputCapture, KeyEventDecision
from application.keyboard import KeyEventHandler
from application.output_service import SpeechOutputService
from application.services import ClipboardService
from application.state import ConnectionState, ControlState, RuntimeState
from interop.protocol.connection_info import ConnectionInfo
from interop.protocol.messages import RemoteMessageType
from interop.protocol.routing.message_router import MessageRouter
from interop.protocol.session.remote_session import RemoteSession
from interop.protocol.transport.base import Transport

from apps.nvda_remote.use_cases.control_mode import NvdaRemoteControlModeUseCase
from apps.nvda_remote.use_cases.input_forwarding import NvdaRemoteInputForwardingUseCase
from apps.nvda_remote.use_cases.speech_settings import NvdaRemoteSpeechSettingsUseCase
from apps.nvda_remote.use_cases.state_transition_hotkeys import (
    NvdaRemoteHotkeyAction,
    NvdaRemoteStateTransitionHotkeyUseCase,
)


class NvdaRemoteAppFacade(KeyEventHandler):
    def __init__(...):
        ...

    def bind(self) -> None:
        self.input_capture.set_listener(self.handle_key_event)
        self.hotkey_capture.set_handler(self._handle_hotkey_toggle)
        self.transport.set_message_handler(self._handle_transport_message)

    def handle_key_event(self, event):
        action = self._state_transition_hotkeys.match(event)
        if action == NvdaRemoteHotkeyAction.TOGGLE_CONTROL:
            self._toggle_control_from_hotkey()
            return KeyEventDecision.SUPPRESS
        return self._input_forwarding.handle(event)
```

Keep these public methods compatible with the current service:

- `connect`
- `disconnect`
- `start_control`
- `stop_control`
- `push_clipboard`
- `is_clipboard_available`
- `set_status_listener`
- `get_speech_backend_options`
- `get_selected_speech_backend`
- `set_speech_backend`
- `get_available_voices`
- `get_selected_voice`
- `set_selected_voice`
- `get_rate`
- `set_rate`
- `get_pitch`
- `set_pitch`
- `get_volume`
- `set_volume`
- `shutdown`

- [ ] **Step 2: Implement `KeyEchoAppFacade`**

Write `src/apps/key_echo/facade.py` with these core pieces:

```python
from adapters.inputs.base import KeyEventDecision
from application.keyboard import KeyEventHandler, KeyboardInputService
from application.output_capabilities import OutputCapabilities

from apps.key_echo.use_cases.echo_control import KeyEchoControlUseCase
from apps.key_echo.use_cases.echo_input import KeyEchoInputUseCase
from apps.key_echo.use_cases.speech_settings import KeyEchoSpeechSettingsUseCase
from apps.key_echo.use_cases.state_transition_hotkeys import (
    KeyEchoHotkeyAction,
    KeyEchoStateTransitionHotkeyUseCase,
)


class KeyEchoAppFacade(KeyEventHandler):
    def __init__(self, *, outputs: OutputCapabilities) -> None:
        ...

    def handle_key_event(self, event):
        action = self._state_transition_hotkeys.match(event)
        if action == KeyEchoHotkeyAction.START_ECHO:
            self.start_echo()
            return KeyEventDecision.SUPPRESS
        if action == KeyEchoHotkeyAction.STOP_ECHO:
            self.stop_echo()
            return KeyEventDecision.SUPPRESS
        return self._echo_input.handle(event)
```

Keep these public methods compatible:

- `attach_input_service`
- `set_status_listener`
- `start_echo`
- `stop_echo`
- `is_echo_running`
- speech settings getters/setters
- `shutdown`

- [ ] **Step 3: Preserve import compatibility in `service.py`**

Replace `src/apps/nvda_remote/service.py` with:

```python
from apps.nvda_remote.facade import NvdaRemoteAppFacade as NvdaRemoteAppService
```

Replace `src/apps/key_echo/service.py` with:

```python
from apps.key_echo.facade import KeyEchoAppFacade as KeyEchoAppService
```

- [ ] **Step 4: Run app service tests**

Run:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_key_echo_app_service.py -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add \
  src/apps/nvda_remote/facade.py \
  src/apps/key_echo/facade.py \
  src/apps/nvda_remote/service.py \
  src/apps/key_echo/service.py \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_key_echo_app_service.py
git commit -m "refactor: introduce app facades and use cases"
```

### Task 7: Rewire runtime composition and verify wx integration

**Files:**
- Modify: `src/apps/nvda_remote/main.py`
- Modify: `src/apps/key_echo/main.py`
- Modify: `tests/unit/test_app_wx.py`

- [ ] **Step 1: Update main modules to instantiate the facades explicitly**

Change `src/apps/nvda_remote/main.py` import:

```python
from apps.nvda_remote.facade import NvdaRemoteAppFacade
```

and construct:

```python
app_service = NvdaRemoteAppFacade(
    transport=transport,
    input_capture=input_capture,
    hotkey_capture=hotkey_capture,
    clipboard=clipboard,
    speech=QueuedOutputService(speech=speech_service, scheduler=output_scheduler),
    on_speech_backend_changed=config_store.save_backend_id,
    main_thread_dispatch=getattr(NvdaRemoteApp, "dispatch", None),
)
```

Change `src/apps/key_echo/main.py` import:

```python
from apps.key_echo.facade import KeyEchoAppFacade
```

and construct:

```python
app_service = KeyEchoAppFacade(
    outputs=OutputCapabilities(speech=output_service),
)
```

- [ ] **Step 2: Update wx/runtime composition tests**

Adjust `tests/unit/test_app_wx.py` and any `main` composition assertions so they no longer depend on implementation details of the old monolithic service class. Keep assertions focused on:

- app object receives a controller
- controller still exposes the expected UI methods
- `nvda_remote` runtime still wires transport/input/hotkey/clipboard/speech correctly
- `key_echo` runtime still wires capture/output/input service correctly

- [ ] **Step 3: Run composition tests**

Run:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/unit/test_app_wx.py \
  tests/unit/test_key_echo_app_service.py \
  tests/unit/test_nvda_remote_app_service.py -v
```

Expected:

- PASS

- [ ] **Step 4: Commit**

```bash
git add \
  src/apps/nvda_remote/main.py \
  src/apps/key_echo/main.py \
  tests/unit/test_app_wx.py
git commit -m "refactor: rewire runtimes to app facades"
```

### Task 8: Full verification

**Files:**
- Verify only

- [ ] **Step 1: Run full test suite**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/unit tests/integration -v
```

Expected:

- PASS

- [ ] **Step 2: Verify service compatibility imports still exist**

Run:

```bash
PYTHONPATH=src python3 - <<'PY'
from apps.nvda_remote.service import NvdaRemoteAppService
from apps.key_echo.service import KeyEchoAppService

print(NvdaRemoteAppService.__name__)
print(KeyEchoAppService.__name__)
PY
```

Expected:

```text
NvdaRemoteAppFacade
KeyEchoAppFacade
```

- [ ] **Step 3: Verify `Enter`/`Escape`/`F11` behavior is covered**

Run:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/unit/test_nvda_remote_app_service.py::test_nvda_remote_service_f11_toggles_control_on_keydown_only \
  tests/unit/test_key_echo_app_service.py::test_key_echo_app_service_starts_echo_on_enter_keydown \
  tests/unit/test_key_echo_app_service.py::test_key_echo_app_service_stops_echo_on_escape_keydown -v
```

Expected:

- PASS

