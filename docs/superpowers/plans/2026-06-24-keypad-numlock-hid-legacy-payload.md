# Keypad NumLock HID Legacy Payload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `HID + num_lock_on` to Windows-style remote payload conversion for `nvda_remote`, with Windows defaulting to HID conversion and an explicit native payload compatibility switch.

**Architecture:** `CapturedKeyEvent` carries optional NumLock state alongside the existing HID `KeyEvent`. The payload converter stays pure and maps HID usages plus `num_lock_on` into `vk_code`, `scan_code`, and `extended`; the bridge only chooses between default HID conversion and the explicit Windows native compatibility path. `NvdaRemoteAppService` handles NumLock as a special `forward + pass-through` key while controlling.

**Tech Stack:** Python dataclasses, pytest, existing `src` layout, existing `KeyboardPipelineResult` and `RemoteMessageType.KEY` transport payloads.

---

## File Structure

- Modify `src/adapters/inputs/captured_event.py`: add `num_lock_on: bool | None = None` to the captured event envelope.
- Modify `src/adapters/windows/keyboard_hook.py`: read `GetKeyState(VK_NUMLOCK)` and place the boolean on emitted `CapturedKeyEvent`.
- Modify `src/apps/nvda_remote/legacy_key_payload.py`: accept `num_lock_on` and implement complete keypad mapping.
- Modify `src/apps/nvda_remote/legacy_key_payload_bridge.py`: add `use_windows_native_key_payload` switch and default to HID conversion.
- Modify `src/apps/nvda_remote/use_cases/input_forwarding.py`: pass the bridge mode switch through from the use case.
- Modify `src/apps/nvda_remote/service.py`: accept/configure the Windows native payload switch and route `HID.NUM_LOCK` through `forward + pass-through` while controlling.
- Modify `tests/unit/test_windows_adapters.py`: assert Windows capture emits `num_lock_on`.
- Modify `tests/unit/test_nvda_remote_legacy_key_payload.py`: cover keypad mappings for `num_lock_on=True`, `False`, and `None`.
- Modify `tests/unit/test_nvda_remote_legacy_key_payload_bridge.py`: cover default HID conversion and native compatibility mode.
- Review `tests/unit/test_nvda_remote_use_cases.py`: existing forwarding tests should continue to pass after the constructor gains the bridge mode parameter.
- Modify `tests/unit/test_nvda_remote_app_service.py`: cover NumLock `forward + pass-through` behavior and service constructor switch wiring.

## Task 1: Add NumLock State To Captured Events

**Files:**
- Modify: `src/adapters/inputs/captured_event.py`
- Test: `tests/unit/test_windows_adapters.py`

- [ ] **Step 1: Write the failing Windows capture test**

Add this test near the existing Windows hook tests in `tests/unit/test_windows_adapters.py`:

```python
class FakeKeyboardUser32WithNumLock(FakeKeyboardUser32):
    def __init__(self, *, num_lock_on: bool):
        super().__init__()
        self.num_lock_on = num_lock_on

    def GetKeyState(self, _vk_code):
        return 1 if self.num_lock_on else 0


def test_windows_keyboard_hook_emits_num_lock_state_on_captured_event():
    user32 = FakeKeyboardUser32WithNumLock(num_lock_on=False)
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]
    key_data = FakeKbdLlHookStruct(vkCode=0x62, scanCode=80, flags=0)

    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_2, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x62, scan_code=80, extended=False),
            num_lock_on=False,
        ),
    ]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/unit/test_windows_adapters.py::test_windows_keyboard_hook_emits_num_lock_state_on_captured_event -v`

Expected: FAIL because `CapturedKeyEvent` does not accept or compare `num_lock_on`.

- [ ] **Step 3: Add the field to `CapturedKeyEvent`**

Replace `src/adapters/inputs/captured_event.py` with:

```python
from dataclasses import dataclass

from interop.key.key_event import KeyEvent


@dataclass(frozen=True)
class CapturedKeyEvent:
    key_event: KeyEvent
    native_context: object | None = None
    num_lock_on: bool | None = None
```

- [ ] **Step 4: Fill `num_lock_on` in Windows capture**

In `src/adapters/windows/keyboard_hook.py`, update `_emit_for_tests` to accept `num_lock_on`:

```python
    def _emit_for_tests(
        self,
        event: KeyEvent | None,
        vk_code: int,
        scan_code: int,
        extended: bool,
        num_lock_on: bool | None,
    ) -> KeyboardPipelineResult:
        if event is None or self._listener is None:
            return KeyboardPipelineResult(send_to_system=True, app_result=AppKeyEventResult.UNHANDLED)
        return self._listener(
            CapturedKeyEvent(
                key_event=event,
                native_context=WindowsNativeKeyContext(
                    vk_code=vk_code,
                    scan_code=scan_code,
                    extended=extended,
                ),
                num_lock_on=num_lock_on,
            )
        )
```

Then update the call site in `_handle_keyboard_event`:

```python
            result = self._emit_for_tests(event, vk_code, scan_code, extended, num_lock_on)
```

- [ ] **Step 5: Run the focused test**

Run: `pytest tests/unit/test_windows_adapters.py::test_windows_keyboard_hook_emits_num_lock_state_on_captured_event -v`

Expected: PASS.

- [ ] **Step 6: Run Windows adapter tests**

Run: `pytest tests/unit/test_windows_adapters.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/adapters/inputs/captured_event.py src/adapters/windows/keyboard_hook.py tests/unit/test_windows_adapters.py
git commit -m "feat: capture numlock state with key events"
```

## Task 2: Implement HID Plus NumLock Payload Mapping

**Files:**
- Modify: `src/apps/nvda_remote/legacy_key_payload.py`
- Test: `tests/unit/test_nvda_remote_legacy_key_payload.py`

- [ ] **Step 1: Write failing tests for keypad NumLock mappings**

Add this block to `tests/unit/test_nvda_remote_legacy_key_payload.py`:

```python
import pytest
```

If the file already has imports, place `import pytest` above project imports.

Add these tests after the existing keypad tests:

```python
@pytest.mark.parametrize(
    ("usage", "expected_on", "expected_off"),
    [
        (HID.KEYPAD_0, (0x60, 82, False), (0x2D, 82, False)),
        (HID.KEYPAD_1, (0x61, 79, False), (0x23, 79, False)),
        (HID.KEYPAD_2, (0x62, 80, False), (0x28, 80, False)),
        (HID.KEYPAD_3, (0x63, 81, False), (0x22, 81, False)),
        (HID.KEYPAD_4, (0x64, 75, False), (0x25, 75, False)),
        (HID.KEYPAD_5, (0x65, 76, False), (0x0C, 76, False)),
        (HID.KEYPAD_6, (0x66, 77, False), (0x27, 77, False)),
        (HID.KEYPAD_7, (0x67, 71, False), (0x24, 71, False)),
        (HID.KEYPAD_8, (0x68, 72, False), (0x26, 72, False)),
        (HID.KEYPAD_9, (0x69, 73, False), (0x21, 73, False)),
        (HID.KEYPAD_DECIMAL, (0x6E, 83, False), (0x2E, 83, False)),
    ],
)
def test_keypad_numeric_keys_map_by_num_lock_state(usage, expected_on, expected_off):
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=True)

    assert key_event_to_legacy_remote_payload(event, num_lock_on=True) == {
        "vk_code": expected_on[0],
        "scan_code": expected_on[1],
        "extended": expected_on[2],
        "pressed": True,
    }
    assert key_event_to_legacy_remote_payload(event, num_lock_on=False) == {
        "vk_code": expected_off[0],
        "scan_code": expected_off[1],
        "extended": expected_off[2],
        "pressed": True,
    }


@pytest.mark.parametrize(
    ("usage", "expected"),
    [
        (HID.KEYPAD_DIVIDE, (0x6F, 53, True)),
        (HID.KEYPAD_MULTIPLY, (0x6A, 55, False)),
        (HID.KEYPAD_SUBTRACT, (0x6D, 74, False)),
        (HID.KEYPAD_ADD, (0x6B, 78, False)),
        (HID.KEYPAD_ENTER, (0x0D, 28, True)),
        (HID.KEYPAD_EQUALS, (0xBB, 89, False)),
    ],
)
def test_keypad_operator_keys_ignore_num_lock_state(usage, expected):
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=False)

    assert key_event_to_legacy_remote_payload(event, num_lock_on=True) == {
        "vk_code": expected[0],
        "scan_code": expected[1],
        "extended": expected[2],
        "pressed": False,
    }
    assert key_event_to_legacy_remote_payload(event, num_lock_on=False) == {
        "vk_code": expected[0],
        "scan_code": expected[1],
        "extended": expected[2],
        "pressed": False,
    }


def test_keypad_num_lock_none_preserves_existing_mapping():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_2, pressed=True)

    assert key_event_to_legacy_remote_payload(event, num_lock_on=None) == {
        "vk_code": 0x62,
        "scan_code": 80,
        "extended": False,
        "pressed": True,
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_nvda_remote_legacy_key_payload.py -v`

Expected: FAIL with `TypeError` because `key_event_to_legacy_remote_payload()` does not accept `num_lock_on`.

- [ ] **Step 3: Implement mapping tables and signature**

In `src/apps/nvda_remote/legacy_key_payload.py`, add this table after `_USAGE_TO_LEGACY`:

```python
_KEYPAD_NUM_LOCK_OFF_TO_LEGACY: dict[int, tuple[int, int, bool]] = {
    HID.KEYPAD_0: (0x2D, 82, False),
    HID.KEYPAD_1: (0x23, 79, False),
    HID.KEYPAD_2: (0x28, 80, False),
    HID.KEYPAD_3: (0x22, 81, False),
    HID.KEYPAD_4: (0x25, 75, False),
    HID.KEYPAD_5: (0x0C, 76, False),
    HID.KEYPAD_6: (0x27, 77, False),
    HID.KEYPAD_7: (0x24, 71, False),
    HID.KEYPAD_8: (0x26, 72, False),
    HID.KEYPAD_9: (0x21, 73, False),
    HID.KEYPAD_DECIMAL: (0x2E, 83, False),
}
```

Replace the function with:

```python
def key_event_to_legacy_remote_payload(
    event: KeyEvent,
    *,
    num_lock_on: bool | None = None,
) -> dict[str, int | bool]:
    if event.usage_page != HID.KEYBOARD_PAGE:
        raise ValueError(f"Unsupported HID usage page: 0x{event.usage_page:02X}")
    unsupported_name = _EXPLICIT_UNSUPPORTED.get(event.usage)
    if unsupported_name is not None:
        raise ValueError(f"Unsupported HID usage for legacy relay: {unsupported_name}")
    mapping = None
    if num_lock_on is False:
        mapping = _KEYPAD_NUM_LOCK_OFF_TO_LEGACY.get(event.usage)
    if mapping is None:
        mapping = _USAGE_TO_LEGACY.get(event.usage)
    if mapping is None:
        raise ValueError(f"Unsupported HID usage for remote payload: 0x{event.usage:02X}")
    vk_code, scan_code, extended = mapping
    return {
        "vk_code": vk_code,
        "scan_code": scan_code,
        "extended": extended,
        "pressed": event.pressed,
    }
```

- [ ] **Step 4: Run focused payload tests**

Run: `pytest tests/unit/test_nvda_remote_legacy_key_payload.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/apps/nvda_remote/legacy_key_payload.py tests/unit/test_nvda_remote_legacy_key_payload.py
git commit -m "feat: map keypad payloads by numlock state"
```

## Task 3: Default Bridge To HID Conversion With Native Compatibility Switch

**Files:**
- Modify: `src/apps/nvda_remote/legacy_key_payload_bridge.py`
- Test: `tests/unit/test_nvda_remote_legacy_key_payload_bridge.py`

- [ ] **Step 1: Replace bridge tests with default-HID and native-mode coverage**

Replace `tests/unit/test_nvda_remote_legacy_key_payload_bridge.py` with:

```python
from adapters.inputs.captured_event import CapturedKeyEvent
from adapters.windows.native_key_context import WindowsNativeKeyContext
from interop.key import HID, KeyEvent

from apps.nvda_remote.legacy_key_payload_bridge import legacy_payload_from_captured_event


def test_bridge_defaults_to_hid_even_when_windows_native_context_exists():
    captured = CapturedKeyEvent(
        key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_2, pressed=True),
        native_context=WindowsNativeKeyContext(vk_code=0x28, scan_code=80, extended=False),
        num_lock_on=True,
    )

    assert legacy_payload_from_captured_event(captured) == {
        "vk_code": 0x62,
        "scan_code": 80,
        "extended": False,
        "pressed": True,
    }


def test_bridge_uses_num_lock_state_for_hid_payload():
    captured = CapturedKeyEvent(
        key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_2, pressed=True),
        native_context=None,
        num_lock_on=False,
    )

    assert legacy_payload_from_captured_event(captured) == {
        "vk_code": 0x28,
        "scan_code": 80,
        "extended": False,
        "pressed": True,
    }


def test_bridge_can_use_windows_native_context_when_enabled():
    captured = CapturedKeyEvent(
        key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_2, pressed=False),
        native_context=WindowsNativeKeyContext(vk_code=0x28, scan_code=80, extended=False),
        num_lock_on=True,
    )

    assert legacy_payload_from_captured_event(
        captured,
        use_windows_native_key_payload=True,
    ) == {
        "vk_code": 0x28,
        "scan_code": 80,
        "extended": False,
        "pressed": False,
    }


def test_bridge_native_mode_falls_back_to_hid_without_windows_context():
    captured = CapturedKeyEvent(
        key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True),
        native_context=None,
    )

    assert legacy_payload_from_captured_event(
        captured,
        use_windows_native_key_payload=True,
    ) == {
        "vk_code": 65,
        "scan_code": 30,
        "extended": False,
        "pressed": True,
    }
```

- [ ] **Step 2: Run bridge tests to verify failure**

Run: `pytest tests/unit/test_nvda_remote_legacy_key_payload_bridge.py -v`

Expected: FAIL because the bridge still prefers native context by default and does not accept `use_windows_native_key_payload`.

- [ ] **Step 3: Implement bridge switch**

Replace `src/apps/nvda_remote/legacy_key_payload_bridge.py` with:

```python
from adapters.inputs.captured_event import CapturedKeyEvent
from adapters.windows.native_key_context import WindowsNativeKeyContext

from apps.nvda_remote.legacy_key_payload import key_event_to_legacy_remote_payload


def legacy_payload_from_captured_event(
    captured: CapturedKeyEvent,
    *,
    use_windows_native_key_payload: bool = False,
) -> dict[str, int | bool]:
    context = captured.native_context
    if use_windows_native_key_payload and isinstance(context, WindowsNativeKeyContext):
        return {
            "vk_code": context.vk_code,
            "scan_code": context.scan_code,
            "extended": context.extended,
            "pressed": captured.key_event.pressed,
        }
    return key_event_to_legacy_remote_payload(
        captured.key_event,
        num_lock_on=captured.num_lock_on,
    )
```

- [ ] **Step 4: Run bridge tests**

Run: `pytest tests/unit/test_nvda_remote_legacy_key_payload_bridge.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/apps/nvda_remote/legacy_key_payload_bridge.py tests/unit/test_nvda_remote_legacy_key_payload_bridge.py
git commit -m "feat: default remote payload bridge to hid mapping"
```

## Task 4: Wire Payload Mode Through Input Forwarding

**Files:**
- Modify: `src/apps/nvda_remote/use_cases/input_forwarding.py`
- Modify: `src/apps/nvda_remote/service.py`
- Test: `tests/unit/test_nvda_remote_app_service.py`

- [ ] **Step 1: Add service tests for default HID mode and native compatibility mode**

Update `build_service` in `tests/unit/test_nvda_remote_app_service.py`:

```python
def build_service(*, dispatch=None, use_windows_native_key_payload=False):
```

And pass the new argument into `NvdaRemoteAppService`:

```python
        use_windows_native_key_payload=use_windows_native_key_payload,
```

Add these tests after `test_nvda_remote_service_forwards_keys_when_controlling`:

```python
def test_nvda_remote_service_defaults_to_hid_payload_when_windows_context_exists():
    service, transport, capture, hotkey, _dispatch_calls = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.start_control()

    decision = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_2, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x28, scan_code=80, extended=False),
            num_lock_on=True,
        )
    )

    assert decision == KeyboardPipelineResult(send_to_system=False, app_result=AppKeyEventResult.HANDLED_STOP)
    assert transport.sent == [
        (RemoteMessageType.KEY, {"vk_code": 0x62, "scan_code": 80, "extended": False, "pressed": True})
    ]


def test_nvda_remote_service_can_use_windows_native_payload_when_enabled():
    service, transport, capture, hotkey, _dispatch_calls = build_service(
        use_windows_native_key_payload=True,
    )
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.start_control()

    decision = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_2, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x28, scan_code=80, extended=False),
            num_lock_on=True,
        )
    )

    assert decision == KeyboardPipelineResult(send_to_system=False, app_result=AppKeyEventResult.HANDLED_STOP)
    assert transport.sent == [
        (RemoteMessageType.KEY, {"vk_code": 0x28, "scan_code": 80, "extended": False, "pressed": True})
    ]
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/unit/test_nvda_remote_app_service.py::test_nvda_remote_service_defaults_to_hid_payload_when_windows_context_exists tests/unit/test_nvda_remote_app_service.py::test_nvda_remote_service_can_use_windows_native_payload_when_enabled -v`

Expected: FAIL because `NvdaRemoteAppService` does not accept the new constructor argument and forwarding use case cannot pass bridge mode.

- [ ] **Step 3: Add mode switch to forwarding use case**

In `src/apps/nvda_remote/use_cases/input_forwarding.py`, add a constructor parameter:

```python
        use_windows_native_key_payload: bool = False,
```

Set an instance field:

```python
        self._use_windows_native_key_payload = use_windows_native_key_payload
```

Update the send call:

```python
            self._send_key(
                legacy_payload_from_captured_event(
                    event,
                    use_windows_native_key_payload=self._use_windows_native_key_payload,
                )
            )
```

- [ ] **Step 4: Add mode switch to service constructor**

In `src/apps/nvda_remote/service.py`, add this parameter to `NvdaRemoteAppService.__init__`:

```python
        use_windows_native_key_payload: bool = False,
```

When constructing `NvdaRemoteInputForwardingUseCase`, pass:

```python
            use_windows_native_key_payload=use_windows_native_key_payload,
```

- [ ] **Step 5: Run focused service tests**

Run: `pytest tests/unit/test_nvda_remote_app_service.py::test_nvda_remote_service_defaults_to_hid_payload_when_windows_context_exists tests/unit/test_nvda_remote_app_service.py::test_nvda_remote_service_can_use_windows_native_payload_when_enabled -v`

Expected: PASS.

- [ ] **Step 6: Run input forwarding and app service tests**

Run: `pytest tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_app_service.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/apps/nvda_remote/use_cases/input_forwarding.py src/apps/nvda_remote/service.py tests/unit/test_nvda_remote_app_service.py
git commit -m "feat: add windows native payload forwarding switch"
```

## Task 5: Forward NumLock While Passing It Through Locally

**Files:**
- Modify: `src/apps/nvda_remote/service.py`
- Test: `tests/unit/test_nvda_remote_app_service.py`

- [ ] **Step 1: Replace the current NumLock controlling test**

Replace `test_nvda_remote_service_passes_num_lock_through_when_controlling_on_windows` in `tests/unit/test_nvda_remote_app_service.py` with:

```python
def test_nvda_remote_service_forwards_num_lock_and_passes_through_when_controlling_on_windows():
    service, transport, capture, hotkey, _dispatch_calls = build_service()
    service.bind()
    service.state.connection_state = service.state.connection_state.CONNECTED
    service.start_control()

    keydown_decision = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(
                usage_page=HID.KEYBOARD_PAGE,
                usage=HID.NUM_LOCK,
                pressed=True,
            ),
            native_context=WindowsNativeKeyContext(vk_code=0x90, scan_code=69, extended=True),
            num_lock_on=False,
        )
    )
    keyup_decision = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(
                usage_page=HID.KEYBOARD_PAGE,
                usage=HID.NUM_LOCK,
                pressed=False,
            ),
            native_context=WindowsNativeKeyContext(vk_code=0x90, scan_code=69, extended=True),
            num_lock_on=True,
        )
    )

    assert keydown_decision == KeyboardPipelineResult(
        send_to_system=True,
        app_result=AppKeyEventResult.HANDLED_STOP,
    )
    assert keyup_decision == KeyboardPipelineResult(
        send_to_system=True,
        app_result=AppKeyEventResult.HANDLED_STOP,
    )
    assert transport.sent == [
        (RemoteMessageType.KEY, {"vk_code": 0x90, "scan_code": 69, "extended": True, "pressed": True}),
        (RemoteMessageType.KEY, {"vk_code": 0x90, "scan_code": 69, "extended": True, "pressed": False}),
    ]
```

Add this non-controlling test nearby:

```python
def test_nvda_remote_service_passes_num_lock_through_without_forwarding_before_control():
    service, transport, _capture, _hotkey, _dispatch_calls = build_service()
    service.state.connection_state = service.state.connection_state.CONNECTED

    decision = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(
                usage_page=HID.KEYBOARD_PAGE,
                usage=HID.NUM_LOCK,
                pressed=True,
            ),
            native_context=WindowsNativeKeyContext(vk_code=0x90, scan_code=69, extended=True),
            num_lock_on=False,
        )
    )

    assert decision == KeyboardPipelineResult(send_to_system=True, app_result=AppKeyEventResult.UNHANDLED)
    assert transport.sent == []
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/unit/test_nvda_remote_app_service.py::test_nvda_remote_service_forwards_num_lock_and_passes_through_when_controlling_on_windows tests/unit/test_nvda_remote_app_service.py::test_nvda_remote_service_passes_num_lock_through_without_forwarding_before_control -v`

Expected: FAIL because controlling NumLock currently returns before forwarding.

- [ ] **Step 3: Adjust service decision order**

In `src/apps/nvda_remote/service.py`, replace the first block of `handle_key_event` with:

```python
    def handle_key_event(self, event: CapturedKeyEvent) -> KeyboardPipelineResult:
        key_event = event.key_event
        if should_pass_through_system_toggle(event) and self.state.control_state != ControlState.CONTROLLING:
            return assemble_pipeline_result(send_to_system=True, app_result=AppKeyEventResult.UNHANDLED)
        if not key_event.pressed and key_event.usage in self._suppressed_keyups:
            self._suppressed_keyups.discard(key_event.usage)
            return assemble_pipeline_result(send_to_system=False, app_result=AppKeyEventResult.HANDLED_STOP)
```

Then update the controlling branch:

```python
        if self.state.control_state == ControlState.CONTROLLING:
            decision = self._input_forwarding.handle(event)
            if decision == KeyEventDecision.SUPPRESS:
                send_to_system = should_pass_through_system_toggle(event)
                return assemble_pipeline_result(
                    send_to_system=send_to_system,
                    app_result=AppKeyEventResult.HANDLED_STOP,
                )
            else:
                return assemble_pipeline_result(send_to_system=True, app_result=AppKeyEventResult.HANDLED_STOP)
```

- [ ] **Step 4: Run focused NumLock tests**

Run: `pytest tests/unit/test_nvda_remote_app_service.py::test_nvda_remote_service_forwards_num_lock_and_passes_through_when_controlling_on_windows tests/unit/test_nvda_remote_app_service.py::test_nvda_remote_service_passes_num_lock_through_without_forwarding_before_control -v`

Expected: PASS.

- [ ] **Step 5: Run service tests**

Run: `pytest tests/unit/test_nvda_remote_app_service.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/apps/nvda_remote/service.py tests/unit/test_nvda_remote_app_service.py
git commit -m "fix: forward numlock while passing through locally"
```

## Task 6: Full Verification And Documentation Consistency

**Files:**
- Verify: `docs/superpowers/specs/2026-06-24-keypad-numlock-hid-legacy-payload-design.md`
- Verify: `docs/superpowers/specs/2026-06-24-keypad-numlock-hid-legacy-payload-design_zh-TW.md`
- Verify: all modified source and test files

- [ ] **Step 1: Run the focused test suite**

Run:

```bash
pytest \
  tests/unit/test_nvda_remote_legacy_key_payload.py \
  tests/unit/test_nvda_remote_legacy_key_payload_bridge.py \
  tests/unit/test_nvda_remote_use_cases.py \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_windows_adapters.py \
  -v
```

Expected: PASS.

- [ ] **Step 2: Run full tests**

Run: `pytest tests/unit tests/integration -v`

Expected: PASS.

- [ ] **Step 3: Check changed files**

Run: `git status --short`

Expected: only intended files are modified or newly added.

- [ ] **Step 4: Review specs against implementation**

Read:

```bash
sed -n '1,240p' docs/superpowers/specs/2026-06-24-keypad-numlock-hid-legacy-payload-design.md
sed -n '1,260p' docs/superpowers/specs/2026-06-24-keypad-numlock-hid-legacy-payload-design_zh-TW.md
```

Confirm the implementation covers:

- `CapturedKeyEvent.num_lock_on`
- Windows default HID conversion path
- explicit native compatibility switch
- full keypad mapping table
- `HID.NUM_LOCK` `forward + pass-through`

- [ ] **Step 5: Commit docs if they are still uncommitted**

```bash
git add docs/superpowers/specs/2026-06-24-keypad-numlock-hid-legacy-payload-design.md docs/superpowers/specs/2026-06-24-keypad-numlock-hid-legacy-payload-design_zh-TW.md docs/superpowers/plans/2026-06-24-keypad-numlock-hid-legacy-payload.md
git commit -m "docs: plan keypad numlock payload implementation"
```
