# Keyboard Pipeline Decision Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current lossy keyboard decision enum model with a structured keyboard pipeline result, while making Windows `Num Lock` in `key_echo` both pass through to the system and still execute app behavior.

**Architecture:** Introduce two new core result types: `AppKeyEventResult` for app-internal handler flow and `KeyboardPipelineResult` for the capture/app boundary. Keep a three-stage pipeline in `key_echo`: fixed system pass-through policy, mode handling, and final result assembly. Adapt capture adapters to read only `send_to_system`, and keep `nvda_remote` behavior unchanged beyond interface compatibility.

**Tech Stack:** Python, pytest, dataclasses, enums, existing `CapturedKeyEvent`/keyboard hook adapters on Windows and macOS.

---

## File Map

- Create: `src/application/input/results.py`
  - Defines `AppKeyEventResult` and `KeyboardPipelineResult`.
- Create: `src/application/input/keyboard_pipeline.py`
  - Hosts decision assembly helpers for combining `send_to_system` with `AppKeyEventResult`.
- Modify: `src/adapters/inputs/base.py`
  - Change `InputCapture.set_listener()` contract to return `KeyboardPipelineResult`.
- Modify: `src/application/input/__init__.py`
  - Export the new result types and pipeline helpers.
- Modify: `src/application/input/active_key_policy.py`
  - Return `AppKeyEventResult` instead of `KeyEventDecision`.
- Modify: `src/apps/shared/mode_manager.py`
  - Return `AppKeyEventResult` instead of `KeyEventDecision`.
- Modify: `src/apps/key_echo/use_cases/echo_input.py`
  - Return `HANDLED_STOP` for normal keys and `HANDLED_CONTINUE` for Windows `Num Lock`.
- Modify: `src/apps/key_echo/service.py`
  - Run the three-stage keyboard pipeline and return `KeyboardPipelineResult`.
- Modify: `src/apps/nvda_remote/service.py`
  - Adapt `handle_key_event()` to return `KeyboardPipelineResult` while preserving current behavior.
- Modify: `src/adapters/windows/keyboard_hook.py`
  - Read `KeyboardPipelineResult.send_to_system`.
- Modify: `src/adapters/macos/keyboard_hook.py`
  - Read `KeyboardPipelineResult.send_to_system`.
- Test: `tests/unit/test_key_echo_use_cases.py`
  - Update for new `AppKeyEventResult`.
- Test: `tests/unit/test_key_echo_app_service.py`
  - Cover `KeyboardPipelineResult` and Windows `Num Lock` pass-through + app handling.
- Test: `tests/unit/test_nvda_remote_app_service.py`
  - Cover interface compatibility under the new return type.
- Test: `tests/unit/test_windows_adapters.py`
  - Verify Windows adapter suppress/pass-through behavior uses `send_to_system`.
- Test: `tests/unit/test_macos_adapters.py`
  - Verify macOS adapter suppress/pass-through behavior uses `send_to_system`.
- Test: `tests/unit/test_mode_manager.py`
  - Add/adjust tests for `AppKeyEventResult`.
- Test: `tests/unit/test_active_key_policy.py`
  - Add/adjust tests for `AppKeyEventResult`.

### Task 1: Add Core Pipeline Result Types

**Files:**
- Create: `src/application/input/results.py`
- Modify: `src/application/input/__init__.py`
- Test: `tests/unit/test_keyboard_pipeline_results.py`

- [ ] **Step 1: Write the failing test**

```python
from application.input.results import AppKeyEventResult, KeyboardPipelineResult


def test_keyboard_pipeline_result_preserves_both_dimensions():
    result = KeyboardPipelineResult(
        send_to_system=True,
        app_result=AppKeyEventResult.HANDLED_CONTINUE,
    )

    assert result.send_to_system is True
    assert result.app_result is AppKeyEventResult.HANDLED_CONTINUE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_keyboard_pipeline_results.py::test_keyboard_pipeline_result_preserves_both_dimensions -v`
Expected: FAIL with `ModuleNotFoundError` or missing `results.py`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/application/input/results.py
from dataclasses import dataclass
from enum import StrEnum


class AppKeyEventResult(StrEnum):
    UNHANDLED = "unhandled"
    HANDLED_CONTINUE = "handled_continue"
    HANDLED_STOP = "handled_stop"


@dataclass(frozen=True)
class KeyboardPipelineResult:
    send_to_system: bool
    app_result: AppKeyEventResult
```

```python
# src/application/input/__init__.py
from application.input.activation import InputActivationUseCase
from application.input.active_key_policy import ActiveKeyEventPolicy
from application.input.results import AppKeyEventResult, KeyboardPipelineResult
from application.input.system_toggle_policy import should_pass_through_system_toggle

__all__ = [
    "ActiveKeyEventPolicy",
    "AppKeyEventResult",
    "InputActivationUseCase",
    "KeyboardPipelineResult",
    "should_pass_through_system_toggle",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_keyboard_pipeline_results.py::test_keyboard_pipeline_result_preserves_both_dimensions -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/application/input/results.py src/application/input/__init__.py tests/unit/test_keyboard_pipeline_results.py
git commit -m "feat: add keyboard pipeline result types"
```

### Task 2: Add Pipeline Assembly Helper

**Files:**
- Create: `src/application/input/keyboard_pipeline.py`
- Modify: `src/application/input/__init__.py`
- Test: `tests/unit/test_keyboard_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
from application.input.keyboard_pipeline import assemble_pipeline_result
from application.input.results import AppKeyEventResult, KeyboardPipelineResult


def test_assemble_pipeline_result_keeps_send_to_system_and_app_result():
    result = assemble_pipeline_result(
        send_to_system=True,
        app_result=AppKeyEventResult.HANDLED_CONTINUE,
    )

    assert result == KeyboardPipelineResult(
        send_to_system=True,
        app_result=AppKeyEventResult.HANDLED_CONTINUE,
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_keyboard_pipeline.py::test_assemble_pipeline_result_keeps_send_to_system_and_app_result -v`
Expected: FAIL with missing `keyboard_pipeline.py` or missing function.

- [ ] **Step 3: Write minimal implementation**

```python
# src/application/input/keyboard_pipeline.py
from application.input.results import AppKeyEventResult, KeyboardPipelineResult


def assemble_pipeline_result(
    *,
    send_to_system: bool,
    app_result: AppKeyEventResult,
) -> KeyboardPipelineResult:
    return KeyboardPipelineResult(
        send_to_system=send_to_system,
        app_result=app_result,
    )
```

```python
# src/application/input/__init__.py
from application.input.keyboard_pipeline import assemble_pipeline_result

__all__ = [
    "ActiveKeyEventPolicy",
    "AppKeyEventResult",
    "InputActivationUseCase",
    "KeyboardPipelineResult",
    "assemble_pipeline_result",
    "should_pass_through_system_toggle",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_keyboard_pipeline.py::test_assemble_pipeline_result_keeps_send_to_system_and_app_result -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/application/input/keyboard_pipeline.py src/application/input/__init__.py tests/unit/test_keyboard_pipeline.py
git commit -m "feat: add keyboard pipeline assembly helper"
```

### Task 3: Convert ActiveKeyEventPolicy and ModeManager to AppKeyEventResult

**Files:**
- Modify: `src/application/input/active_key_policy.py`
- Modify: `src/apps/shared/mode_manager.py`
- Test: `tests/unit/test_active_key_policy.py`
- Test: `tests/unit/test_mode_manager.py`

- [ ] **Step 1: Write the failing tests**

```python
from application.input.active_key_policy import ActiveKeyEventPolicy
from application.input.results import AppKeyEventResult
from interop.key import HID, KeyEvent


def test_active_key_policy_returns_unhandled_when_on_key_does_not_handle():
    policy = ActiveKeyEventPolicy(
        exit_usage=HID.ESCAPE,
        on_exit=lambda: AppKeyEventResult.HANDLED_STOP,
        on_key=lambda _event: AppKeyEventResult.UNHANDLED,
    )

    result = policy.handle(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    )

    assert result is AppKeyEventResult.UNHANDLED
```

```python
from application.input.results import AppKeyEventResult


def test_mode_manager_returns_unhandled_when_no_mode_is_active():
    manager = ModeManager(
        activation=FakeActivation(),
        notify_status=lambda _status: None,
    )

    result = manager.handle_key_event(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    )

    assert result is AppKeyEventResult.UNHANDLED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_active_key_policy.py::test_active_key_policy_returns_unhandled_when_on_key_does_not_handle tests/unit/test_mode_manager.py::test_mode_manager_returns_unhandled_when_no_mode_is_active -v`
Expected: FAIL because the code still returns `KeyEventDecision`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/application/input/active_key_policy.py
from collections.abc import Callable

from application.input.results import AppKeyEventResult
from interop.key.key_event import KeyEvent


class ActiveKeyEventPolicy:
    def __init__(
        self,
        *,
        exit_usage: int,
        on_exit: Callable[[], AppKeyEventResult],
        on_key: Callable[[KeyEvent], AppKeyEventResult],
    ) -> None:
        self._exit_usage = exit_usage
        self._on_exit = on_exit
        self._on_key = on_key

    def handle(self, event: KeyEvent) -> AppKeyEventResult:
        if event.pressed and event.usage == self._exit_usage:
            return self._on_exit()
        return self._on_key(event)
```

```python
# src/apps/shared/mode_manager.py
from collections.abc import Callable
from typing import Any

from application.input.results import AppKeyEventResult
from interop.key.key_event import KeyEvent


class ModeManager:
    ...

    def exit_active_mode(self) -> AppKeyEventResult:
        if self.active_mode_id is None:
            return AppKeyEventResult.UNHANDLED
        ...
        if not self._activation.exit_active():
            return AppKeyEventResult.HANDLED_STOP
        ...
        return AppKeyEventResult.HANDLED_STOP

    def handle_key_event(self, event: KeyEvent) -> AppKeyEventResult:
        if self.active_mode_id is None:
            return AppKeyEventResult.UNHANDLED
        ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_active_key_policy.py tests/unit/test_mode_manager.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/application/input/active_key_policy.py src/apps/shared/mode_manager.py tests/unit/test_active_key_policy.py tests/unit/test_mode_manager.py
git commit -m "refactor: return app key event results from policies"
```

### Task 4: Update KeyEchoInputUseCase to AppKeyEventResult

**Files:**
- Modify: `src/apps/key_echo/use_cases/echo_input.py`
- Test: `tests/unit/test_key_echo_use_cases.py`

- [ ] **Step 1: Write the failing tests**

```python
from application.input.results import AppKeyEventResult
from interop.key import HID, KeyEvent


def test_echo_input_use_case_returns_handled_stop_for_regular_keys():
    use_case = KeyEchoInputUseCase(cancel=lambda: None, speak=lambda _sequence: None)

    result = use_case.handle(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    )

    assert result is AppKeyEventResult.HANDLED_STOP


def test_echo_input_use_case_returns_handled_continue_for_num_lock():
    use_case = KeyEchoInputUseCase(cancel=lambda: None, speak=lambda _sequence: None)

    result = use_case.handle(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.NUM_LOCK, pressed=True)
    )

    assert result is AppKeyEventResult.HANDLED_CONTINUE
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_key_echo_use_cases.py -q`
Expected: FAIL because the use case still returns `KeyEventDecision`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/apps/key_echo/use_cases/echo_input.py
from collections.abc import Callable

from application.input.results import AppKeyEventResult
from interop.key import HID
from interop.key.key_event import KeyEvent
from interop.speech.speech_sequence import SpeechSequence


class KeyEchoInputUseCase:
    ...

    def handle(self, event: KeyEvent) -> AppKeyEventResult:
        if event.pressed:
            self._cancel()
            self._speak(
                SpeechSequence(
                    items=(f"HID 0x{event.usage_page:02X}:0x{event.usage:02X}",)
                )
            )
        if event.usage == HID.NUM_LOCK:
            return AppKeyEventResult.HANDLED_CONTINUE
        return AppKeyEventResult.HANDLED_STOP
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_key_echo_use_cases.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/key_echo/use_cases/echo_input.py tests/unit/test_key_echo_use_cases.py
git commit -m "refactor: return app results from key echo input use case"
```

### Task 5: Switch InputCapture and Adapters to KeyboardPipelineResult

**Files:**
- Modify: `src/adapters/inputs/base.py`
- Modify: `src/adapters/windows/keyboard_hook.py`
- Modify: `src/adapters/macos/keyboard_hook.py`
- Test: `tests/unit/test_windows_adapters.py`
- Test: `tests/unit/test_macos_adapters.py`

- [ ] **Step 1: Write the failing tests**

```python
from application.input.results import AppKeyEventResult, KeyboardPipelineResult


def test_windows_keyboard_hook_passes_event_when_listener_requests_send_to_system():
    capture = WindowsKeyboardCapture(user32=FakeUser32(), kernel32=FakeKernel32(), is_windows=True)
    capture.set_listener(
        lambda _event: KeyboardPipelineResult(
            send_to_system=True,
            app_result=AppKeyEventResult.HANDLED_CONTINUE,
        )
    )

    decision = capture._emit_for_tests(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True),
        0x41,
        30,
        False,
    )

    assert decision.send_to_system is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_windows_adapters.py tests/unit/test_macos_adapters.py -q`
Expected: FAIL because adapters still expect `KeyEventDecision`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/adapters/inputs/base.py
from collections.abc import Callable
from typing import Protocol

from adapters.inputs.captured_event import CapturedKeyEvent
from application.input.results import KeyboardPipelineResult


class InputCapture(Protocol):
    @property
    def running(self) -> bool: ...

    def set_listener(
        self,
        listener: Callable[[CapturedKeyEvent], KeyboardPipelineResult],
    ) -> None: ...
```

```python
# src/adapters/windows/keyboard_hook.py
from application.input.results import AppKeyEventResult, KeyboardPipelineResult
...
        self._listener: Callable[[CapturedKeyEvent], KeyboardPipelineResult] | None = None
...
            result = self._emit_for_tests(event, vk_code, scan_code, extended)
            if not result.send_to_system:
                return 1
...
    def _emit_for_tests(...) -> KeyboardPipelineResult:
        if event is None or self._listener is None:
            return KeyboardPipelineResult(
                send_to_system=True,
                app_result=AppKeyEventResult.UNHANDLED,
            )
        return self._listener(...)
```

```python
# src/adapters/macos/keyboard_hook.py
from application.input.results import AppKeyEventResult, KeyboardPipelineResult
...
        if self._listener is None:
            return KeyboardPipelineResult(
                send_to_system=True,
                app_result=AppKeyEventResult.UNHANDLED,
            )
...
        if key_event is None:
            return KeyboardPipelineResult(
                send_to_system=True,
                app_result=AppKeyEventResult.UNHANDLED,
            )
        return self._listener(...)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_windows_adapters.py tests/unit/test_macos_adapters.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/inputs/base.py src/adapters/windows/keyboard_hook.py src/adapters/macos/keyboard_hook.py tests/unit/test_windows_adapters.py tests/unit/test_macos_adapters.py
git commit -m "refactor: switch keyboard captures to pipeline result"
```

### Task 6: Implement KeyEcho Pipeline in App Service

**Files:**
- Modify: `src/apps/key_echo/service.py`
- Modify: `src/application/input/system_toggle_policy.py`
- Test: `tests/unit/test_key_echo_app_service.py`

- [ ] **Step 1: Write the failing tests**

```python
from application.input.results import AppKeyEventResult, KeyboardPipelineResult


def test_key_echo_app_service_returns_pipeline_result_for_regular_key():
    ...
    result = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True),
            native_context=None,
        )
    )

    assert result == KeyboardPipelineResult(
        send_to_system=False,
        app_result=AppKeyEventResult.HANDLED_STOP,
    )


def test_key_echo_app_service_returns_pipeline_result_for_windows_num_lock():
    ...
    result = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.NUM_LOCK, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x90, scan_code=69, extended=True),
        )
    )

    assert result == KeyboardPipelineResult(
        send_to_system=True,
        app_result=AppKeyEventResult.HANDLED_CONTINUE,
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_key_echo_app_service.py -q`
Expected: FAIL because `KeyEchoAppService.handle_key_event()` still returns `KeyEventDecision`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/application/input/system_toggle_policy.py
from adapters.inputs.captured_event import CapturedKeyEvent
from adapters.windows.native_key_context import WindowsNativeKeyContext
from interop.key import HID


def should_pass_through_system_toggle(event: CapturedKeyEvent) -> bool:
    return (
        event.key_event.usage == HID.NUM_LOCK
        and isinstance(event.native_context, WindowsNativeKeyContext)
    )
```

```python
# src/apps/key_echo/service.py
from application.input import assemble_pipeline_result
...
    def handle_key_event(self, event: CapturedKeyEvent) -> KeyboardPipelineResult:
        send_to_system = should_pass_through_system_toggle(event)
        app_result = self._mode_manager.handle_key_event(event.key_event)
        return assemble_pipeline_result(
            send_to_system=send_to_system,
            app_result=app_result,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_key_echo_app_service.py tests/unit/test_key_echo_use_cases.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/key_echo/service.py src/application/input/system_toggle_policy.py tests/unit/test_key_echo_app_service.py tests/unit/test_key_echo_use_cases.py
git commit -m "feat: add key echo keyboard pipeline"
```

### Task 7: Adapt NvdaRemote Service for Interface Compatibility

**Files:**
- Modify: `src/apps/nvda_remote/service.py`
- Test: `tests/unit/test_nvda_remote_app_service.py`

- [ ] **Step 1: Write the failing test**

```python
from application.input.results import AppKeyEventResult, KeyboardPipelineResult


def test_nvda_remote_service_returns_pipeline_result_while_controlling():
    service, transport, capture, hotkey, _dispatch_calls = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.start_control()

    result = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True),
            native_context=None,
        )
    )

    assert result == KeyboardPipelineResult(
        send_to_system=False,
        app_result=AppKeyEventResult.HANDLED_STOP,
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_nvda_remote_app_service.py::test_nvda_remote_service_returns_pipeline_result_while_controlling -v`
Expected: FAIL because the service still returns `KeyEventDecision`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/apps/nvda_remote/service.py
from application.input import assemble_pipeline_result
from application.input.results import AppKeyEventResult, KeyboardPipelineResult
...
    def handle_key_event(self, event: CapturedKeyEvent) -> KeyboardPipelineResult:
        key_event = event.key_event
        if not key_event.pressed and key_event.usage in self._suppressed_keyups:
            self._suppressed_keyups.discard(key_event.usage)
            return assemble_pipeline_result(
                send_to_system=False,
                app_result=AppKeyEventResult.HANDLED_STOP,
            )
        ...
        if self.state.control_state == ControlState.CONTROLLING:
            decision = self._input_forwarding.handle(event)
            return assemble_pipeline_result(
                send_to_system=(decision == KeyEventDecision.PASS_THROUGH),
                app_result=AppKeyEventResult.HANDLED_STOP,
            )
        return assemble_pipeline_result(
            send_to_system=True,
            app_result=AppKeyEventResult.UNHANDLED,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_nvda_remote_app_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/nvda_remote/service.py tests/unit/test_nvda_remote_app_service.py
git commit -m "refactor: adapt nvda remote service to pipeline result"
```

### Task 8: Run Integration-Level Regression Checks

**Files:**
- No new production files
- Verify: `tests/unit/test_key_echo_use_cases.py`
- Verify: `tests/unit/test_key_echo_app_service.py`
- Verify: `tests/unit/test_nvda_remote_app_service.py`
- Verify: `tests/unit/test_windows_adapters.py`
- Verify: `tests/unit/test_macos_adapters.py`
- Verify: `tests/unit/test_mode_manager.py`
- Verify: `tests/unit/test_active_key_policy.py`

- [ ] **Step 1: Run focused regression suite**

Run:

```bash
pytest \
  tests/unit/test_keyboard_pipeline_results.py \
  tests/unit/test_keyboard_pipeline.py \
  tests/unit/test_active_key_policy.py \
  tests/unit/test_mode_manager.py \
  tests/unit/test_key_echo_use_cases.py \
  tests/unit/test_key_echo_app_service.py \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_windows_adapters.py \
  tests/unit/test_macos_adapters.py -q
```

Expected: PASS for all targeted tests.

- [ ] **Step 2: Run broader unit suite**

Run: `pytest tests/unit -q`
Expected: PASS with no regressions introduced by the new result model.

- [ ] **Step 3: Commit final cleanup**

```bash
git add -A
git commit -m "test: verify keyboard pipeline decision model refactor"
```

## Self-Review

- Spec coverage:
  - `AppKeyEventResult`: Task 1 + Task 3 + Task 4
  - `KeyboardPipelineResult`: Task 1 + Task 2 + Task 5 + Task 6 + Task 7
  - three-stage pipeline: Task 2 + Task 6
  - `key_echo` Windows `Num Lock`: Task 4 + Task 6
  - `nvda_remote` interface compatibility only: Task 7
  - adapters using only `send_to_system`: Task 5
- Placeholder scan:
  - no `TODO`, `TBD`, or "similar to"
- Type consistency:
  - final boundary type is `KeyboardPipelineResult`
  - app-internal result type is `AppKeyEventResult`
  - `KeyEventDecision` remains only as a temporary compatibility bridge inside `nvda_remote` forwarding in Task 7
