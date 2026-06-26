# Speech Runtime Settings And NVDA Remote Protocol Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract shared speech runtime settings persistence from app entrypoints, replace NVDA Remote's dict-based protocol status flow with typed events, and split NVDA Remote orchestration into smaller use cases around that typed boundary.

**Architecture:** Implement the work in three milestones that can merge independently: shared speech runtime settings coordination, typed protocol events for `RemoteSession` and `MessageRouter`, and an orchestration split that leaves `NvdaRemoteAppService` as a thin UI-facing facade. Keep config schema and UI behavior stable while moving duplication and protocol parsing out of the current entrypoints and app service.

**Tech Stack:** Python 3.11+, `pytest`, existing `SpeechEngineConfigStore`, `SpeechSettingsController`, `RemoteSession`, `MessageRouter`, wxPython-compatible app services, dataclasses

---

## File Structure

| File | Responsibility |
|---|---|
| `src/apps/shared/speech_runtime_settings.py` | New shared coordinator for startup engine selection, saved speech setting application, and engine-change persistence callbacks |
| `src/apps/nvda_remote/main.py` | Replace inline speech settings startup logic with the shared coordinator |
| `src/apps/key_echo/main.py` | Replace inline fixed-engine speech settings startup logic with the shared coordinator |
| `src/apps/access8graph/main.py` | Replace inline speech settings startup logic with the shared coordinator |
| `tests/unit/test_speech_runtime_settings.py` | New focused coordinator tests |
| `src/interop/protocol/events.py` | New typed protocol event dataclasses shared by session and router |
| `src/interop/protocol/session/remote_session.py` | Emit typed session/protocol events instead of dict payloads |
| `src/interop/protocol/routing/message_router.py` | Emit typed protocol events for remote passthrough and invalid messages |
| `tests/unit/test_remote_session.py` | New session contract tests moved out of router coverage |
| `tests/unit/test_message_router.py` | Router-specific typed event tests |
| `src/apps/nvda_remote/service.py` | Consume typed protocol events and delegate orchestration to smaller units |
| `src/apps/nvda_remote/use_cases/connection.py` | New connection/disconnection orchestration and state transition handling |
| `src/apps/nvda_remote/use_cases/protocol_events.py` | New mapper/handler for typed protocol events to app state and app events |
| `src/apps/nvda_remote/use_cases/status_presentation.py` | New UI-facing status dispatch helper for app and protocol events |
| `tests/unit/test_nvda_remote_use_cases.py` | Focused tests for new NVDA Remote use cases |
| `tests/unit/test_nvda_remote_app_service.py` | Regression tests for facade wiring and behavior after the split |

## Task 1: Add Shared Speech Runtime Settings Coordinator

**Files:**
- Create: `src/apps/shared/speech_runtime_settings.py`
- Create: `tests/unit/test_speech_runtime_settings.py`
- Modify: `src/apps/shared/__init__.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_speech_runtime_settings.py`:

```python
from application.config import SpeechEngineConfigStore
from apps.shared.speech_runtime_settings import SpeechRuntimeSettingsCoordinator


class FakeSpeech:
    def __init__(self) -> None:
        self.selected_engine = "engine-a"
        self.voice = None
        self.rate = None
        self.pitch = None
        self.volume = None
        self.voices = (("voice-a", "Voice A"),)
        self.supported_settings = []

    def get_selected_engine(self) -> str:
        return self.selected_engine

    def list_voices(self):
        return self.voices

    def set_voice(self, voice_id: str) -> None:
        self.voice = voice_id

    def get_supported_numeric_settings(self):
        return self.supported_settings

    def set_rate(self, value: int) -> None:
        self.rate = value

    def set_pitch(self, value: int) -> None:
        self.pitch = value

    def set_volume(self, value: int) -> None:
        self.volume = value


class FakeSetting:
    def __init__(self, setting_id: str) -> None:
        self.id = setting_id


def test_coordinator_applies_saved_voice_and_supported_numeric_settings(tmp_path):
    store = SpeechEngineConfigStore(tmp_path / "speech.json")
    store.save_voice("engine-a", "voice-a")
    store.save_numeric_setting("engine-a", "rate", 70)
    store.save_numeric_setting("engine-a", "pitch", 20)
    store.save_numeric_setting("engine-a", "volume", 90)
    speech = FakeSpeech()
    speech.supported_settings = [FakeSetting("rate"), FakeSetting("volume")]
    coordinator = SpeechRuntimeSettingsCoordinator(config_store=store)

    coordinator.apply_saved_settings(speech=speech, engine_id="engine-a")

    assert speech.voice == "voice-a"
    assert speech.rate == 70
    assert speech.pitch is None
    assert speech.volume == 90


def test_coordinator_builds_engine_change_callback_that_persists_and_reapplies(tmp_path):
    store = SpeechEngineConfigStore(tmp_path / "speech.json")
    store.save_voice("engine-b", "voice-b")
    speech = FakeSpeech()
    speech.voices = (("voice-b", "Voice B"),)
    coordinator = SpeechRuntimeSettingsCoordinator(config_store=store)

    on_engine_changed = coordinator.build_engine_change_callback(speech=speech)
    on_engine_changed("engine-b")

    assert store.load_engine_id(default_engine_id="fallback") == "engine-b"
    assert speech.voice == "voice-b"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_speech_runtime_settings.py -v`

Expected: FAIL with `ModuleNotFoundError` for `apps.shared.speech_runtime_settings`.

- [ ] **Step 3: Write the minimal implementation**

Create `src/apps/shared/speech_runtime_settings.py`:

```python
from __future__ import annotations

from application.config import SpeechEngineConfigStore
from application.output.speech import SpeechService


class SpeechRuntimeSettingsCoordinator:
    def __init__(self, *, config_store: SpeechEngineConfigStore) -> None:
        self._config_store = config_store

    def selected_engine_id(self, *, default_engine_id: str) -> str:
        return self._config_store.load_engine_id(default_engine_id=default_engine_id)

    def apply_saved_settings(self, *, speech: SpeechService, engine_id: str) -> None:
        voice_id = self._config_store.load_voice(engine_id)
        available_voice_ids = {voice for voice, _label in speech.list_voices()}
        if voice_id is not None and voice_id in available_voice_ids:
            speech.set_voice(voice_id)
        supported = {setting.id for setting in speech.get_supported_numeric_settings()}
        for setting_id, setter in (
            ("rate", speech.set_rate),
            ("pitch", speech.set_pitch),
            ("volume", speech.set_volume),
        ):
            value = self._config_store.load_numeric_setting(engine_id, setting_id)
            if value is not None and setting_id in supported:
                setter(value)

    def build_engine_change_callback(self, *, speech: SpeechService):
        def _on_engine_changed(engine_id: str) -> None:
            self._config_store.save_engine_id(engine_id)
            self.apply_saved_settings(speech=speech, engine_id=engine_id)

        return _on_engine_changed
```

Update `src/apps/shared/__init__.py`:

```python
from apps.shared.speech_runtime_settings import SpeechRuntimeSettingsCoordinator
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_speech_runtime_settings.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/apps/shared/__init__.py src/apps/shared/speech_runtime_settings.py tests/unit/test_speech_runtime_settings.py
git commit -m "feat: add speech runtime settings coordinator"
```

## Task 2: Rewire App Entrypoints To Use The Shared Coordinator

**Files:**
- Modify: `src/apps/nvda_remote/main.py`
- Modify: `src/apps/key_echo/main.py`
- Modify: `src/apps/access8graph/main.py`
- Modify: `tests/unit/test_bootstrap_app_runtime.py`
- Modify: `tests/unit/test_app_wx.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_bootstrap_app_runtime.py`:

```python
from application.config import SpeechEngineConfigStore
from apps.shared.speech_runtime_settings import SpeechRuntimeSettingsCoordinator


def test_coordinator_selected_engine_id_uses_store_default(tmp_path):
    store = SpeechEngineConfigStore(tmp_path / "speech.json")
    coordinator = SpeechRuntimeSettingsCoordinator(config_store=store)

    assert coordinator.selected_engine_id(default_engine_id="Pyttsx3") == "Pyttsx3"


def test_coordinator_selected_engine_id_reads_saved_engine(tmp_path):
    store = SpeechEngineConfigStore(tmp_path / "speech.json")
    store.save_engine_id("NvdaController")
    coordinator = SpeechRuntimeSettingsCoordinator(config_store=store)

    assert coordinator.selected_engine_id(default_engine_id="Pyttsx3") == "NvdaController"
```

Add one regression assertion to an existing app runtime test in `tests/unit/test_app_wx.py` that already builds `nvda_remote` runtime:

```python
assert runtime.app_service.get_selected_speech_engine() == runtime.speech.get_selected_engine()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_bootstrap_app_runtime.py -k "selected_engine_id" tests/unit/test_app_wx.py -k "nvda_remote" -v`

Expected: at least one FAIL because the coordinator is not yet used by the runtime tests or the import path is missing in app wiring.

- [ ] **Step 3: Rewire the three entrypoints**

Replace the duplicated speech settings blocks in the three entrypoints with the coordinator pattern.

`src/apps/nvda_remote/main.py`:

```python
from apps.shared.speech_runtime_settings import SpeechRuntimeSettingsCoordinator

config_store = SpeechEngineConfigStore(default_config_path())
coordinator = SpeechRuntimeSettingsCoordinator(config_store=config_store)
provider = PlatformProvider()
default_engine_id = provider.default_speech_engine_id()
selected_engine_id = coordinator.selected_engine_id(default_engine_id=default_engine_id)
parts = build_app_runtime_parts(
    provider=provider,
    hotkey_usage=NvdaRemoteAppService.enter_usage,
    selected_engine_id=selected_engine_id,
    fallback_engine_id=default_engine_id,
    on_engine_fallback=config_store.save_engine_id,
    include_clipboard=True,
)
coordinator.apply_saved_settings(
    speech=parts.output.speech,
    engine_id=parts.output.speech.get_selected_engine(),
)
on_speech_engine_changed = coordinator.build_engine_change_callback(
    speech=parts.output.speech,
)
```

`src/apps/key_echo/main.py`:

```python
from apps.shared.speech_runtime_settings import SpeechRuntimeSettingsCoordinator

config_store = SpeechEngineConfigStore(default_config_path())
coordinator = SpeechRuntimeSettingsCoordinator(config_store=config_store)
parts = build_app_runtime_parts(
    hotkey_usage=KeyEchoAppService.enter_usage,
    selected_engine_id="Pyttsx3",
    fallback_engine_id="Pyttsx3",
    include_tone=False,
)
coordinator.apply_saved_settings(speech=parts.output.speech, engine_id="Pyttsx3")
on_speech_engine_changed = coordinator.build_engine_change_callback(
    speech=parts.output.speech,
)
```

`src/apps/access8graph/main.py`:

```python
from apps.shared.speech_runtime_settings import SpeechRuntimeSettingsCoordinator

config_store = SpeechEngineConfigStore(default_config_path())
coordinator = SpeechRuntimeSettingsCoordinator(config_store=config_store)
provider = PlatformProvider()
default_engine_id = provider.default_speech_engine_id()
selected_engine_id = coordinator.selected_engine_id(default_engine_id=default_engine_id)
parts = build_app_runtime_parts(
    hotkey_usage=Access8GraphAppService.enter_usage,
    selected_engine_id=selected_engine_id,
    fallback_engine_id=default_engine_id,
    on_engine_fallback=config_store.save_engine_id,
)
coordinator.apply_saved_settings(speech=parts.output.speech, engine_id=selected_engine_id)
on_speech_engine_changed = coordinator.build_engine_change_callback(
    speech=parts.output.speech,
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_speech_runtime_settings.py tests/unit/test_bootstrap_app_runtime.py tests/unit/test_app_wx.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/apps/nvda_remote/main.py src/apps/key_echo/main.py src/apps/access8graph/main.py tests/unit/test_bootstrap_app_runtime.py tests/unit/test_app_wx.py
git commit -m "refactor: share speech runtime settings wiring"
```

## Task 3: Add Typed Protocol Event Models And Move Session Tests

**Files:**
- Create: `src/interop/protocol/events.py`
- Create: `tests/unit/test_remote_session.py`
- Modify: `src/interop/protocol/session/remote_session.py`
- Modify: `tests/unit/test_message_router.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_remote_session.py`:

```python
from interop.protocol.events import (
    RemotePeerMessageReceived,
    RemoteSessionConnected,
    RemoteSessionDisconnected,
    RemoteSessionVersionMismatch,
)
from interop.protocol.session.remote_session import RemoteSession


class DummyTransport:
    def __init__(self) -> None:
        self.closed = False
        self.sent = []

    def connect(self, host, port, insecure=False):
        self.sent.append(("connect", host, port, insecure))

    def send(self, message_type, **payload):
        self.sent.append((message_type, payload))

    def close(self):
        self.closed = True


def test_session_reports_connected_after_channel_joined():
    seen = []
    session = RemoteSession(transport=DummyTransport(), on_event=seen.append)

    assert session.handle_message({"type": "channel_joined"}) is True

    assert seen == [RemoteSessionConnected()]


def test_session_disconnect_emits_disconnected_event():
    seen = []
    transport = DummyTransport()
    session = RemoteSession(transport=transport, on_event=seen.append)

    session.disconnect()

    assert transport.closed is True
    assert seen == [RemoteSessionDisconnected()]


def test_session_emits_version_mismatch_and_remote_messages():
    seen = []
    session = RemoteSession(transport=DummyTransport(), on_event=seen.append)
    motd = {"type": "motd", "message": "hello"}

    assert session.handle_message({"type": "version_mismatch"}) is True
    assert session.handle_message(motd) is True

    assert seen == [
        RemoteSessionVersionMismatch(),
        RemotePeerMessageReceived(message_type="motd", payload=motd),
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_remote_session.py -v`

Expected: FAIL because `interop.protocol.events` does not exist and `RemoteSession` still takes `on_status`.

- [ ] **Step 3: Add the typed event model and update `RemoteSession`**

Create `src/interop/protocol/events.py`:

```python
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RemoteSessionConnected:
    pass


@dataclass(frozen=True, slots=True)
class RemoteSessionDisconnected:
    pass


@dataclass(frozen=True, slots=True)
class RemoteSessionVersionMismatch:
    pass


@dataclass(frozen=True, slots=True)
class RemotePeerMessageReceived:
    message_type: str
    payload: dict[str, Any]
```

Update `src/interop/protocol/session/remote_session.py`:

```python
from collections.abc import Callable
from interop.protocol.events import (
    RemotePeerMessageReceived,
    RemoteSessionConnected,
    RemoteSessionDisconnected,
    RemoteSessionVersionMismatch,
)

class RemoteSession:
    def __init__(self, transport: Transport, on_event: Callable[[object], None]) -> None:
        self.transport = transport
        self.on_event = on_event

    def disconnect(self) -> None:
        self.transport.close()
        self.on_event(RemoteSessionDisconnected())

    def handle_message(self, payload: dict[str, Any]) -> bool:
        match payload.get("type"):
            case RemoteMessageType.CHANNEL_JOINED.value:
                self.on_event(RemoteSessionConnected())
                return True
            case RemoteMessageType.VERSION_MISMATCH.value:
                self.on_event(RemoteSessionVersionMismatch())
                return True
            case (
                RemoteMessageType.MOTD.value
                | RemoteMessageType.CLIENT_JOINED.value
                | RemoteMessageType.CLIENT_LEFT.value
                | RemoteMessageType.ERROR.value
            ):
                self.on_event(
                    RemotePeerMessageReceived(
                        message_type=str(payload.get("type", "")),
                        payload=payload,
                    )
                )
                return True
```

Remove the old session assertions from `tests/unit/test_message_router.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_remote_session.py tests/unit/test_message_router.py -v`

Expected: session tests PASS; router tests that still depend on dict status may still FAIL until the next task.

- [ ] **Step 5: Commit**

```bash
git add src/interop/protocol/events.py src/interop/protocol/session/remote_session.py tests/unit/test_remote_session.py tests/unit/test_message_router.py
git commit -m "feat: add typed remote session events"
```

## Task 4: Migrate `MessageRouter` To Typed Protocol Events

**Files:**
- Modify: `src/interop/protocol/routing/message_router.py`
- Modify: `src/interop/protocol/events.py`
- Modify: `tests/unit/test_message_router.py`

- [ ] **Step 1: Write the failing router tests**

Update `tests/unit/test_message_router.py` to assert typed events:

```python
from interop.protocol.events import (
    RemotePeerMessageReceived,
    RemoteProtocolMessageInvalid,
)


def test_router_reports_unknown_messages_as_remote_peer_messages():
    seen = []
    router = build_router(seen)
    payload = {"type": "motd", "message": "hi"}

    router.handle_message(payload)

    assert seen == [("status", RemotePeerMessageReceived(message_type="motd", payload=payload))]


def test_router_reports_missing_clipboard_text_as_invalid_message():
    seen = []
    router = build_router(seen)
    payload = {"type": "set_clipboard_text"}

    router.handle_message(payload)

    assert seen == [
        (
            "status",
            RemoteProtocolMessageInvalid(
                reason="clipboard_text_must_be_string",
                payload=payload,
            ),
        )
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_message_router.py -k "remote_peer or invalid_message" -v`

Expected: FAIL because the router still emits dict status payloads.

- [ ] **Step 3: Update event types and router emission**

Append to `src/interop/protocol/events.py`:

```python
@dataclass(frozen=True, slots=True)
class RemoteProtocolMessageIgnored:
    message_type: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RemoteProtocolMessageInvalid:
    reason: str
    payload: dict[str, Any]
```

Update `src/interop/protocol/routing/message_router.py`:

```python
from interop.protocol.events import (
    RemotePeerMessageReceived,
    RemoteProtocolMessageInvalid,
)

class MessageRouter:
    def __init__(..., on_status: Callable[[object], None]) -> None:
        ...

    def handle_message(self, payload: dict[str, Any]) -> None:
        match payload.get("type"):
            ...
            case _:
                self._on_status(
                    RemotePeerMessageReceived(
                        message_type=str(payload.get("type", "")),
                        payload=payload,
                    )
                )

    def _handle_clipboard_message(self, payload: dict[str, Any]) -> None:
        text = payload.get("text")
        if not isinstance(text, str):
            self._on_status(
                RemoteProtocolMessageInvalid(
                    reason="clipboard_text_must_be_string",
                    payload=payload,
                )
            )
            return
```

Apply the same `RemoteProtocolMessageInvalid(...)` pattern in `_handle_pause_message()` and `_handle_tone_message()`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_message_router.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/interop/protocol/events.py src/interop/protocol/routing/message_router.py tests/unit/test_message_router.py
git commit -m "feat: add typed message router events"
```

## Task 5: Consume Typed Protocol Events In `NvdaRemoteAppService`

**Files:**
- Modify: `src/apps/nvda_remote/service.py`
- Modify: `src/apps/nvda_remote/events.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`
- Modify: `tests/unit/test_application_events.py`
- Modify: `src/application/events.py`

- [ ] **Step 1: Write the failing app-service tests**

Append to `tests/unit/test_nvda_remote_app_service.py`:

```python
from interop.protocol.events import (
    RemotePeerMessageReceived,
    RemoteProtocolMessageInvalid,
    RemoteSessionConnected,
)


def test_nvda_remote_service_handles_typed_session_connected_event():
    service, _transport, _capture, hotkey, _dispatch_calls = build_service()
    delivered = []
    service.set_status_listener(delivered.append)

    service._on_protocol_event(RemoteSessionConnected())

    assert service.state.connection_state == service.state.connection_state.CONNECTED
    assert hotkey.started == 1
    assert delivered == [RemoteConnectionChanged("connected")]


def test_nvda_remote_service_converts_typed_remote_peer_message_for_listener():
    service, _transport, _capture, _hotkey, _dispatch_calls = build_service()
    delivered = []
    payload = {"type": "motd", "message": "hello"}
    service.set_status_listener(delivered.append)

    service._on_protocol_event(
        RemotePeerMessageReceived(message_type="motd", payload=payload)
    )

    assert delivered == [RemoteMessageReceived("motd", payload)]


def test_nvda_remote_service_ignores_invalid_protocol_messages_for_listener():
    service, _transport, _capture, _hotkey, _dispatch_calls = build_service()
    delivered = []
    service.set_status_listener(delivered.append)

    service._on_protocol_event(
        RemoteProtocolMessageInvalid(
            reason="clipboard_text_must_be_string",
            payload={"type": "set_clipboard_text"},
        )
    )

    assert delivered == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_nvda_remote_app_service.py -k "typed_session_connected or typed_remote_peer or invalid_protocol_messages" -v`

Expected: FAIL because `_on_protocol_event()` does not exist and the service still uses `_on_status()`.

- [ ] **Step 3: Replace dict-based protocol consumption**

Update `src/apps/nvda_remote/service.py`:

```python
from interop.protocol.events import (
    RemotePeerMessageReceived,
    RemoteProtocolMessageInvalid,
    RemoteSessionConnected,
    RemoteSessionDisconnected,
    RemoteSessionVersionMismatch,
)

self.session = RemoteSession(transport=transport, on_event=self._on_protocol_event)
self.router = MessageRouter(..., on_status=self._on_protocol_event)

def _on_protocol_event(self, event: object) -> None:
    match event:
        case RemoteSessionConnected():
            self._handle_connection_status(ConnectionState.CONNECTED.value)
        case RemoteSessionDisconnected():
            self._handle_connection_status(ConnectionState.IDLE.value)
        case RemoteSessionVersionMismatch():
            _logger.debug("Ignoring version mismatch for UI listener")
        case RemotePeerMessageReceived(message_type=message_type, payload=payload):
            self._notify_status_listener(RemoteMessageReceived(message_type, payload))
        case RemoteProtocolMessageInvalid():
            _logger.debug("Ignoring invalid protocol event for UI listener: %s", event)
```

Remove `StatusEvent` usage from the service and delete `_on_status()` / `_event_from_status()` after migrating the callers. In `src/application/events.py`, keep `StatusEvent` only if `tests/unit/test_application_events.py` still explicitly verifies the transitional helper; otherwise remove it and update the tests to cover only shared typed events.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_nvda_remote_app_service.py tests/unit/test_application_events.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/apps/nvda_remote/service.py src/application/events.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_application_events.py
git commit -m "refactor: consume typed protocol events in nvda remote"
```

## Task 6: Split NVDA Remote Connection And Protocol Orchestration

**Files:**
- Create: `src/apps/nvda_remote/use_cases/connection.py`
- Create: `src/apps/nvda_remote/use_cases/protocol_events.py`
- Create: `src/apps/nvda_remote/use_cases/status_presentation.py`
- Modify: `src/apps/nvda_remote/use_cases/__init__.py`
- Modify: `src/apps/nvda_remote/service.py`
- Modify: `tests/unit/test_nvda_remote_use_cases.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`

- [ ] **Step 1: Write the failing use-case tests**

Append to `tests/unit/test_nvda_remote_use_cases.py`:

```python
from application.state import ConnectionState, ControlState, RuntimeState
from apps.nvda_remote.events import RemoteConnectionChanged, RemoteMessageReceived
from apps.nvda_remote.use_cases.connection import RemoteConnectionUseCase
from apps.nvda_remote.use_cases.protocol_events import RemoteProtocolEventHandler
from interop.protocol.events import RemotePeerMessageReceived, RemoteSessionConnected


def test_remote_connection_use_case_sets_connected_state_and_requests_hotkey_start():
    state = RuntimeState()
    effects = []
    use_case = RemoteConnectionUseCase(
        state=state,
        exit_active=lambda: effects.append("exit_active"),
        ensure_hotkey_started=lambda: effects.append("ensure_hotkey_started"),
        stop_capture=lambda: effects.append("stop_capture"),
        stop_hotkey=lambda: effects.append("stop_hotkey"),
        notify=lambda event: effects.append(event),
    )

    use_case.handle_connected()

    assert state.connection_state == ConnectionState.CONNECTED
    assert state.control_state == ControlState.CONNECTED
    assert effects == [
        "exit_active",
        "ensure_hotkey_started",
        RemoteConnectionChanged("connected"),
    ]


def test_remote_protocol_event_handler_maps_remote_peer_messages():
    delivered = []
    handler = RemoteProtocolEventHandler(
        on_connected=lambda: delivered.append("connected"),
        on_disconnected=lambda: delivered.append("disconnected"),
        notify_remote_message=lambda event: delivered.append(event),
    )

    handler.handle(RemoteSessionConnected())
    handler.handle(
        RemotePeerMessageReceived(
            message_type="motd",
            payload={"type": "motd", "message": "hello"},
        )
    )

    assert delivered == [
        "connected",
        RemoteMessageReceived("motd", {"type": "motd", "message": "hello"}),
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_nvda_remote_use_cases.py -k "connection_use_case or protocol_event_handler" -v`

Expected: FAIL because the new modules do not exist.

- [ ] **Step 3: Implement the orchestration use cases and thin the service**

Create `src/apps/nvda_remote/use_cases/connection.py`:

```python
from application.state import ConnectionState, ControlState, RuntimeState
from apps.nvda_remote.events import RemoteConnectionChanged


class RemoteConnectionUseCase:
    def __init__(self, *, state: RuntimeState, exit_active, ensure_hotkey_started, stop_capture, stop_hotkey, notify) -> None:
        self._state = state
        self._exit_active = exit_active
        self._ensure_hotkey_started = ensure_hotkey_started
        self._stop_capture = stop_capture
        self._stop_hotkey = stop_hotkey
        self._notify = notify

    def handle_connected(self) -> None:
        self._state.connection_state = ConnectionState.CONNECTED
        if self._state.control_state != ControlState.CONTROLLING:
            self._state.control_state = ControlState.CONNECTED
            self._exit_active()
            self._ensure_hotkey_started()
        self._notify(RemoteConnectionChanged("connected"))

    def handle_disconnected(self) -> None:
        self._stop_capture()
        self._stop_hotkey()
        self._state.connection_state = ConnectionState.IDLE
        self._state.control_state = ControlState.IDLE
        self._notify(RemoteConnectionChanged("idle"))
```

Create `src/apps/nvda_remote/use_cases/protocol_events.py`:

```python
from apps.nvda_remote.events import RemoteMessageReceived
from interop.protocol.events import (
    RemotePeerMessageReceived,
    RemoteSessionConnected,
    RemoteSessionDisconnected,
)


class RemoteProtocolEventHandler:
    def __init__(self, *, on_connected, on_disconnected, notify_remote_message) -> None:
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected
        self._notify_remote_message = notify_remote_message

    def handle(self, event: object) -> None:
        match event:
            case RemoteSessionConnected():
                self._on_connected()
            case RemoteSessionDisconnected():
                self._on_disconnected()
            case RemotePeerMessageReceived(message_type=message_type, payload=payload):
                self._notify_remote_message(RemoteMessageReceived(message_type, payload))
```

Create `src/apps/nvda_remote/use_cases/status_presentation.py`:

```python
class RemoteStatusPresenter:
    def __init__(self, *, dispatch, get_listener) -> None:
        self._dispatch = dispatch
        self._get_listener = get_listener

    def notify(self, event) -> None:
        listener = self._get_listener()
        if listener is None:
            return
        self._dispatch(lambda: listener(event))
```

Then update `src/apps/nvda_remote/service.py` so `_handle_connection_status()` and direct listener dispatching are replaced by these use cases.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_app_service.py -v`

Expected: PASS.

- [ ] **Step 5: Run the full relevant regression suite**

Run: `pytest tests/unit/test_speech_runtime_settings.py tests/unit/test_bootstrap_app_runtime.py tests/unit/test_message_router.py tests/unit/test_remote_session.py tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_app_wx.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/apps/nvda_remote/service.py src/apps/nvda_remote/use_cases/__init__.py src/apps/nvda_remote/use_cases/connection.py src/apps/nvda_remote/use_cases/protocol_events.py src/apps/nvda_remote/use_cases/status_presentation.py tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_app_service.py
git commit -m "refactor: split nvda remote orchestration"
```

## Spec Coverage Check

- Milestone 1 is covered by Tasks 1-2.
- Milestone 2 is covered by Tasks 3-5.
- Milestone 3 is covered by Task 6.
- Non-goals remain respected:
  - no config schema rename
  - no Access8Graph refactor beyond entrypoint wiring
  - no output bus redesign
  - no DI container

## Placeholder Scan

Checked for forbidden placeholders:

- no `TBD`
- no `TODO`
- no "implement later"
- every task includes code, commands, expected failures, expected passes, and commit boundaries

## Type Consistency Check

- Shared coordinator name is consistently `SpeechRuntimeSettingsCoordinator`
- Typed protocol event callback is consistently `on_event`
- New protocol event module is consistently `src/interop/protocol/events.py`
- The orchestration split uses `RemoteConnectionUseCase`, `RemoteProtocolEventHandler`, and `RemoteStatusPresenter` consistently across later tasks
