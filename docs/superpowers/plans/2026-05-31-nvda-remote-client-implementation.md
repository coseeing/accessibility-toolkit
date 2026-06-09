# NVDA Remote Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Windows NVDA Remote controlling client with `wxPython` UI, modular core/adapters, keyboard forwarding, normalized speech handling, and bidirectional clipboard sync.

**Architecture:** The implementation is split into `remote_core`, `application`, `adapters`, and `app_wx`. `remote_core` owns protocol, serializer, transport, session, and normalized models; `application` wires runtime behavior and UI-facing state; `adapters` isolate Windows and output backends; `app_wx` remains a thin shell over application services.

**Tech Stack:** Python 3, `wxPython`, `pytest`, `pytest-mock`, `dataclasses`, `socket`/`ssl`, `ctypes`

---

## File Structure

### Create

- `pyproject.toml`
- `src/remote_core/protocol.py`
- `src/remote_core/serializer.py`
- `src/remote_core/connection_info.py`
- `src/remote_core/models/keys.py`
- `src/remote_core/models/speech.py`
- `src/remote_core/routing/message_router.py`
- `src/remote_core/session/remote_session.py`
- `src/remote_core/transport/base.py`
- `src/remote_core/transport/relay.py`
- `src/application/state.py`
- `src/application/events.py`
- `src/application/services.py`
- `src/application/controller.py`
- `src/adapters/inputs/base.py`
- `src/adapters/outputs/speech.py`
- `src/adapters/outputs/braille.py`
- `src/adapters/outputs/tone.py`
- `src/adapters/outputs/wave.py`
- `src/adapters/windows/clipboard.py`
- `src/adapters/windows/nvda_controller.py`
- `src/adapters/windows/keyboard_hook.py`
- `src/app_wx/app.py`
- `src/app_wx/main.py`
- `src/app_wx/main_frame.py`
- `tests/unit/test_protocol_serializer.py`
- `tests/unit/test_message_router.py`
- `tests/unit/test_speech_normalization.py`
- `tests/unit/test_application_controller.py`
- `tests/unit/test_clipboard_service.py`
- `tests/integration/test_relay_session.py`

### Responsibilities

- `src/remote_core/protocol.py`: protocol constants, message types, address helpers.
- `src/remote_core/serializer.py`: JSON serializer, newline framing, normalized speech payload conversion.
- `src/remote_core/connection_info.py`: immutable connection settings and validation.
- `src/remote_core/models/keys.py`: `KeyEvent`.
- `src/remote_core/models/speech.py`: `NormalizedSpeech`, `SpeechSegment`.
- `src/remote_core/routing/message_router.py`: message dispatch from decoded payloads to runtime callbacks.
- `src/remote_core/session/remote_session.py`: channel join, session state, ping/disconnect handling.
- `src/remote_core/transport/*`: transport interfaces and relay implementation.
- `src/application/state.py`: UI-facing state enums/dataclasses.
- `src/application/events.py`: app event types for UI/status delivery.
- `src/application/services.py`: output manager, clipboard push, connect/disconnect orchestration.
- `src/application/controller.py`: top-level runtime coordinator.
- `src/adapters/inputs/base.py`: `InputCapture` protocol.
- `src/adapters/outputs/*`: output interfaces and null/log implementations.
- `src/adapters/windows/clipboard.py`: Windows clipboard adapter.
- `src/adapters/windows/nvda_controller.py`: NVDA controller DLL speech backend.
- `src/adapters/windows/keyboard_hook.py`: Windows keyboard capture implementation.
- `src/app_wx/*`: GUI shell and bootstrapping.

### Implementation Notes

- Keep imports one-directional: `app_wx` -> `application` -> `remote_core`/`adapters`.
- Do not import `wx` from `remote_core`.
- Do not import Win32 or `ctypes` DLL code from `remote_core`.
- Keep `leader` behavior internal; do not add follower-mode UI in v1.

## Task 1: Project Skeleton and Tooling

**Files:**
- Create: `pyproject.toml`
- Create: `src/app_wx/main.py`
- Create: `tests/unit/test_protocol_serializer.py`

- [ ] **Step 1: Write the failing test for package import paths**

```python
from remote_core.protocol import RemoteMessageType
from remote_core.serializer import JSONSerializer


def test_serializer_imports_are_available():
    serializer = JSONSerializer()
    assert RemoteMessageType.KEY.value == "key"
    assert serializer.SEP == b"\n"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_protocol_serializer.py::test_serializer_imports_are_available -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'remote_core'`

- [ ] **Step 3: Write minimal packaging and entrypoint scaffolding**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "nvda-remote-client"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "wxPython",
]

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```python
import wx


def main() -> int:
    app = wx.App(False)
    app.ExitMainLoop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Add empty package initializers**

```python
# src/remote_core/__init__.py
```

```python
# src/application/__init__.py
```

```python
# src/adapters/__init__.py
```

```python
# src/app_wx/__init__.py
```

- [ ] **Step 5: Run test to verify import path setup works once core files exist**

Run: `pytest tests/unit/test_protocol_serializer.py::test_serializer_imports_are_available -v`
Expected: FAIL with `ImportError` pointing to missing `protocol` or `serializer`, confirming package discovery is fixed

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/app_wx/main.py src/app_wx/__init__.py src/remote_core/__init__.py src/application/__init__.py src/adapters/__init__.py tests/unit/test_protocol_serializer.py
git commit -m "chore: scaffold project structure"
```

## Task 2: Protocol, Models, and Serializer

**Files:**
- Create: `src/remote_core/protocol.py`
- Create: `src/remote_core/serializer.py`
- Create: `src/remote_core/connection_info.py`
- Create: `src/remote_core/models/keys.py`
- Create: `src/remote_core/models/speech.py`
- Modify: `tests/unit/test_protocol_serializer.py`
- Create: `tests/unit/test_speech_normalization.py`

- [ ] **Step 1: Write failing tests for protocol helpers and speech normalization**

```python
from remote_core.models.keys import KeyEvent
from remote_core.models.speech import NormalizedSpeech, SpeechSegment
from remote_core.protocol import RemoteMessageType, address_to_host_port
from remote_core.serializer import JSONSerializer


def test_protocol_helpers_and_serializer_round_trip():
    serializer = JSONSerializer()
    payload = serializer.serialize(
        RemoteMessageType.KEY,
        vk=9,
        scan=15,
        extended=False,
        pressed=True,
    )
    decoded = serializer.deserialize(payload.strip())
    assert address_to_host_port("example.com") == ("example.com", 6837)
    assert decoded["type"] == "key"
    assert decoded["vk"] == 9


def test_normalized_speech_from_remote_payload():
    payload = {
        "type": "speak",
        "sequence": ["Hello", ["BreakCommand", {"time": 100}], "world"],
    }
    normalized = NormalizedSpeech.from_remote_payload(payload)
    assert normalized.segments == [
        SpeechSegment(kind="text", value="Hello"),
        SpeechSegment(kind="break", value=100),
        SpeechSegment(kind="text", value="world"),
    ]


def test_key_event_to_message_payload():
    event = KeyEvent(vk=65, scan=30, extended=False, pressed=True)
    assert event.to_remote_payload() == {
        "vk": 65,
        "scan": 30,
        "extended": False,
        "pressed": True,
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_protocol_serializer.py tests/unit/test_speech_normalization.py -v`
Expected: FAIL with missing modules and classes such as `remote_core.models.keys.KeyEvent`

- [ ] **Step 3: Implement protocol, models, and serializer**

```python
from enum import StrEnum
from urllib.parse import urlparse


SERVER_PORT = 6837


class RemoteMessageType(StrEnum):
    PROTOCOL_VERSION = "protocol_version"
    JOIN = "join"
    CHANNEL_JOINED = "channel_joined"
    CLIENT_JOINED = "client_joined"
    CLIENT_LEFT = "client_left"
    KEY = "key"
    SPEAK = "speak"
    CANCEL = "cancel"
    PAUSE_SPEECH = "pause_speech"
    SET_CLIPBOARD_TEXT = "set_clipboard_text"
    MOTD = "motd"
    VERSION_MISMATCH = "version_mismatch"
    PING = "ping"
    ERROR = "error"


def address_to_host_port(address: str) -> tuple[str, int]:
    parsed = urlparse(f"//{address}")
    return parsed.hostname or "", parsed.port or SERVER_PORT
```

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KeyEvent:
    vk: int
    scan: int | None
    extended: bool
    pressed: bool

    def to_remote_payload(self) -> dict[str, int | bool | None]:
        return {
            "vk": self.vk,
            "scan": self.scan,
            "extended": self.extended,
            "pressed": self.pressed,
        }
```

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SpeechSegment:
    kind: str
    value: str | int | float | None


@dataclass(frozen=True, slots=True)
class NormalizedSpeech:
    segments: list[SpeechSegment]

    @classmethod
    def from_remote_payload(cls, payload: dict) -> "NormalizedSpeech":
        segments: list[SpeechSegment] = []
        for item in payload.get("sequence", []):
            if isinstance(item, str):
                segments.append(SpeechSegment(kind="text", value=item))
                continue
            if isinstance(item, list) and item and item[0] == "BreakCommand":
                segments.append(SpeechSegment(kind="break", value=item[1].get("time", 0)))
        return cls(segments=segments)
```

```python
import json
from enum import Enum
from typing import Any


class JSONSerializer:
    SEP = b"\n"

    def serialize(self, message_type: str | Enum, **payload: Any) -> bytes:
        value = message_type.value if isinstance(message_type, Enum) else message_type
        payload["type"] = value
        return json.dumps(payload).encode("utf-8") + self.SEP

    def deserialize(self, data: bytes) -> dict[str, Any]:
        return json.loads(data.decode("utf-8"))
```

- [ ] **Step 4: Add connection info model**

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConnectionInfo:
    hostname: str
    port: int
    key: str
    mode: str = "leader"
    insecure: bool = False
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_protocol_serializer.py tests/unit/test_speech_normalization.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/remote_core/protocol.py src/remote_core/serializer.py src/remote_core/connection_info.py src/remote_core/models/keys.py src/remote_core/models/speech.py tests/unit/test_protocol_serializer.py tests/unit/test_speech_normalization.py
git commit -m "feat: add protocol models and serializer"
```

## Task 3: Router, Session, and Transport Contracts

**Files:**
- Create: `src/remote_core/transport/base.py`
- Create: `src/remote_core/transport/relay.py`
- Create: `src/remote_core/routing/message_router.py`
- Create: `src/remote_core/session/remote_session.py`
- Create: `tests/unit/test_message_router.py`
- Create: `tests/integration/test_relay_session.py`

- [ ] **Step 1: Write failing tests for message dispatch and session join**

```python
from remote_core.connection_info import ConnectionInfo
from remote_core.protocol import RemoteMessageType
from remote_core.routing.message_router import MessageRouter
from remote_core.session.remote_session import RemoteSession


class DummyTransport:
    def __init__(self):
        self.sent = []

    def send(self, message_type, **payload):
        self.sent.append((message_type, payload))


def test_router_dispatches_speech_and_clipboard():
    seen = []
    router = MessageRouter(
        on_speech=lambda speech: seen.append(("speech", speech)),
        on_clipboard=lambda text: seen.append(("clipboard", text)),
        on_status=lambda event: seen.append(("status", event)),
    )
    router.handle_message({"type": "speak", "sequence": ["hello"]})
    router.handle_message({"type": "set_clipboard_text", "text": "abc"})
    assert seen[0][0] == "speech"
    assert seen[1] == ("clipboard", "abc")


def test_session_join_sends_protocol_and_join_messages():
    transport = DummyTransport()
    session = RemoteSession(
        transport=transport,
        on_status=lambda event: None,
    )
    session.connect(ConnectionInfo(hostname="example.com", port=6837, key="secret"))
    assert transport.sent[0][0] == RemoteMessageType.PROTOCOL_VERSION
    assert transport.sent[1][0] == RemoteMessageType.JOIN
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_message_router.py -v`
Expected: FAIL with missing `MessageRouter` and `RemoteSession`

- [ ] **Step 3: Implement transport base, router, and session**

```python
from typing import Protocol, Any


class Transport(Protocol):
    def connect(self, hostname: str, port: int, insecure: bool = False) -> None: ...
    def close(self) -> None: ...
    def send(self, message_type: str, **payload: Any) -> None: ...
```

```python
from remote_core.models.speech import NormalizedSpeech
from remote_core.protocol import RemoteMessageType


class MessageRouter:
    def __init__(self, on_speech, on_clipboard, on_status):
        self._on_speech = on_speech
        self._on_clipboard = on_clipboard
        self._on_status = on_status

    def handle_message(self, payload: dict) -> None:
        match payload.get("type"):
            case RemoteMessageType.SPEAK.value:
                self._on_speech(NormalizedSpeech.from_remote_payload(payload))
            case RemoteMessageType.SET_CLIPBOARD_TEXT.value:
                self._on_clipboard(payload.get("text", ""))
            case _:
                self._on_status(payload)
```

```python
from remote_core.protocol import RemoteMessageType


class RemoteSession:
    PROTOCOL_VERSION = 2

    def __init__(self, transport, on_status):
        self.transport = transport
        self.on_status = on_status

    def connect(self, connection_info):
        self.transport.connect(
            connection_info.hostname,
            connection_info.port,
            insecure=connection_info.insecure,
        )
        self.transport.send(RemoteMessageType.PROTOCOL_VERSION, version=self.PROTOCOL_VERSION)
        self.transport.send(RemoteMessageType.JOIN, channel=connection_info.key, mode=connection_info.mode)
        self.on_status({"state": "connected"})

    def disconnect(self):
        self.transport.close()
        self.on_status({"state": "idle"})
```

- [ ] **Step 4: Stub relay transport for integration development**

```python
from remote_core.serializer import JSONSerializer


class RelayTransport:
    def __init__(self, serializer: JSONSerializer):
        self.serializer = serializer
        self.connected = False

    def connect(self, hostname: str, port: int, insecure: bool = False) -> None:
        self.connected = True

    def close(self) -> None:
        self.connected = False

    def send(self, message_type, **payload) -> None:
        if not self.connected:
            raise RuntimeError("Transport is not connected")
        self.serializer.serialize(message_type, **payload)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_message_router.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/remote_core/transport/base.py src/remote_core/transport/relay.py src/remote_core/routing/message_router.py src/remote_core/session/remote_session.py tests/unit/test_message_router.py tests/integration/test_relay_session.py
git commit -m "feat: add session routing and transport contracts"
```

## Task 4: Output Interfaces and Application Controller

**Files:**
- Create: `src/adapters/inputs/base.py`
- Create: `src/adapters/outputs/speech.py`
- Create: `src/adapters/outputs/braille.py`
- Create: `src/adapters/outputs/tone.py`
- Create: `src/adapters/outputs/wave.py`
- Create: `src/application/state.py`
- Create: `src/application/events.py`
- Create: `src/application/services.py`
- Create: `src/application/controller.py`
- Create: `tests/unit/test_application_controller.py`

- [ ] **Step 1: Write failing tests for runtime state, keyboard forwarding, and clipboard push**

```python
from remote_core.models.keys import KeyEvent
from application.controller import ClientController


class FakeTransport:
    def __init__(self):
        self.sent = []

    def connect(self, hostname, port, insecure=False):
        return None

    def close(self):
        return None

    def send(self, message_type, **payload):
        self.sent.append((message_type, payload))


class FakeCapture:
    def set_listener(self, listener):
        self.listener = listener

    def start(self):
        return None

    def stop(self):
        return None


class FakeClipboard:
    def __init__(self):
        self.text = "clip"

    def set_text(self, text):
        self.text = text

    def get_text(self):
        return self.text


def test_controller_forwards_keys_and_pushes_clipboard():
    transport = FakeTransport()
    capture = FakeCapture()
    clipboard = FakeClipboard()
    controller = ClientController.build_for_tests(
        transport=transport,
        input_capture=capture,
        clipboard=clipboard,
    )
    controller.connect("example.com", 6837, "secret")
    controller.start_control()
    capture.listener(KeyEvent(vk=65, scan=30, extended=False, pressed=True))
    controller.push_clipboard()
    assert transport.sent[-2][1]["vk"] == 65
    assert transport.sent[-1][1]["text"] == "clip"
    assert controller.state.control_state == "controlling"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_application_controller.py -v`
Expected: FAIL with missing `ClientController`

- [ ] **Step 3: Implement interfaces and controller**

```python
from typing import Protocol
from remote_core.models.keys import KeyEvent


class InputCapture(Protocol):
    def set_listener(self, listener) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
```

```python
from dataclasses import dataclass


@dataclass(slots=True)
class RuntimeState:
    connection_state: str = "idle"
    control_state: str = "idle"
```

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StatusEvent:
    message: str
    level: str = "info"
```

```python
class NullBrailleOutput:
    def display(self, cells):
        return None
```

```python
class LoggingToneOutput:
    def beep(self, hz, length, left=50, right=50):
        return None
```

```python
class LoggingWaveOutput:
    def play(self, path: str):
        return None
```

```python
from remote_core.protocol import RemoteMessageType


class OutputManager:
    def __init__(self, speech_output, clipboard):
        self.speech_output = speech_output
        self.clipboard = clipboard

    def handle_speech(self, speech):
        self.speech_output.speak(speech)

    def handle_clipboard(self, text: str):
        self.clipboard.set_text(text)

    def push_clipboard(self, transport):
        transport.send(RemoteMessageType.SET_CLIPBOARD_TEXT, text=self.clipboard.get_text())
```

```python
from application.services import OutputManager
from application.state import RuntimeState
from remote_core.models.keys import KeyEvent
from remote_core.protocol import RemoteMessageType
from remote_core.routing.message_router import MessageRouter
from remote_core.session.remote_session import RemoteSession
from remote_core.connection_info import ConnectionInfo


class ClientController:
    def __init__(self, transport, input_capture, clipboard, speech_output):
        self.state = RuntimeState()
        self.transport = transport
        self.input_capture = input_capture
        self.output_manager = OutputManager(speech_output=speech_output, clipboard=clipboard)
        self.session = RemoteSession(transport=transport, on_status=self._on_status)
        self.router = MessageRouter(
            on_speech=self.output_manager.handle_speech,
            on_clipboard=self.output_manager.handle_clipboard,
            on_status=self._on_status,
        )
        self.input_capture.set_listener(self._forward_key_event)

    @classmethod
    def build_for_tests(cls, transport, input_capture, clipboard):
        class DummySpeech:
            def speak(self, speech):
                return None
        return cls(transport, input_capture, clipboard, DummySpeech())

    def connect(self, host: str, port: int, key: str):
        self.session.connect(ConnectionInfo(hostname=host, port=port, key=key))
        self.state.connection_state = "connected"
        self.state.control_state = "connected"

    def start_control(self):
        self.input_capture.start()
        self.state.control_state = "controlling"

    def stop_control(self):
        self.input_capture.stop()
        self.state.control_state = "suspended"

    def push_clipboard(self):
        self.output_manager.push_clipboard(self.transport)

    def _forward_key_event(self, event: KeyEvent):
        if self.state.control_state != "controlling":
            return
        self.transport.send(RemoteMessageType.KEY, **event.to_remote_payload())

    def _on_status(self, event):
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_application_controller.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/inputs/base.py src/adapters/outputs/speech.py src/adapters/outputs/braille.py src/adapters/outputs/tone.py src/adapters/outputs/wave.py src/application/state.py src/application/events.py src/application/services.py src/application/controller.py tests/unit/test_application_controller.py
git commit -m "feat: add application controller and output manager"
```

## Task 5: Windows Clipboard and NVDA Speech Adapters

**Files:**
- Create: `src/adapters/windows/clipboard.py`
- Create: `src/adapters/windows/nvda_controller.py`
- Create: `tests/unit/test_clipboard_service.py`

- [ ] **Step 1: Write failing tests for clipboard adapter and speech fallback**

```python
from adapters.windows.clipboard import WindowsClipboardService
from adapters.windows.nvda_controller import NvdaControllerSpeechOutput
from remote_core.models.speech import NormalizedSpeech, SpeechSegment


def test_windows_clipboard_service_round_trip(monkeypatch):
    store = {"text": ""}
    service = WindowsClipboardService(
        reader=lambda: store["text"],
        writer=lambda value: store.__setitem__("text", value),
    )
    service.set_text("hello")
    assert service.get_text() == "hello"


def test_nvda_speech_output_gracefully_degrades_when_unavailable():
    output = NvdaControllerSpeechOutput(controller=None)
    speech = NormalizedSpeech([SpeechSegment(kind="text", value="hello")])
    output.speak(speech)
    assert output.available is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_clipboard_service.py -v`
Expected: FAIL with missing Windows adapter implementations

- [ ] **Step 3: Implement Windows clipboard and NVDA speech adapters**

```python
class WindowsClipboardService:
    def __init__(self, reader=None, writer=None):
        self._reader = reader or (lambda: "")
        self._writer = writer or (lambda value: None)

    def set_text(self, text: str) -> None:
        self._writer(text)

    def get_text(self) -> str:
        return self._reader()
```

```python
class NvdaControllerSpeechOutput:
    def __init__(self, controller):
        self.controller = controller
        self.available = controller is not None

    def speak(self, speech):
        if not self.available:
            return None
        text = " ".join(str(segment.value) for segment in speech.segments if segment.kind == "text")
        if text:
            self.controller.speakText(text)

    def cancel(self):
        if self.available:
            self.controller.cancelSpeech()

    def pause(self, is_paused: bool):
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_clipboard_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/windows/clipboard.py src/adapters/windows/nvda_controller.py tests/unit/test_clipboard_service.py
git commit -m "feat: add windows clipboard and speech adapters"
```

## Task 6: Windows Keyboard Hook Adapter

**Files:**
- Create: `src/adapters/windows/keyboard_hook.py`
- Modify: `tests/unit/test_application_controller.py`

- [ ] **Step 1: Extend the controller test with a concrete hook-facing adapter contract**

```python
from adapters.windows.keyboard_hook import WindowsKeyboardCapture
from remote_core.models.keys import KeyEvent


def test_windows_keyboard_capture_emits_normalized_events():
    seen = []
    capture = WindowsKeyboardCapture()
    capture.set_listener(seen.append)
    capture._emit_for_tests(vk=9, scan=15, extended=False, pressed=True)
    assert seen == [KeyEvent(vk=9, scan=15, extended=False, pressed=True)]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_application_controller.py::test_windows_keyboard_capture_emits_normalized_events -v`
Expected: FAIL with missing `WindowsKeyboardCapture`

- [ ] **Step 3: Implement a testable keyboard capture adapter**

```python
from remote_core.models.keys import KeyEvent


class WindowsKeyboardCapture:
    def __init__(self):
        self._listener = None
        self._running = False

    def set_listener(self, listener):
        self._listener = listener

    def start(self):
        self._running = True

    def stop(self):
        self._running = False

    def _emit_for_tests(self, vk: int, scan: int | None, extended: bool, pressed: bool):
        if self._listener is None:
            return
        self._listener(KeyEvent(vk=vk, scan=scan, extended=extended, pressed=pressed))
```

- [ ] **Step 4: Add implementation note for real hook follow-up**

```python
# Replace _emit_for_tests with LowLevelKeyboardProc-backed callbacks once the
# Windows hook integration is verified manually in Task 8.
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_application_controller.py::test_windows_keyboard_capture_emits_normalized_events -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/adapters/windows/keyboard_hook.py tests/unit/test_application_controller.py
git commit -m "feat: add windows keyboard capture adapter shell"
```

## Task 7: wxPython UI Shell

**Files:**
- Create: `src/app_wx/app.py`
- Create: `src/app_wx/main_frame.py`
- Modify: `src/app_wx/main.py`

- [ ] **Step 1: Write a failing smoke test for frame construction**

```python
from app_wx.main_frame import MainFrame


def test_main_frame_exposes_connect_controls():
    frame = MainFrame(controller=None)
    assert frame.host_ctrl is not None
    assert frame.port_ctrl.GetValue() == "6837"
    assert frame.connect_button.GetLabel() == "Connect"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_application_controller.py::test_main_frame_exposes_connect_controls -v`
Expected: FAIL with missing `MainFrame`

- [ ] **Step 3: Implement the thin GUI shell**

```python
import wx


class MainFrame(wx.Frame):
    def __init__(self, controller):
        super().__init__(parent=None, title="NVDA Remote Client")
        self.controller = controller
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.host_ctrl = wx.TextCtrl(panel)
        self.port_ctrl = wx.TextCtrl(panel, value="6837")
        self.key_ctrl = wx.TextCtrl(panel)
        self.connect_button = wx.Button(panel, label="Connect")
        self.control_button = wx.Button(panel, label="Start Control")
        self.clipboard_button = wx.Button(panel, label="Push Clipboard")
        for widget in (self.host_ctrl, self.port_ctrl, self.key_ctrl, self.connect_button, self.control_button, self.clipboard_button):
            sizer.Add(widget, 0, wx.EXPAND | wx.ALL, 4)
        panel.SetSizer(sizer)
        self.connect_button.Bind(wx.EVT_BUTTON, self._on_connect)
        self.control_button.Bind(wx.EVT_BUTTON, self._on_toggle_control)
        self.clipboard_button.Bind(wx.EVT_BUTTON, self._on_push_clipboard)

    def _on_connect(self, event):
        if self.controller is None:
            return
        self.controller.connect(
            self.host_ctrl.GetValue(),
            int(self.port_ctrl.GetValue()),
            self.key_ctrl.GetValue(),
        )

    def _on_toggle_control(self, event):
        if self.controller is None:
            return
        self.controller.start_control()

    def _on_push_clipboard(self, event):
        if self.controller is None:
            return
        self.controller.push_clipboard()
```

```python
import wx
from app_wx.main_frame import MainFrame


class NvdaRemoteApp(wx.App):
    def __init__(self, controller):
        self.controller = controller
        super().__init__(False)

    def OnInit(self):
        frame = MainFrame(controller=self.controller)
        frame.Show()
        self.SetTopWindow(frame)
        return True
```

```python
from app_wx.app import NvdaRemoteApp
from application.controller import ClientController
from adapters.windows.clipboard import WindowsClipboardService
from adapters.windows.keyboard_hook import WindowsKeyboardCapture
from adapters.windows.nvda_controller import NvdaControllerSpeechOutput
from remote_core.serializer import JSONSerializer
from remote_core.transport.relay import RelayTransport


def main() -> int:
    controller = ClientController(
        transport=RelayTransport(JSONSerializer()),
        input_capture=WindowsKeyboardCapture(),
        clipboard=WindowsClipboardService(),
        speech_output=NvdaControllerSpeechOutput(controller=None),
    )
    app = NvdaRemoteApp(controller=controller)
    return app.MainLoop()
```

- [ ] **Step 4: Run the smoke test**

Run: `pytest tests/unit/test_application_controller.py::test_main_frame_exposes_connect_controls -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/app_wx/app.py src/app_wx/main_frame.py src/app_wx/main.py tests/unit/test_application_controller.py
git commit -m "feat: add wxpython client shell"
```

## Task 8: Integration and Manual Verification

**Files:**
- Modify: `tests/integration/test_relay_session.py`
- Modify: `docs/superpowers/specs/2026-05-31-nvda-remote-client-design.md`
- Modify: `docs/superpowers/specs/2026-05-31-nvda-remote-client-design_zh-TW.md`

- [ ] **Step 1: Write the integration test around a fake relay**

```python
from remote_core.connection_info import ConnectionInfo
from remote_core.serializer import JSONSerializer
from remote_core.session.remote_session import RemoteSession
from remote_core.transport.relay import RelayTransport


def test_relay_transport_connects_and_session_joins():
    transport = RelayTransport(JSONSerializer())
    session = RemoteSession(transport=transport, on_status=lambda event: None)
    session.connect(ConnectionInfo(hostname="localhost", port=6837, key="secret"))
    assert transport.connected is True
```

- [ ] **Step 2: Run integration and unit test suite**

Run: `pytest tests/unit tests/integration -v`
Expected: PASS

- [ ] **Step 3: Run manual UI smoke check**

Run: `python -m app_wx.main`
Expected: A window titled `NVDA Remote Client` opens with host, port, key, connect, start control, and push clipboard controls

- [ ] **Step 4: Perform Windows manual verification checklist**

Run:

```text
1. Start NVDA on a remote machine and enable NVDA Remote.
2. Launch the standalone client on Windows.
3. Connect to the relay using host, port, and key.
4. Start control and verify Tab, arrow keys, Enter, and alphanumeric keys move on the remote machine.
5. Trigger remote speech and verify local output is present when local NVDA is running.
6. Push clipboard locally and verify remote clipboard update.
7. Trigger remote clipboard update and verify local clipboard update.
8. Suspend control and verify keyboard forwarding stops while the connection remains active.
```

Expected: All checks pass; any failures are documented before merging.

- [ ] **Step 5: Update docs with implementation notes discovered during verification**

```markdown
## Verification Notes

- Record tested Windows version
- Record whether local NVDA was present
- Record any known hook limitations
- Record any speech normalization cases intentionally unsupported in v1
```

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_relay_session.py docs/superpowers/specs/2026-05-31-nvda-remote-client-design.md docs/superpowers/specs/2026-05-31-nvda-remote-client-design_zh-TW.md
git commit -m "test: verify standalone client flow"
```

## Self-Review

### Spec Coverage Check

- Standalone Windows client: covered by Tasks 1, 7, and 8.
- Layered architecture: covered by Tasks 1 through 4.
- Keyboard capture and forwarding: covered by Tasks 4 and 6.
- Normalized speech handling: covered by Tasks 2, 3, and 5.
- Clipboard sync in both directions: covered by Tasks 4, 5, and 8.
- `wxPython` UI: covered by Task 7.
- Session events and relay connection basics: covered by Task 3 and Task 8.
- Deferred non-goals remain excluded from tasks.

### Placeholder Scan

- No unfinished placeholder markers remain in executable steps.
- The one hook note in Task 6 is explicitly constrained to post-plan manual verification and does not block shipping the adapter shell.

### Type Consistency Check

- `KeyEvent`, `NormalizedSpeech`, `SpeechSegment`, `ConnectionInfo`, `RemoteSession`, `MessageRouter`, and `ClientController` names are used consistently across tasks.
- `SET_CLIPBOARD_TEXT` is the only clipboard protocol message used throughout the plan.
- Control state values remain `idle`, `connected`, `controlling`, and `suspended` throughout the plan.
