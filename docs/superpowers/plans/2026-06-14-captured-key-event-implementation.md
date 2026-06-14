# CapturedKeyEvent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce `CapturedKeyEvent` and Windows native key context so capture stays platform-aware at the boundary, NVDA Remote forwards Windows legacy payloads from native data, and general business logic continues to consume HID semantics.

**Architecture:** Add a cross-platform capture wrapper in the input adapter layer, update capture protocols and services to pass that wrapper end-to-end, keep `KeyEvent` as pure HID, and add an NVDA Remote bridge that prefers Windows native context when building legacy payloads. In parallel, tighten Windows HID mapping for Num Lock-sensitive keypad and navigation keys so general logic gets stable semantics.

**Tech Stack:** Python 3, pytest, wxPython app services, Windows low-level keyboard hook adapter, macOS event tap adapter

---

## File Map

**Create**
- `src/adapters/inputs/captured_event.py` - defines `CapturedKeyEvent`
- `src/adapters/windows/native_key_context.py` - defines `WindowsNativeKeyContext`
- `src/apps/nvda_remote/legacy_key_payload_bridge.py` - builds legacy payload from `CapturedKeyEvent`
- `tests/unit/test_nvda_remote_legacy_key_payload_bridge.py` - covers native-context-first forwarding behavior
- `docs/superpowers/specs/2026-06-14-captured-key-event-design_zh-TW.md` - already created spec translation, no implementation work required here

**Modify**
- `src/adapters/inputs/base.py` - update `InputCapture` listener protocol to use `CapturedKeyEvent`
- `src/application/keyboard.py` - update `KeyEventHandler` and binding flow to receive `CapturedKeyEvent`
- `src/adapters/windows/keyboard_hook.py` - emit `CapturedKeyEvent` with `WindowsNativeKeyContext`
- `src/adapters/macos/keyboard_hook.py` - emit `CapturedKeyEvent` with `native_context=None`
- `src/adapters/windows/hid_map.py` - formalize keypad/navigation VK-assisted mapping path
- `src/apps/nvda_remote/use_cases/input_forwarding.py` - accept `CapturedKeyEvent` and use bridge helper
- `src/apps/nvda_remote/service.py` - unwrap `captured.key_event` for mode logic and suppression
- `src/apps/key_echo/service.py` - unwrap `captured.key_event` for mode logic
- `src/apps/shared/mode_manager.py` - no signature change expected, should continue receiving plain `KeyEvent`
- `tests/unit/test_windows_adapters.py` - update capture expectations and Windows HID mapping coverage
- `tests/unit/test_macos_adapters.py` - update macOS capture expectations
- `tests/unit/test_nvda_remote_use_cases.py` - update forwarding tests to use `CapturedKeyEvent`
- `tests/unit/test_nvda_remote_app_service.py` - update fake captures and app-service input tests
- `tests/unit/test_key_echo_app_service.py` - update fake captures and service input tests
- `tests/unit/test_keyboard_input_service.py` - update service contract tests
- `tests/unit/test_app_wx.py` - update fake capture listener signatures where needed

**Reference**
- `src/apps/nvda_remote/legacy_key_payload.py` - existing HID-to-legacy mapping fallback
- `tests/unit/test_nvda_remote_legacy_key_payload.py` - existing mapping coverage for fallback path

### Task 1: Add the Shared Capture Wrapper and Update the Input Service Contract

**Files:**
- Create: `src/adapters/inputs/captured_event.py`
- Modify: `src/adapters/inputs/base.py`
- Modify: `src/application/keyboard.py`
- Test: `tests/unit/test_keyboard_input_service.py`
- Test: `tests/unit/test_key_echo_app_service.py`

- [ ] **Step 1: Write the failing tests for the new capture-wrapper contract**

Add these tests to `tests/unit/test_keyboard_input_service.py`:

```python
from adapters.inputs.captured_event import CapturedKeyEvent
from interop.key import HID, KeyEvent


def test_keyboard_input_service_binds_captured_key_event_listener():
    events = []

    class FakeCapture:
        def __init__(self):
            self.listener = None

        def set_listener(self, listener):
            self.listener = listener

        @property
        def running(self):
            return False

        def start(self):
            return None

        def stop(self):
            return None

    class FakeHandler:
        def handle_key_event(self, event):
            events.append(event)
            return "pass_through"

    capture = FakeCapture()
    service = KeyboardInputService(capture, FakeHandler())
    service.bind()

    captured = CapturedKeyEvent(
        key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True),
        native_context=None,
    )
    assert capture.listener(captured) == "pass_through"
    assert events == [captured]
```

Update `tests/unit/test_key_echo_app_service.py` to drive the service with `CapturedKeyEvent`:

```python
from adapters.inputs.captured_event import CapturedKeyEvent

event = CapturedKeyEvent(
    key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True),
    native_context=None,
)
decision = service.handle_key_event(event)
```

- [ ] **Step 2: Run the focused tests to confirm the contract is still KeyEvent-based and fails**

Run: `pytest tests/unit/test_keyboard_input_service.py tests/unit/test_key_echo_app_service.py -v`

Expected: failures showing `CapturedKeyEvent` import missing and/or `handle_key_event` still expecting `KeyEvent`

- [ ] **Step 3: Implement the shared wrapper and update the service contract**

Create `src/adapters/inputs/captured_event.py`:

```python
from dataclasses import dataclass

from interop.key.key_event import KeyEvent


@dataclass(frozen=True)
class CapturedKeyEvent:
    key_event: KeyEvent
    native_context: object | None = None
```

Update `src/adapters/inputs/base.py`:

```python
from adapters.inputs.captured_event import CapturedKeyEvent


class InputCapture(Protocol):
    @property
    def running(self) -> bool: ...

    def set_listener(
        self,
        listener: Callable[[CapturedKeyEvent], KeyEventDecision],
    ) -> None: ...
```

Update `src/application/keyboard.py`:

```python
from adapters.inputs.captured_event import CapturedKeyEvent


class KeyEventHandler(Protocol):
    def handle_key_event(self, event: CapturedKeyEvent) -> KeyEventDecision: ...
```

Update `src/apps/key_echo/service.py` so the app service unwraps the wrapper before delegating:

```python
from adapters.inputs.captured_event import CapturedKeyEvent


def handle_key_event(self, event: CapturedKeyEvent) -> KeyEventDecision:
    return self._mode_manager.handle_key_event(event.key_event)
```

- [ ] **Step 4: Run the focused tests to verify the contract migration passes**

Run: `pytest tests/unit/test_keyboard_input_service.py tests/unit/test_key_echo_app_service.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/inputs/captured_event.py src/adapters/inputs/base.py src/application/keyboard.py src/apps/key_echo/service.py tests/unit/test_keyboard_input_service.py tests/unit/test_key_echo_app_service.py
git commit -m "refactor: add captured key event contract"
```

### Task 2: Update Platform Captures to Emit CapturedKeyEvent

**Files:**
- Create: `src/adapters/windows/native_key_context.py`
- Modify: `src/adapters/windows/keyboard_hook.py`
- Modify: `src/adapters/macos/keyboard_hook.py`
- Test: `tests/unit/test_windows_adapters.py`
- Test: `tests/unit/test_macos_adapters.py`

- [ ] **Step 1: Write the failing capture-emission tests**

Update `tests/unit/test_windows_adapters.py`:

```python
from adapters.inputs.captured_event import CapturedKeyEvent
from adapters.windows.native_key_context import WindowsNativeKeyContext


def test_windows_keyboard_hook_callback_emits_captured_key_event():
    ...
    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.TAB, pressed=True),
            native_context=WindowsNativeKeyContext(
                vk_code=0x09,
                scan_code=15,
                extended=False,
            ),
        ),
    ]
```

Update `tests/unit/test_macos_adapters.py`:

```python
from adapters.inputs.captured_event import CapturedKeyEvent


assert seen == [
    CapturedKeyEvent(
        key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True),
        native_context=None,
    ),
]
```

- [ ] **Step 2: Run the platform adapter tests to verify they fail on raw KeyEvent output**

Run: `pytest tests/unit/test_windows_adapters.py tests/unit/test_macos_adapters.py -v`

Expected: failures showing capture callbacks still emit plain `KeyEvent`

- [ ] **Step 3: Implement native-context and capture emission changes**

Create `src/adapters/windows/native_key_context.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class WindowsNativeKeyContext:
    vk_code: int
    scan_code: int
    extended: bool
```

Update `src/adapters/windows/keyboard_hook.py`:

```python
from adapters.inputs.captured_event import CapturedKeyEvent
from adapters.windows.native_key_context import WindowsNativeKeyContext

...
self._listener: Callable[[CapturedKeyEvent], KeyEventDecision] | None = None

...
event = key_event_from_windows(...)
decision = self._emit_for_tests(
    None
    if event is None
    else CapturedKeyEvent(
        key_event=event,
        native_context=WindowsNativeKeyContext(
            vk_code=vk_code,
            scan_code=scan_code,
            extended=extended,
        ),
    )
)
```

Update `src/adapters/macos/keyboard_hook.py`:

```python
from adapters.inputs.captured_event import CapturedKeyEvent

...
self._listener: Callable[[CapturedKeyEvent], KeyEventDecision] | None = None

...
return self._listener(
    CapturedKeyEvent(
        key_event=key_event,
        native_context=None,
    )
)
```

- [ ] **Step 4: Run the platform adapter tests to verify captured-event emission passes**

Run: `pytest tests/unit/test_windows_adapters.py tests/unit/test_macos_adapters.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/windows/native_key_context.py src/adapters/windows/keyboard_hook.py src/adapters/macos/keyboard_hook.py tests/unit/test_windows_adapters.py tests/unit/test_macos_adapters.py
git commit -m "feat: emit captured key events from adapters"
```

### Task 3: Route NVDA Remote Forwarding Through the Legacy Payload Bridge

**Files:**
- Create: `src/apps/nvda_remote/legacy_key_payload_bridge.py`
- Modify: `src/apps/nvda_remote/use_cases/input_forwarding.py`
- Modify: `src/apps/nvda_remote/service.py`
- Modify: `tests/unit/test_nvda_remote_use_cases.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`
- Create: `tests/unit/test_nvda_remote_legacy_key_payload_bridge.py`

- [ ] **Step 1: Write failing bridge and forwarding tests**

Create `tests/unit/test_nvda_remote_legacy_key_payload_bridge.py`:

```python
from adapters.inputs.captured_event import CapturedKeyEvent
from adapters.windows.native_key_context import WindowsNativeKeyContext
from interop.key import HID, KeyEvent

from apps.nvda_remote.legacy_key_payload_bridge import legacy_payload_from_captured_event


def test_bridge_prefers_windows_native_context():
    captured = CapturedKeyEvent(
        key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True),
        native_context=WindowsNativeKeyContext(vk_code=0x41, scan_code=30, extended=False),
    )

    assert legacy_payload_from_captured_event(captured) == {
        "vk_code": 0x41,
        "scan_code": 30,
        "extended": False,
        "pressed": True,
    }
```

Update `tests/unit/test_nvda_remote_use_cases.py`:

```python
from adapters.inputs.captured_event import CapturedKeyEvent
from adapters.windows.native_key_context import WindowsNativeKeyContext

event = CapturedKeyEvent(
    key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True),
    native_context=WindowsNativeKeyContext(vk_code=65, scan_code=30, extended=False),
)
decision = use_case.handle(event)
```

Update `tests/unit/test_nvda_remote_app_service.py` similarly so app-service handlers receive `CapturedKeyEvent`.

- [ ] **Step 2: Run NVDA Remote tests to confirm failures**

Run: `pytest tests/unit/test_nvda_remote_legacy_key_payload_bridge.py tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_app_service.py -v`

Expected: failures for missing bridge helper and `handle_key_event` still assuming plain `KeyEvent`

- [ ] **Step 3: Implement the bridge and app/use-case unwrap logic**

Create `src/apps/nvda_remote/legacy_key_payload_bridge.py`:

```python
from adapters.inputs.captured_event import CapturedKeyEvent
from adapters.windows.native_key_context import WindowsNativeKeyContext

from apps.nvda_remote.legacy_key_payload import key_event_to_legacy_remote_payload


def legacy_payload_from_captured_event(captured: CapturedKeyEvent) -> dict[str, int | bool]:
    context = captured.native_context
    if isinstance(context, WindowsNativeKeyContext):
        return {
            "vk_code": context.vk_code,
            "scan_code": context.scan_code,
            "extended": context.extended,
            "pressed": captured.key_event.pressed,
        }
    return key_event_to_legacy_remote_payload(captured.key_event)
```

Update `src/apps/nvda_remote/use_cases/input_forwarding.py`:

```python
from adapters.inputs.captured_event import CapturedKeyEvent
from apps.nvda_remote.legacy_key_payload_bridge import legacy_payload_from_captured_event


def handle(self, event: CapturedKeyEvent) -> KeyEventDecision:
    key_event = event.key_event
    if not key_event.pressed and key_event.usage in self._suppressed_keyups:
        ...
    try:
        self._send_key(legacy_payload_from_captured_event(event))
```

Update `src/apps/nvda_remote/service.py`:

```python
from adapters.inputs.captured_event import CapturedKeyEvent


def handle_key_event(self, event: CapturedKeyEvent) -> KeyEventDecision:
    key_event = event.key_event
    if not key_event.pressed and key_event.usage in self._suppressed_keyups:
        ...
    if key_event.pressed and key_event.usage == self._LOCAL_STOP_USAGE and self._mode_manager.active_mode_id is not None:
        ...
    return self._mode_manager.handle_key_event(key_event)
```

- [ ] **Step 4: Run the NVDA Remote tests to verify forwarding now prefers native context**

Run: `pytest tests/unit/test_nvda_remote_legacy_key_payload_bridge.py tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_app_service.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/nvda_remote/legacy_key_payload_bridge.py src/apps/nvda_remote/use_cases/input_forwarding.py src/apps/nvda_remote/service.py tests/unit/test_nvda_remote_legacy_key_payload_bridge.py tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_app_service.py
git commit -m "feat: forward native windows payloads for nvda remote"
```

### Task 4: Strengthen Windows HID Semantics for Keypad and Navigation Keys

**Files:**
- Modify: `src/adapters/windows/hid_map.py`
- Modify: `tests/unit/test_windows_adapters.py`

- [ ] **Step 1: Write failing tests for the full VK-assisted keypad/navigation scope**

Add to `tests/unit/test_windows_adapters.py`:

```python
@pytest.mark.parametrize(
    ("vk_code", "expected_usage"),
    [
        (0x60, HID.KEYPAD_0),
        (0x61, HID.KEYPAD_1),
        (0x62, HID.KEYPAD_2),
        (0x63, HID.KEYPAD_3),
        (0x64, HID.KEYPAD_4),
        (0x65, HID.KEYPAD_5),
        (0x66, HID.KEYPAD_6),
        (0x67, HID.KEYPAD_7),
        (0x68, HID.KEYPAD_8),
        (0x69, HID.KEYPAD_9),
        (0x23, HID.END),
        (0x24, HID.HOME),
        (0x25, HID.LEFT),
        (0x26, HID.UP),
        (0x27, HID.RIGHT),
        (0x28, HID.DOWN),
        (0x2D, HID.INSERT),
        (0x2E, HID.DELETE),
    ],
)
def test_key_event_from_windows_uses_vk_fallback_for_keypad_and_navigation_group(vk_code, expected_usage):
    from adapters.windows.hid_map import key_event_from_windows

    event = key_event_from_windows(
        vk_code=vk_code,
        scan_code=99999,
        extended=True,
        pressed=True,
    )

    assert event == KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=expected_usage, pressed=True)
```

Also keep a priority test:

```python
def test_key_event_from_windows_prefers_standard_scan_code_over_vk_fallback():
    from adapters.windows.hid_map import key_event_from_windows

    event = key_event_from_windows(vk_code=0x23, scan_code=79, extended=True, pressed=True)

    assert event == KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.END, pressed=True)
```

- [ ] **Step 2: Run the Windows adapter tests to capture any missing VK mappings**

Run: `pytest tests/unit/test_windows_adapters.py -v`

Expected: failures for missing or incomplete VK-assisted coverage

- [ ] **Step 3: Implement the keypad/navigation VK-group handling cleanly**

Update `src/adapters/windows/hid_map.py` to keep the rule explicit:

```python
_VK_TO_USAGE_KEYPAD_NAV: dict[int, int] = {
    0x21: HID.PAGE_UP,
    0x22: HID.PAGE_DOWN,
    0x23: HID.END,
    0x24: HID.HOME,
    0x25: HID.LEFT,
    0x26: HID.UP,
    0x27: HID.RIGHT,
    0x28: HID.DOWN,
    0x2D: HID.INSERT,
    0x2E: HID.DELETE,
    0x60: HID.KEYPAD_0,
    0x61: HID.KEYPAD_1,
    0x62: HID.KEYPAD_2,
    0x63: HID.KEYPAD_3,
    0x64: HID.KEYPAD_4,
    0x65: HID.KEYPAD_5,
    0x66: HID.KEYPAD_6,
    0x67: HID.KEYPAD_7,
    0x68: HID.KEYPAD_8,
    0x69: HID.KEYPAD_9,
    0x6A: HID.KEYPAD_MULTIPLY,
    0x6B: HID.KEYPAD_ADD,
    0x6D: HID.KEYPAD_SUBTRACT,
    0x6E: HID.KEYPAD_DECIMAL,
    0x6F: HID.KEYPAD_DIVIDE,
    0x90: HID.NUM_LOCK,
}


def key_event_from_windows(*, vk_code: int, scan_code: int, extended: bool, pressed: bool) -> KeyEvent | None:
    usage = _SCAN_TO_USAGE.get((scan_code, extended))
    if usage is None and extended and scan_code > 0xFF:
        usage = _SCAN_TO_USAGE.get((scan_code & 0xFF, extended))
    if usage is None:
        usage = _VK_TO_USAGE_KEYPAD_NAV.get(vk_code)
    if usage is None and vk_code == 0xF2:
        usage = HID.INTERNATIONAL3
    if usage is None:
        return None
    return KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=pressed)
```

- [ ] **Step 4: Run the Windows adapter tests to verify the semantics layer**

Run: `pytest tests/unit/test_windows_adapters.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/windows/hid_map.py tests/unit/test_windows_adapters.py
git commit -m "fix: stabilize windows keypad hid mapping"
```

### Task 5: Run the Integrated Regression Slice

**Files:**
- Modify: `tests/unit/test_app_wx.py`
- Modify: any remaining fake capture tests touched by the signature migration

- [ ] **Step 1: Update any remaining fake captures to accept `CapturedKeyEvent`**

Apply the same fake-listener contract in any straggler tests, especially `tests/unit/test_app_wx.py` and `tests/unit/test_nvda_remote_app_service.py`:

```python
from adapters.inputs.captured_event import CapturedKeyEvent


class FakeKeyboardCapture:
    def __init__(self):
        self.listener = None

    def set_listener(self, listener):
        self.listener = listener
```

Where tests invoke the listener directly, pass:

```python
CapturedKeyEvent(
    key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F11, pressed=True),
    native_context=None,
)
```

- [ ] **Step 2: Run the focused regression suite**

Run:

```bash
pytest \
  tests/unit/test_keyboard_input_service.py \
  tests/unit/test_key_echo_app_service.py \
  tests/unit/test_windows_adapters.py \
  tests/unit/test_macos_adapters.py \
  tests/unit/test_nvda_remote_legacy_key_payload_bridge.py \
  tests/unit/test_nvda_remote_use_cases.py \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_app_wx.py -v
```

Expected: PASS

- [ ] **Step 3: Run the broader unit suite for confidence**

Run: `pytest tests/unit -v`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_app_wx.py tests/unit/test_nvda_remote_app_service.py
git commit -m "test: align capture event regression coverage"
```

## Self-Review

- Spec coverage:
  - `CapturedKeyEvent` and `WindowsNativeKeyContext` are implemented in Tasks 1-2.
  - `InputCapture` / `KeyboardInputService` contract migration is handled in Task 1.
  - Windows and macOS capture output migration is handled in Task 2.
  - NVDA Remote native-context-first forwarding is handled in Task 3.
  - Windows keypad/navigation HID semantics are handled in Task 4.
  - Regression validation for app/service boundaries is handled in Task 5.
- Placeholder scan:
  - No `TODO`, `TBD`, or “implement later” placeholders remain.
  - Every code-changing step includes explicit file paths, code snippets, and commands.
- Type consistency:
  - `CapturedKeyEvent.key_event`
  - `CapturedKeyEvent.native_context`
  - `WindowsNativeKeyContext(vk_code, scan_code, extended)`
  - `legacy_payload_from_captured_event(captured)`
  - `handle_key_event(self, event: CapturedKeyEvent)`

## Notes for Execution

- Do not change `apps.shared.mode_manager.ModeManager` to know about `CapturedKeyEvent`; it should continue to receive plain `KeyEvent`.
- In NVDA Remote, perform suppression checks against `event.key_event.usage`, not against the wrapper object.
- Keep HID fallback behavior in the bridge for non-Windows tests and future portability, but treat Windows native context as the primary forwarding path in this phase.
- Prefer small commits exactly as listed; the interface migration touches many tests, and narrower commits make regressions easier to isolate.
