# Input Architecture Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify `nvda_remote` and `key_echo` on the same `idle hotkey / active keyboard` input lifecycle, while extracting shared capture-transition and key-routing policy code into `application/`.

**Architecture:** Add a shared input layer that owns activation state, capture mutual exclusion, idle hotkey matching, and active key routing. Keep app-specific business behavior in app-local handlers: `nvda_remote` still owns remote forwarding rules and `key_echo` still owns echo playback rules, but both apps stop embedding their primary input state machine inside the facade.

**Tech Stack:** Python 3.12+, pytest, monkeypatch, existing `InputCapture` / `HotkeyCapture` protocols, `KeyboardInputService`, wxPython shell integration, macOS shared event tap path, Windows hotkey/keyboard hook adapters

---

## Planned File Structure

### New files

- `src/application/input/__init__.py`
  - Shared exports for the new input components
- `src/application/input/activation.py`
  - Shared activation lifecycle and capture mutual-exclusion logic
- `src/application/input/state_transition_hotkeys.py`
  - Shared idle hotkey mapping policy
- `src/application/input/active_key_policy.py`
  - Shared active keyboard routing policy
- `tests/unit/test_input_activation.py`
  - Direct tests for activation transitions and rollback
- `tests/unit/test_input_policies.py`
  - Direct tests for idle hotkey and active key routing policies

### Modified files

- `src/apps/nvda_remote/facade.py`
  - Compose shared input lifecycle components instead of owning the state machine directly
- `src/apps/nvda_remote/main.py`
  - Keep runtime wiring aligned with the new shared lifecycle model
- `src/apps/nvda_remote/use_cases/control_mode.py`
  - Remove duplicated capture transition responsibility if it moves into `application/input`
- `src/apps/nvda_remote/use_cases/input_forwarding.py`
  - Continue owning remote forwarding rules only
- `src/apps/key_echo/facade.py`
  - Switch from always-on keyboard capture assumptions to `idle hotkey / active keyboard`
- `src/apps/key_echo/main.py`
  - Add `HotkeyCapture` wiring and start in idle mode
- `src/apps/key_echo/use_cases/echo_control.py`
  - Stop owning capture lifecycle beyond echo-specific state reporting
- `tests/unit/test_nvda_remote_app_service.py`
  - Verify idle `F11` activation and active `F11` exit under the new shared model
- `tests/unit/test_key_echo_app_service.py`
  - Verify idle `Enter`, active `Escape`, active echo input, and shutdown behavior
- `tests/unit/test_app_wx.py`
  - Verify both runtimes start in idle mode and wire the right capture objects

---

### Task 1: Add failing tests for shared input activation and routing

**Files:**
- Create: `tests/unit/test_input_activation.py`
- Create: `tests/unit/test_input_policies.py`
- Modify: `tests/unit/test_key_echo_app_service.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`

- [ ] **Step 1: Add direct activation use-case tests**

Create `tests/unit/test_input_activation.py`:

```python
import pytest

from application.input.activation import InputActivationUseCase


class FakeCapture:
    def __init__(self, running: bool = False, fail_start: bool = False) -> None:
        self._running = running
        self._fail_start = fail_start
        self.started = 0
        self.stopped = 0

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        self.started += 1
        if self._fail_start:
            raise RuntimeError("boom")
        self._running = True

    def stop(self) -> None:
        self.stopped += 1
        self._running = False


def test_activation_enters_active_by_stopping_hotkey_and_starting_keyboard():
    keyboard = FakeCapture(running=False)
    hotkey = FakeCapture(running=True)
    errors: list[str] = []
    activation = InputActivationUseCase(
        input_capture=keyboard,
        hotkey_capture=hotkey,
        is_active=lambda: False,
        set_active=lambda active: errors.append(f"state={active}"),
        notify_error=errors.append,
    )

    assert activation.enter_active() is True
    assert keyboard.running is True
    assert hotkey.running is False
    assert keyboard.started == 1
    assert hotkey.stopped == 1
    assert "boom" not in errors


def test_activation_rolls_back_to_hotkey_when_keyboard_start_fails():
    keyboard = FakeCapture(running=False, fail_start=True)
    hotkey = FakeCapture(running=True)
    states: list[bool] = []
    errors: list[str] = []
    activation = InputActivationUseCase(
        input_capture=keyboard,
        hotkey_capture=hotkey,
        is_active=lambda: False,
        set_active=states.append,
        notify_error=errors.append,
    )

    assert activation.enter_active() is False
    assert keyboard.running is False
    assert hotkey.running is True
    assert states == []
    assert errors == ["boom"]
```

- [ ] **Step 2: Add direct idle/active policy tests**

Create `tests/unit/test_input_policies.py`:

```python
from adapters.inputs.base import KeyEventDecision
from interop.key.key_event import KeyEvent

from application.input.active_key_policy import ActiveKeyEventPolicy
from application.input.state_transition_hotkeys import StateTransitionHotkeyPolicy


def test_idle_hotkey_policy_matches_keydown_only():
    policy = StateTransitionHotkeyPolicy(mapping={0x7A: "enter_active"})

    assert policy.match(KeyEvent(vk=0x7A, scan=87, extended=False, pressed=True)) == "enter_active"
    assert policy.match(KeyEvent(vk=0x7A, scan=87, extended=False, pressed=False)) is None


def test_active_key_policy_uses_exit_key_before_normal_handler():
    calls: list[str] = []
    policy = ActiveKeyEventPolicy(
        exit_vk=0x1B,
        on_exit=lambda: calls.append("exit") or KeyEventDecision.SUPPRESS,
        on_key=lambda event: calls.append(f"key:{event.vk}") or KeyEventDecision.PASS_THROUGH,
    )

    exit_decision = policy.handle(KeyEvent(vk=0x1B, scan=1, extended=False, pressed=True))
    other_decision = policy.handle(KeyEvent(vk=65, scan=30, extended=False, pressed=True))

    assert exit_decision == KeyEventDecision.SUPPRESS
    assert other_decision == KeyEventDecision.PASS_THROUGH
    assert calls == ["exit", "key:65"]
```

- [ ] **Step 3: Add app-level regression tests for the target lifecycle**

Add to `tests/unit/test_key_echo_app_service.py`:

```python
def test_key_echo_app_service_idle_enter_uses_hotkey_path() -> None:
    capture = FakeCapture()
    hotkey = FakeHotkeyCapture()
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        hotkey_capture=hotkey,
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output)),
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.bind()

    hotkey.handler()

    assert service.is_echo_running() is True
    assert hotkey.stop_calls == 1
    assert capture.start_calls == 1


def test_key_echo_app_service_active_escape_exits_through_keyboard_pipeline() -> None:
    capture = FakeCapture()
    hotkey = FakeHotkeyCapture()
    speech_output = FakeSpeechOutput()
    service = KeyEchoAppService(
        hotkey_capture=hotkey,
        outputs=OutputCapabilities(speech=SpeechService.single_backend(speech_output)),
    )
    input_service = KeyboardInputService(capture, service)
    service.attach_input_service(input_service)
    service.bind()
    hotkey.handler()

    decision = service.handle_key_event(KeyEvent(vk=0x1B, scan=1, extended=False, pressed=True))

    assert decision == KeyEventDecision.SUPPRESS
    assert service.is_echo_running() is False
    assert capture.stop_calls == 1
    assert hotkey.start_calls == 2
```

Add to `tests/unit/test_nvda_remote_app_service.py`:

```python
def test_nvda_remote_service_idle_f11_uses_hotkey_capture_path():
    service, _transport, capture, hotkey, dispatch_calls = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.state.control_state = service.state.control_state.CONNECTED

    hotkey.handler()

    assert dispatch_calls == ["called"]
    assert service.state.control_state == service.state.control_state.CONTROLLING
    assert hotkey.stopped == 1
    assert capture.started == 1
```

- [ ] **Step 4: Run the focused tests and verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/unit/test_input_activation.py \
  tests/unit/test_input_policies.py \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_key_echo_app_service.py -v
```

Expected:

- FAIL because `application.input` modules do not exist yet
- FAIL because `KeyEchoAppService` does not accept `hotkey_capture`
- FAIL because `key_echo` does not bind an idle hotkey path

- [ ] **Step 5: Commit**

```bash
git add \
  tests/unit/test_input_activation.py \
  tests/unit/test_input_policies.py \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_key_echo_app_service.py
git commit -m "test: add input lifecycle regression coverage"
```

### Task 2: Implement shared input activation and routing components

**Files:**
- Create: `src/application/input/__init__.py`
- Create: `src/application/input/activation.py`
- Create: `src/application/input/state_transition_hotkeys.py`
- Create: `src/application/input/active_key_policy.py`
- Test: `tests/unit/test_input_activation.py`
- Test: `tests/unit/test_input_policies.py`

- [ ] **Step 1: Write the shared activation use case**

Create `src/application/input/activation.py`:

```python
from collections.abc import Callable

from adapters.inputs.base import HotkeyCapture, InputCapture


class InputActivationUseCase:
    def __init__(
        self,
        *,
        input_capture: InputCapture,
        hotkey_capture: HotkeyCapture,
        is_active: Callable[[], bool],
        set_active: Callable[[bool], None],
        notify_error: Callable[[str], None],
    ) -> None:
        self._input_capture = input_capture
        self._hotkey_capture = hotkey_capture
        self._is_active = is_active
        self._set_active = set_active
        self._notify_error = notify_error

    def enter_active(self) -> bool:
        if self._hotkey_capture.running:
            self._hotkey_capture.stop()
        try:
            if not self._input_capture.running:
                self._input_capture.start()
        except Exception as error:
            if not self._hotkey_capture.running:
                try:
                    self._hotkey_capture.start()
                except Exception:
                    pass
            self._notify_error(str(error))
            return False
        self._set_active(True)
        return True

    def exit_active(self) -> bool:
        if self._input_capture.running:
            self._input_capture.stop()
        try:
            if not self._hotkey_capture.running:
                self._hotkey_capture.start()
        except Exception as error:
            self._notify_error(str(error))
            return False
        self._set_active(False)
        return True
```

- [ ] **Step 2: Write the shared hotkey and active-key policies**

Create `src/application/input/state_transition_hotkeys.py`:

```python
from interop.key.key_event import KeyEvent


class StateTransitionHotkeyPolicy:
    def __init__(self, *, mapping: dict[int, str]) -> None:
        self._mapping = dict(mapping)

    def match(self, event: KeyEvent) -> str | None:
        if not event.pressed:
            return None
        return self._mapping.get(event.vk)
```

Create `src/application/input/active_key_policy.py`:

```python
from collections.abc import Callable

from adapters.inputs.base import KeyEventDecision
from interop.key.key_event import KeyEvent


class ActiveKeyEventPolicy:
    def __init__(
        self,
        *,
        exit_vk: int,
        on_exit: Callable[[], KeyEventDecision],
        on_key: Callable[[KeyEvent], KeyEventDecision],
    ) -> None:
        self._exit_vk = exit_vk
        self._on_exit = on_exit
        self._on_key = on_key

    def handle(self, event: KeyEvent) -> KeyEventDecision:
        if event.pressed and event.vk == self._exit_vk:
            return self._on_exit()
        return self._on_key(event)
```

Create `src/application/input/__init__.py`:

```python
from application.input.activation import InputActivationUseCase
from application.input.active_key_policy import ActiveKeyEventPolicy
from application.input.state_transition_hotkeys import StateTransitionHotkeyPolicy

__all__ = [
    "ActiveKeyEventPolicy",
    "InputActivationUseCase",
    "StateTransitionHotkeyPolicy",
]
```

- [ ] **Step 3: Run the new shared tests and verify they pass**

Run:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/unit/test_input_activation.py \
  tests/unit/test_input_policies.py -v
```

Expected:

- PASS for the new `application.input` unit tests
- app-level tests may still fail until the facades are rewired

- [ ] **Step 4: Commit**

```bash
git add \
  src/application/input/__init__.py \
  src/application/input/activation.py \
  src/application/input/state_transition_hotkeys.py \
  src/application/input/active_key_policy.py \
  tests/unit/test_input_activation.py \
  tests/unit/test_input_policies.py
git commit -m "feat: add shared input lifecycle components"
```

### Task 3: Rewire `nvda_remote` to the shared input lifecycle

**Files:**
- Modify: `src/apps/nvda_remote/facade.py`
- Modify: `src/apps/nvda_remote/use_cases/control_mode.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`

- [ ] **Step 1: Replace facade-owned hotkey toggling with shared components**

Update `src/apps/nvda_remote/facade.py` to compose the shared components:

```python
from application.input import (
    ActiveKeyEventPolicy,
    InputActivationUseCase,
    StateTransitionHotkeyPolicy,
)

# inside __init__
self._activation = InputActivationUseCase(
    input_capture=input_capture,
    hotkey_capture=hotkey_capture,
    is_active=lambda: self.state.control_state == ControlState.CONTROLLING,
    set_active=lambda active: setattr(
        self.state,
        "control_state",
        ControlState.CONTROLLING if active else ControlState.CONNECTED,
    ),
    notify_error=self._notify_error,
)
self._idle_hotkeys = StateTransitionHotkeyPolicy(mapping={0x7A: "enter_active"})
self._active_keys = ActiveKeyEventPolicy(
    exit_vk=0x7A,
    on_exit=lambda: self._exit_active_from_keyboard(),
    on_key=self._input_forwarding.handle,
)
```

Update the facade entry points:

```python
def bind(self) -> None:
    self.input_capture.set_listener(self.handle_key_event)
    self.hotkey_capture.set_handler(self._handle_idle_hotkey)
    self.transport.set_message_handler(self._handle_transport_message)


def handle_key_event(self, event: KeyEvent) -> KeyEventDecision:
    if self.state.control_state != ControlState.CONTROLLING:
        return KeyEventDecision.PASS_THROUGH
    return self._active_keys.handle(event)
```

- [ ] **Step 2: Adjust control mode use case to stop owning capture state transitions**

Update `src/apps/nvda_remote/use_cases/control_mode.py` so it owns business state and status reporting, not capture toggling:

```python
class NvdaRemoteControlModeUseCase:
    def __init__(
        self,
        *,
        state: RuntimeState,
        notify_error: Callable[[str], None],
        notify_status: Callable[[dict[str, str]], None],
    ) -> None:
        self._state = state
        self._notify_error = notify_error
        self._notify_status = notify_status

    def start_control(self) -> None:
        if self._state.connection_state == ConnectionState.IDLE:
            self._notify_error("Not connected")
            return
        self._state.control_state = ControlState.CONTROLLING
        self._notify_status({"kind": "control", "state": ControlState.CONTROLLING.value})

    def stop_control(self) -> None:
        self._state.control_state = ControlState.CONNECTED
        self._notify_status({"kind": "control", "state": ControlState.CONNECTED.value})
```

- [ ] **Step 3: Run the `nvda_remote` tests**

Run:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/unit/test_input_activation.py \
  tests/unit/test_input_policies.py \
  tests/unit/test_nvda_remote_app_service.py -v
```

Expected:

- PASS for the shared tests
- PASS for idle `F11` and active `F11` routing in `nvda_remote`

- [ ] **Step 4: Commit**

```bash
git add \
  src/apps/nvda_remote/facade.py \
  src/apps/nvda_remote/use_cases/control_mode.py \
  tests/unit/test_nvda_remote_app_service.py
git commit -m "refactor: route nvda remote through shared input lifecycle"
```

### Task 4: Rewire `key_echo` to `idle hotkey / active keyboard`

**Files:**
- Modify: `src/apps/key_echo/facade.py`
- Modify: `src/apps/key_echo/main.py`
- Modify: `src/apps/key_echo/use_cases/echo_control.py`
- Modify: `tests/unit/test_key_echo_app_service.py`

- [ ] **Step 1: Add hotkey capture to `key_echo` runtime and facade**

Update `src/apps/key_echo/main.py`:

```python
from adapters.inputs.base import HotkeyCapture, InputCapture
from bootstrap.platform import create_hotkey_capture, create_input_capture


@dataclass(frozen=True)
class KeyEchoRuntime:
    input_capture: InputCapture
    hotkey_capture: HotkeyCapture
    output_scheduler: OutputScheduler
    speech_service: SpeechService
    output_service: QueuedOutputService
    input_service: KeyboardInputService
    app_service: KeyEchoAppFacade
    app: Any


input_capture = create_input_capture()
hotkey_capture = create_hotkey_capture()
app_service = KeyEchoAppFacade(
    hotkey_capture=hotkey_capture,
    outputs=OutputCapabilities(speech=output_service),
)
input_service = KeyboardInputService(input_capture, app_service)
app_service.attach_input_service(input_service)
app_service.bind()
hotkey_capture.start()
```

Update `src/apps/key_echo/facade.py` constructor shape:

```python
class KeyEchoAppFacade(KeyEventHandler):
    def __init__(self, *, hotkey_capture: HotkeyCapture, outputs: OutputCapabilities) -> None:
        self.hotkey_capture = hotkey_capture
        ...
```

- [ ] **Step 2: Rework `key_echo` active/idle behavior around shared policies**

Update `src/apps/key_echo/facade.py`:

```python
from application.input import (
    ActiveKeyEventPolicy,
    InputActivationUseCase,
    StateTransitionHotkeyPolicy,
)

self._activation = InputActivationUseCase(
    input_capture=input_service._capture,
    hotkey_capture=hotkey_capture,
    is_active=self.is_echo_running,
    set_active=lambda active: None,
    notify_error=lambda message: self._notify_status_listener({"kind": "error", "message": message}),
)
self._idle_hotkeys = StateTransitionHotkeyPolicy(mapping={0x0D: "enter_active"})
self._active_keys = ActiveKeyEventPolicy(
    exit_vk=0x1B,
    on_exit=lambda: self._stop_active_echo(),
    on_key=self._echo_input.handle,
)

def bind(self) -> None:
    self.hotkey_capture.set_handler(self._handle_idle_hotkey)

def handle_key_event(self, event: KeyEvent) -> KeyEventDecision:
    if not self.is_echo_running():
        return KeyEventDecision.PASS_THROUGH
    return self._active_keys.handle(event)
```

Update `src/apps/key_echo/use_cases/echo_control.py` back toward echo-state ownership only:

```python
class KeyEchoControlUseCase:
    def start_echo(self) -> None:
        self._echo_active = True
        self._notify_status({"kind": "echo", "state": "running"})

    def stop_echo(self) -> None:
        self._echo_active = False
        self._notify_status({"kind": "echo", "state": "stopped"})
```

- [ ] **Step 3: Run the `key_echo` tests**

Run:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/unit/test_input_activation.py \
  tests/unit/test_input_policies.py \
  tests/unit/test_key_echo_app_service.py -v
```

Expected:

- PASS for idle `Enter` through `HotkeyCapture`
- PASS for active `Escape` through keyboard input
- PASS for normal active echo playback

- [ ] **Step 4: Commit**

```bash
git add \
  src/apps/key_echo/facade.py \
  src/apps/key_echo/main.py \
  src/apps/key_echo/use_cases/echo_control.py \
  tests/unit/test_key_echo_app_service.py
git commit -m "refactor: unify key echo input lifecycle"
```

### Task 5: Verify runtime wiring, teardown, and full regression coverage

**Files:**
- Modify: `tests/unit/test_app_wx.py`
- Modify: `tests/unit/test_key_echo_app_service.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`

- [ ] **Step 1: Add runtime wiring and shutdown coverage**

Add to `tests/unit/test_app_wx.py`:

```python
def test_key_echo_build_runtime_starts_in_idle_mode(monkeypatch):
    runtime = main_module.build_runtime()

    assert runtime.hotkey_capture.running is True
    assert runtime.input_capture.running is False


def test_key_echo_shutdown_stops_both_capture_paths(monkeypatch):
    runtime = main_module.build_runtime()
    runtime.app_service.start_echo()
    runtime.app_service.shutdown()

    assert runtime.hotkey_capture.running is False
    assert runtime.input_capture.running is False
```

- [ ] **Step 2: Run targeted runtime and wx tests**

Run:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/unit/test_app_wx.py \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_key_echo_app_service.py -v
```

Expected:

- PASS for runtime idle-mode ownership
- PASS for shutdown teardown
- PASS for both app-specific lifecycle behaviors

- [ ] **Step 3: Run the full suite**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/unit tests/integration -v
```

Expected:

- PASS for the entire suite with no regressions

- [ ] **Step 4: Commit**

```bash
git add \
  tests/unit/test_app_wx.py \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_key_echo_app_service.py
git commit -m "test: verify unified input runtime wiring"
```

## Self-Review

- **Spec coverage:** This plan covers shared lifecycle extraction, idle hotkey policy, active key routing, `nvda_remote` rewiring, `key_echo` hotkey introduction, shutdown coverage, and rollback tests. No spec requirement is intentionally deferred.
- **Placeholder scan:** No `TODO`, `TBD`, or “similar to” placeholders remain. Each task includes paths, code, commands, and expected results.
- **Type consistency:** The plan consistently uses `InputActivationUseCase`, `StateTransitionHotkeyPolicy`, `ActiveKeyEventPolicy`, `HotkeyCapture`, and `InputCapture` across tests and implementation tasks.

