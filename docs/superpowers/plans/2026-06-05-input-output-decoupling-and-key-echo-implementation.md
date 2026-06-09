# Input/Output Decoupling and Key Echo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `ClientController` with app-specific services, introduce a shared `SpeechService` and `KeyboardInputService`, and add a standalone `key_echo` app that speaks keydown `vk` codes while preserving existing `nvda_remote` behavior.

**Architecture:** Extract shared keyboard and speech coordination into `application` services, move NVDA Remote-specific orchestration into `apps/nvda_remote`, and add a parallel `apps/key_echo` service and entrypoint. Keep adapters reusable and protocol-specific code isolated inside the NVDA Remote app module.

**Tech Stack:** Python 3.12, pytest, wxPython app entrypoints, Windows keyboard hook adapters, pyttsx3 and NVDA controller speech adapters

---

## File Structure

### Create

- `src/application/keyboard.py`
  - Shared `KeyEventHandler` protocol and `KeyboardInputService`.
- `src/application/speech_service.py`
  - Shared `SpeechService` that wraps backend selection and speech parameter control.
- `src/application/output_capabilities.py`
  - Shared `OutputCapabilities` dataclass holding `speech`, `tone`, and `braille`.
- `src/apps/__init__.py`
  - Package marker for app modules.
- `src/apps/nvda_remote/__init__.py`
  - Package marker for NVDA Remote app module.
- `src/apps/nvda_remote/service.py`
  - `NvdaRemoteAppService` replacing `ClientController`.
- `src/apps/nvda_remote/main.py`
  - NVDA Remote composition root to replace `src/ui/main.py` as the runtime entry.
- `src/apps/key_echo/__init__.py`
  - Package marker for Key Echo app module.
- `src/apps/key_echo/service.py`
  - `KeyEchoAppService`.
- `src/apps/key_echo/main.py`
  - Standalone Key Echo composition root.
- `tests/unit/test_keyboard_input_service.py`
  - Unit tests for shared keyboard event forwarding.
- `tests/unit/test_speech_service.py`
  - Unit tests for backend switching and speech controls.
- `tests/unit/test_key_echo_app_service.py`
  - Unit tests for key echo rules.
- `tests/unit/test_nvda_remote_app_service.py`
  - Unit tests for extracted NVDA Remote rules.

### Modify

- `src/ui/main.py`
  - Reduce to a thin compatibility wrapper importing and calling `apps.nvda_remote.main.main`, or remove if packaging allows direct switch.
- `src/ui/main_frame.py`
  - Replace controller-specific dependencies with `NvdaRemoteAppService` speech/status APIs.
- `src/ui/app.py`
  - Construct the UI around the new app service type.
- `src/application/speech_backends.py`
  - Reuse internals from `SpeechBackendManager` inside `SpeechService`, or trim down to backend option data structures only.
- `src/application/services.py`
  - Remove or simplify `OutputManager` so no remote protocol behavior remains there.
- `src/adapters/inputs/base.py`
  - Keep capture protocols aligned with `KeyboardInputService`.
- `tests/unit/test_app_wx.py`
  - Point GUI-facing tests at the new app service APIs.
- `tests/unit/test_application_controller.py`
  - Replace or retire controller tests as behavior moves into `NvdaRemoteAppService`.
- `tests/unit/test_speech_backends.py`
  - Update tests to target `SpeechService` instead of direct backend manager wiring.
- `tests/integration/test_relay_session.py`
  - Keep remote speech path coverage passing with new service wiring.

### Delete

- `src/application/controller.py`
  - Retire once all callers use `NvdaRemoteAppService`.

## Task 1: Introduce Shared Keyboard Handling

**Files:**
- Create: `src/application/keyboard.py`
- Test: `tests/unit/test_keyboard_input_service.py`
- Modify: `src/adapters/inputs/base.py`

- [ ] **Step 1: Write the failing test**

```python
from adapters.inputs.base import KeyEventDecision
from application.keyboard import KeyboardInputService
from remote_core.models.keys import KeyEvent


class FakeCapture:
    def __init__(self):
        self.listener = None
        self.running = False

    def set_listener(self, listener):
        self.listener = listener

    def start(self):
        self.running = True

    def stop(self):
        self.running = False


class FakeHandler:
    def __init__(self):
        self.events = []

    def handle_key_event(self, event):
        self.events.append(event)
        return KeyEventDecision.PASS_THROUGH


def test_keyboard_input_service_forwards_events_to_handler():
    capture = FakeCapture()
    handler = FakeHandler()

    service = KeyboardInputService(capture, handler)
    service.bind()

    event = KeyEvent(vk=65, scan=30, extended=False, pressed=True)
    decision = capture.listener(event)

    assert decision == KeyEventDecision.PASS_THROUGH
    assert handler.events == [event]


def test_keyboard_input_service_controls_capture_lifecycle():
    capture = FakeCapture()
    handler = FakeHandler()

    service = KeyboardInputService(capture, handler)

    service.start()
    assert capture.running is True

    service.stop()
    assert capture.running is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_keyboard_input_service.py -v`
Expected: FAIL with `ModuleNotFoundError` for `application.keyboard` or missing `KeyboardInputService`

- [ ] **Step 3: Write minimal implementation**

```python
from typing import Protocol

from adapters.inputs.base import InputCapture, KeyEventDecision
from remote_core.models.keys import KeyEvent


class KeyEventHandler(Protocol):
    def handle_key_event(self, event: KeyEvent) -> KeyEventDecision: ...


class KeyboardInputService:
    def __init__(self, capture: InputCapture, handler: KeyEventHandler) -> None:
        self._capture = capture
        self._handler = handler

    def bind(self) -> None:
        self._capture.set_listener(self._handler.handle_key_event)

    def set_handler(self, handler: KeyEventHandler) -> None:
        self._handler = handler
        self.bind()

    def start(self) -> None:
        self.bind()
        self._capture.start()

    def stop(self) -> None:
        self._capture.stop()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_keyboard_input_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_keyboard_input_service.py src/application/keyboard.py src/adapters/inputs/base.py
git commit -m "feat: add shared keyboard input service"
```

## Task 2: Introduce Shared SpeechService and OutputCapabilities

**Files:**
- Create: `src/application/speech_service.py`
- Create: `src/application/output_capabilities.py`
- Test: `tests/unit/test_speech_service.py`
- Modify: `src/application/speech_backends.py`
- Modify: `src/adapters/outputs/interfaces.py`

- [ ] **Step 1: Write the failing test**

```python
from application.speech_service import SpeechService
from application.speech_backends import SpeechBackendOption
from remote_core.models.speech_sequence import SpeechSequence


class FakeSpeechOutput:
    def __init__(self, name):
        self.name = name
        self.spoken = []
        self.cancelled = 0
        self.paused = []
        self.voice = None
        self.rate = 100
        self.pitch = 100
        self.volume = 100

    def speak(self, sequence):
        self.spoken.append(sequence)

    def cancel(self):
        self.cancelled += 1

    def pause(self, is_paused):
        self.paused.append(is_paused)

    def list_voices(self):
        return (("voice-1", "Voice 1"),)

    def get_voice(self):
        return self.voice

    def set_voice(self, voice_id):
        self.voice = voice_id

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


def test_speech_service_switches_backends_and_routes_calls():
    created = []

    def build(name):
        def factory():
            output = FakeSpeechOutput(name)
            created.append(output)
            return output
        return factory

    service = SpeechService(
        backend_options=(
            SpeechBackendOption("nvda_controller", "NVDA Controller", build("nvda")),
            SpeechBackendOption("pyttsx3", "pyttsx3", build("pyttsx3")),
        ),
        selected_backend_id="nvda_controller",
    )

    sequence = SpeechSequence(items=("VK 65",))
    service.speak(sequence)
    service.set_backend("pyttsx3")
    service.set_voice("voice-1")

    assert created[0].spoken == [sequence]
    assert service.get_selected_backend() == "pyttsx3"
    assert service.get_voice() == "voice-1"


def test_speech_service_rejects_unknown_backend():
    service = SpeechService(
        backend_options=(SpeechBackendOption("nvda_controller", "NVDA Controller", lambda: FakeSpeechOutput("nvda")),),
        selected_backend_id="nvda_controller",
    )

    try:
        service.set_backend("missing")
    except ValueError as error:
        assert "Unknown speech backend" in str(error)
    else:
        raise AssertionError("Expected ValueError")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_speech_service.py -v`
Expected: FAIL with `ModuleNotFoundError` for `application.speech_service`

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass

from adapters.outputs.interfaces import BrailleOutput, SpeechOutput, ToneOutput
from application.speech_backends import SpeechBackendOption
from remote_core.models.speech_sequence import SpeechSequence


@dataclass
class OutputCapabilities:
    speech: "SpeechService"
    tone: ToneOutput | None = None
    braille: BrailleOutput | None = None


class SpeechService:
    def __init__(
        self,
        *,
        backend_options: tuple[SpeechBackendOption, ...],
        selected_backend_id: str,
    ) -> None:
        self._options = backend_options
        self._options_by_id = {option.backend_id: option for option in backend_options}
        if selected_backend_id not in self._options_by_id:
            raise ValueError(f"Unknown speech backend: {selected_backend_id}")
        self._selected_backend_id = selected_backend_id
        self._current_output = self._options_by_id[selected_backend_id].factory()

    def speak(self, sequence: SpeechSequence) -> None:
        self._current_output.speak(sequence)

    def cancel(self) -> None:
        self._current_output.cancel()

    def pause(self, is_paused: bool) -> None:
        self._current_output.pause(is_paused)

    def get_backend_options(self) -> tuple[tuple[str, str], ...]:
        return tuple((option.backend_id, option.label) for option in self._options)

    def get_selected_backend(self) -> str:
        return self._selected_backend_id

    def set_backend(self, backend_id: str) -> None:
        if backend_id not in self._options_by_id:
            raise ValueError(f"Unknown speech backend: {backend_id}")
        if backend_id == self._selected_backend_id:
            return
        self._current_output.cancel()
        self._current_output = self._options_by_id[backend_id].factory()
        self._selected_backend_id = backend_id

    def list_voices(self):
        return self._current_output.list_voices()

    def get_voice(self):
        return self._current_output.get_voice()

    def set_voice(self, voice_id: str) -> None:
        self._current_output.set_voice(voice_id)

    def get_rate(self):
        return self._current_output.get_rate()

    def set_rate(self, value: int) -> None:
        self._current_output.set_rate(value)

    def get_pitch(self):
        return self._current_output.get_pitch()

    def set_pitch(self, value: int) -> None:
        self._current_output.set_pitch(value)

    def get_volume(self):
        return self._current_output.get_volume()

    def set_volume(self, value: int) -> None:
        self._current_output.set_volume(value)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_speech_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_speech_service.py src/application/speech_service.py src/application/output_capabilities.py src/application/speech_backends.py src/adapters/outputs/interfaces.py
git commit -m "feat: add shared speech service"
```

## Task 3: Add Key Echo App Service and Standalone Entrypoint

**Files:**
- Create: `src/apps/__init__.py`
- Create: `src/apps/key_echo/__init__.py`
- Create: `src/apps/key_echo/service.py`
- Create: `src/apps/key_echo/main.py`
- Test: `tests/unit/test_key_echo_app_service.py`

- [ ] **Step 1: Write the failing test**

```python
from adapters.inputs.base import KeyEventDecision
from apps.key_echo.service import KeyEchoAppService
from application.output_capabilities import OutputCapabilities
from remote_core.models.keys import KeyEvent


class FakeSpeechService:
    def __init__(self):
        self.spoken = []

    def speak(self, sequence):
        self.spoken.append(sequence)


def test_key_echo_speaks_vk_only_on_keydown():
    speech = FakeSpeechService()
    service = KeyEchoAppService(OutputCapabilities(speech=speech))

    keydown = KeyEvent(vk=65, scan=30, extended=False, pressed=True)
    keyup = KeyEvent(vk=65, scan=30, extended=False, pressed=False)

    assert service.handle_key_event(keydown) == KeyEventDecision.PASS_THROUGH
    assert service.handle_key_event(keyup) == KeyEventDecision.PASS_THROUGH

    assert len(speech.spoken) == 1
    assert speech.spoken[0].items == ("VK 65",)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_key_echo_app_service.py -v`
Expected: FAIL with `ModuleNotFoundError` for `apps.key_echo.service`

- [ ] **Step 3: Write minimal implementation**

```python
from adapters.inputs.base import KeyEventDecision
from application.keyboard import KeyEventHandler
from application.output_capabilities import OutputCapabilities
from remote_core.models.keys import KeyEvent
from remote_core.models.speech_sequence import SpeechSequence


class KeyEchoAppService(KeyEventHandler):
    def __init__(self, outputs: OutputCapabilities) -> None:
        self._outputs = outputs

    def handle_key_event(self, event: KeyEvent) -> KeyEventDecision:
        if event.pressed:
            self._outputs.speech.speak(SpeechSequence(items=(f"VK {event.vk}",)))
        return KeyEventDecision.PASS_THROUGH
```

And create the entrypoint:

```python
from adapters.windows.keyboard_hook import WindowsKeyboardCapture
from adapters.outputs.drivers.pyttsx3 import Pyttsx3SpeechOutput
from application.keyboard import KeyboardInputService
from application.output_capabilities import OutputCapabilities
from application.speech_backends import SpeechBackendOption
from application.speech_service import SpeechService
from apps.key_echo.service import KeyEchoAppService


def main() -> int:
    speech = SpeechService(
        backend_options=(
            SpeechBackendOption(
                backend_id="pyttsx3",
                label="pyttsx3",
                factory=Pyttsx3SpeechOutput.load_default,
            ),
        ),
        selected_backend_id="pyttsx3",
    )
    app_service = KeyEchoAppService(OutputCapabilities(speech=speech))
    keyboard = KeyboardInputService(WindowsKeyboardCapture(), app_service)
    keyboard.start()
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_key_echo_app_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_key_echo_app_service.py src/apps/__init__.py src/apps/key_echo/__init__.py src/apps/key_echo/service.py src/apps/key_echo/main.py
git commit -m "feat: add key echo app service"
```

## Task 4: Extract NvdaRemoteAppService from ClientController

**Files:**
- Create: `src/apps/nvda_remote/__init__.py`
- Create: `src/apps/nvda_remote/service.py`
- Test: `tests/unit/test_nvda_remote_app_service.py`
- Modify: `src/remote_core/routing/message_router.py`
- Modify: `src/application/state.py`
- Delete: `src/application/controller.py`

- [ ] **Step 1: Write the failing test**

```python
from adapters.inputs.base import KeyEventDecision
from apps.nvda_remote.service import NvdaRemoteAppService
from remote_core.models.keys import KeyEvent
from remote_core.protocol import RemoteMessageType


class FakeTransport:
    def __init__(self):
        self.sent = []

    def send(self, message_type, **payload):
        self.sent.append((message_type, payload))

    def set_message_handler(self, handler):
        self.handler = handler


class FakeCapture:
    def __init__(self):
        self.running = False

    def set_listener(self, listener):
        self.listener = listener

    def start(self):
        self.running = True

    def stop(self):
        self.running = False


class FakeHotkey:
    def set_handler(self, handler):
        self.handler = handler

    def start(self):
        pass

    def stop(self):
        pass


class FakeClipboard:
    def set_text(self, text):
        self.text = text

    def get_text(self):
        return "clip"


class FakeSpeechService:
    def speak(self, sequence):
        self.sequence = sequence

    def cancel(self):
        self.cancelled = True

    def pause(self, is_paused):
        self.paused = is_paused


def test_nvda_remote_service_forwards_keys_when_controlling():
    service = NvdaRemoteAppService(
        transport=FakeTransport(),
        input_capture=FakeCapture(),
        hotkey_capture=FakeHotkey(),
        clipboard=FakeClipboard(),
        speech=FakeSpeechService(),
        main_thread_dispatch=lambda callback: callback(),
    )

    service.state.connection_state = service.state.connection_state.CONNECTED
    service.start_control()
    event = KeyEvent(vk=65, scan=30, extended=False, pressed=True)

    decision = service.handle_key_event(event)

    assert decision == KeyEventDecision.FORWARD_AND_SUPPRESS
    assert service.transport.sent == [
        (RemoteMessageType.KEY, event.to_remote_payload())
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_nvda_remote_app_service.py -v`
Expected: FAIL with `ModuleNotFoundError` for `apps.nvda_remote.service`

- [ ] **Step 3: Write minimal implementation**

```python
from typing import Any

from adapters.inputs.base import HotkeyCapture, InputCapture, KeyEventDecision
from application.keyboard import KeyEventHandler
from application.state import ConnectionState, ControlState, RuntimeState
from remote_core.connection_info import ConnectionInfo
from remote_core.models.keys import KeyEvent
from remote_core.protocol import RemoteMessageType
from remote_core.routing.message_router import MessageRouter
from remote_core.session.remote_session import RemoteSession
from remote_core.transport.base import Transport


class NvdaRemoteAppService(KeyEventHandler):
    _LOCAL_STOP_VK = 0x7A

    def __init__(
        self,
        *,
        transport: Transport,
        input_capture: InputCapture,
        hotkey_capture: HotkeyCapture,
        clipboard,
        speech,
        main_thread_dispatch=None,
    ) -> None:
        self.transport = transport
        self.input_capture = input_capture
        self.hotkey_capture = hotkey_capture
        self.clipboard = clipboard
        self.speech = speech
        self.state = RuntimeState()
        self._main_thread_dispatch = main_thread_dispatch or (lambda callback: callback())
        self._suppressed_keyups: set[int] = set()
        self.session = RemoteSession(transport=transport, on_status=self._on_status)
        self.router = MessageRouter(
            on_speech=self.speech.speak,
            on_cancel=self.speech.cancel,
            on_pause=self.speech.pause,
            on_clipboard=self.clipboard.set_text,
            on_status=self._on_status,
        )
        set_message_handler = getattr(self.transport, "set_message_handler", None)
        if set_message_handler is not None:
            set_message_handler(self._handle_transport_message)

    def handle_key_event(self, event: KeyEvent) -> KeyEventDecision:
        if not event.pressed and event.vk in self._suppressed_keyups:
            self._suppressed_keyups.discard(event.vk)
            return KeyEventDecision.LOCAL_ONLY_SUPPRESS
        if self.state.connection_state == ConnectionState.IDLE:
            return KeyEventDecision.PASS_THROUGH
        if event.vk == self._LOCAL_STOP_VK:
            if event.pressed:
                self._suppressed_keyups.add(event.vk)
                self.stop_control()
            return KeyEventDecision.LOCAL_ONLY_SUPPRESS
        if self.state.control_state != ControlState.CONTROLLING:
            return KeyEventDecision.PASS_THROUGH
        self.transport.send(RemoteMessageType.KEY, **event.to_remote_payload())
        return KeyEventDecision.FORWARD_AND_SUPPRESS

    def start_control(self) -> None:
        self.state.control_state = ControlState.CONTROLLING

    def stop_control(self) -> None:
        self.state.control_state = ControlState.SUSPENDED

    def _handle_transport_message(self, payload: dict[str, Any]) -> None:
        if self.session.handle_message(payload):
            return
        self.router.handle_message(payload)

    def _on_status(self, status: dict[str, Any]) -> None:
        if status.get("kind") == "connection" and status.get("state") == ConnectionState.CONNECTED.value:
            self.state.connection_state = ConnectionState.CONNECTED
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_nvda_remote_app_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_nvda_remote_app_service.py src/apps/nvda_remote/__init__.py src/apps/nvda_remote/service.py src/application/state.py src/remote_core/routing/message_router.py
git commit -m "refactor: extract nvda remote app service"
```

## Task 5: Rewire UI and Runtime Entrypoints to New Services

**Files:**
- Create: `src/apps/nvda_remote/main.py`
- Modify: `src/ui/main.py`
- Modify: `src/ui/app.py`
- Modify: `src/ui/main_frame.py`
- Modify: `tests/unit/test_app_wx.py`
- Modify: `tests/integration/test_relay_session.py`

- [ ] **Step 1: Write the failing test**

```python
import ui.main as main_module


def test_ui_main_delegates_to_nvda_remote_app_main(monkeypatch):
    called = {}

    def fake_main():
        called["ran"] = True
        return 0

    monkeypatch.setattr("apps.nvda_remote.main.main", fake_main)

    assert main_module.main() == 0
    assert called["ran"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_app_wx.py -k delegates_to_nvda_remote_app_main -v`
Expected: FAIL because `ui.main.main` still owns the old composition root

- [ ] **Step 3: Write minimal implementation**

```python
# src/apps/nvda_remote/main.py
from adapters.windows.clipboard import WindowsClipboardService
from adapters.windows.hotkey import WindowsHotkeyCapture
from adapters.windows.keyboard_hook import WindowsKeyboardCapture
from adapters.windows.nvda_controller import NvdaControllerSpeechOutput
from adapters.outputs.drivers.pyttsx3 import Pyttsx3SpeechOutput
from application.config import SpeechBackendConfigStore
from application.keyboard import KeyboardInputService
from application.speech_backends import SpeechBackendOption
from application.speech_service import SpeechService
from apps.nvda_remote.service import NvdaRemoteAppService
from remote_core.serializer import JSONSerializer
from remote_core.transport.relay import RelayTransport
from ui.app import NvdaRemoteApp


def main() -> int:
    config_store = SpeechBackendConfigStore()
    speech = SpeechService(
        backend_options=(
            SpeechBackendOption("nvda_controller", "NVDA Controller", NvdaControllerSpeechOutput.load_default),
            SpeechBackendOption("pyttsx3", "pyttsx3", Pyttsx3SpeechOutput.load_default),
        ),
        selected_backend_id=config_store.load_backend_id(default_backend_id="nvda_controller"),
    )
    service = NvdaRemoteAppService(
        transport=RelayTransport(JSONSerializer()),
        input_capture=WindowsKeyboardCapture(),
        hotkey_capture=WindowsHotkeyCapture(),
        clipboard=WindowsClipboardService(),
        speech=speech,
        main_thread_dispatch=getattr(NvdaRemoteApp, "dispatch", None),
    )
    KeyboardInputService(service.input_capture, service).bind()
    app = NvdaRemoteApp(controller=service)
    return app.MainLoop()


# src/ui/main.py
from apps.nvda_remote.main import main
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_app_wx.py -k delegates_to_nvda_remote_app_main -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_app_wx.py tests/integration/test_relay_session.py src/apps/nvda_remote/main.py src/ui/main.py src/ui/app.py src/ui/main_frame.py
git commit -m "refactor: rewire ui to app services"
```

## Task 6: Retire Controller and Update Legacy Tests

**Files:**
- Delete: `src/application/controller.py`
- Modify: `tests/unit/test_application_controller.py`
- Modify: `tests/unit/test_output_manager.py`
- Modify: `tests/unit/test_speech_backends.py`
- Modify: `tests/unit/test_windows_adapters.py`
- Modify: `README.md`

- [ ] **Step 1: Write the failing test**

```python
def test_legacy_controller_module_is_no_longer_imported():
    try:
        import src.application.controller  # noqa: F401
    except ModuleNotFoundError:
        assert True
    else:
        raise AssertionError("controller module should be retired")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_application_controller.py -v`
Expected: FAIL because legacy controller tests still exist and import `application.controller`

- [ ] **Step 3: Write minimal implementation**

```python
# Replace controller-centric tests with imports and behavior checks for:
# - tests/unit/test_nvda_remote_app_service.py
# - tests/unit/test_keyboard_input_service.py
# - tests/unit/test_speech_service.py
# - tests/unit/test_key_echo_app_service.py
#
# Delete src/application/controller.py after callers and tests are migrated.
```

Update README runtime examples:

```markdown
## Entrypoints

- NVDA Remote GUI: `python -m apps.nvda_remote.main`
- Key echo demo: `python -m apps.key_echo.main`
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_keyboard_input_service.py tests/unit/test_speech_service.py tests/unit/test_key_echo_app_service.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_app_wx.py tests/integration/test_relay_session.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md tests/unit/test_application_controller.py tests/unit/test_output_manager.py tests/unit/test_speech_backends.py tests/unit/test_windows_adapters.py tests/unit/test_keyboard_input_service.py tests/unit/test_speech_service.py tests/unit/test_key_echo_app_service.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_app_wx.py tests/integration/test_relay_session.py
git rm src/application/controller.py
git commit -m "refactor: retire legacy controller"
```

## Task 7: Final Verification

**Files:**
- Modify: `docs/superpowers/specs/2026-06-05-input-output-decoupling-and-key-echo-design_zh-TW.md`
- Modify: `docs/superpowers/plans/2026-06-05-input-output-decoupling-and-key-echo-implementation.md`

- [ ] **Step 1: Run targeted unit and integration suites**

Run:

```bash
pytest tests/unit/test_keyboard_input_service.py \
  tests/unit/test_speech_service.py \
  tests/unit/test_key_echo_app_service.py \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_app_wx.py \
  tests/unit/test_speech_backends.py \
  tests/unit/test_windows_adapters.py \
  tests/integration/test_relay_session.py -v
```

Expected: PASS

- [ ] **Step 2: Smoke-test the new entrypoints**

Run:

```bash
python -m apps.key_echo.main
python -m apps.nvda_remote.main
```

Expected:
- `apps.key_echo.main` starts keyboard capture without importing remote transport code
- `apps.nvda_remote.main` starts the GUI composition path

- [ ] **Step 3: Review spec coverage and update notes**

Check that the implementation matches:

- `ClientController` retired
- `SpeechService` introduced
- `key_echo` standalone entrypoint added
- tone / braille capability fields exist
- remote transport remains inside `apps/nvda_remote`

If any behavior differs, update:

```markdown
- docs/superpowers/specs/2026-06-05-input-output-decoupling-and-key-echo-design_zh-TW.md
- docs/superpowers/plans/2026-06-05-input-output-decoupling-and-key-echo-implementation.md
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-06-05-input-output-decoupling-and-key-echo-design_zh-TW.md docs/superpowers/plans/2026-06-05-input-output-decoupling-and-key-echo-implementation.md
git commit -m "docs: finalize decoupling implementation notes"
```
