# HID Keyboard Input Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the shared keyboard event model with HID-first events across Windows and macOS input capture, shared input logic, and both apps, while preserving the existing NVDA Remote relay wire format through a legacy adapter.

**Architecture:** The implementation keeps HID as the only shared keyboard representation inside `src/`. Platform adapters normalize native events into `KeyEvent(usage_page, usage, pressed)`, application and app code compare HID constants, and `apps/nvda_remote` converts HID back into the old `vk_code/scan_code/extended/pressed` payload only at the protocol boundary.

**Tech Stack:** Python 3.11, `pytest`, `ctypes`, Quartz/PyObjC adapters, dataclasses, existing relay JSON protocol

---

## File Structure

### Create

- `src/interop/key/hid.py`
- `src/adapters/windows/hid_map.py`
- `src/adapters/macos/hid_map.py`
- `src/apps/nvda_remote/legacy_key_payload.py`
- `tests/unit/test_hid_keys.py`
- `tests/unit/test_nvda_remote_legacy_key_payload.py`

### Modify

- `src/interop/key/key_event.py`
- `src/interop/key/__init__.py`
- `src/adapters/windows/keyboard_hook.py`
- `src/adapters/windows/hotkey.py`
- `src/adapters/macos/keyboard_hook.py`
- `src/adapters/macos/keymap.py`
- `src/adapters/macos/hotkey.py`
- `src/application/input/active_key_policy.py`
- `src/application/input/state_transition_hotkeys.py`
- `src/apps/shared/mode_manager.py`
- `src/apps/key_echo/use_cases/echo_input.py`
- `src/apps/key_echo/use_cases/state_transition_hotkeys.py`
- `src/apps/key_echo/facade.py`
- `src/apps/nvda_remote/use_cases/state_transition_hotkeys.py`
- `src/apps/nvda_remote/use_cases/input_forwarding.py`
- `src/apps/nvda_remote/facade.py`
- `src/bootstrap/platform.py`
- `tests/unit/test_protocol_serializer.py`
- `tests/unit/test_windows_adapters.py`
- `tests/unit/test_macos_adapters.py`
- `tests/unit/test_input_policies.py`
- `tests/unit/test_mode_manager.py`
- `tests/unit/test_key_echo_use_cases.py`
- `tests/unit/test_key_echo_app_service.py`
- `tests/unit/test_nvda_remote_use_cases.py`
- `tests/unit/test_nvda_remote_app_service.py`
- `tests/unit/test_bootstrap_platform.py`
- `tests/unit/test_app_wx.py`
- `tests/unit/test_keyboard_input_service.py`

### Responsibilities

- `src/interop/key/hid.py`: HID constants and helper predicates for `usage_page` `0x07`.
- `src/interop/key/key_event.py`: shared HID `KeyEvent` model and local serialization helper.
- `src/adapters/windows/hid_map.py`: Windows `scanCode + extended + vkCode` to HID mappings plus reverse legacy conversion helpers.
- `src/adapters/macos/hid_map.py`: macOS virtual key code to HID mapping table.
- `src/adapters/*/keyboard_hook.py`: native capture to HID conversion.
- `src/adapters/*/hotkey.py`: platform hotkey adapters keyed by HID usage, not VK or raw macOS key codes.
- `src/application/input/*` and `src/apps/shared/mode_manager.py`: compare HID usage values instead of `event.vk`.
- `src/apps/key_echo/*`: echo mode hotkeys and spoken output based on HID usage naming.
- `src/apps/nvda_remote/legacy_key_payload.py`: single HID -> legacy relay payload adapter.
- `src/apps/nvda_remote/*`: local stop and forwarding logic based on HID, with legacy payload conversion at send time.
- `src/bootstrap/platform.py`: platform factories that request hotkeys by HID usage and translate to platform adapters.

### Implementation Notes

- Keep `usage_page` explicit in `KeyEvent` even though phase 1 only supports `0x07`.
- Do not add consumer/media key support in this plan.
- Do not change `RemoteMessageType.KEY` wire format.
- Do not leave compatibility conversion code in multiple places; only `legacy_key_payload.py` should know `vk_code/scan_code/extended`.
- Prefer one new focused mapping module per platform over growing existing adapter files.

## Task 1: Introduce the HID Core Model

**Files:**
- Create: `src/interop/key/hid.py`
- Modify: `src/interop/key/key_event.py`
- Modify: `src/interop/key/__init__.py`
- Create: `tests/unit/test_hid_keys.py`
- Modify: `tests/unit/test_protocol_serializer.py`

- [ ] **Step 1: Write the failing tests for the new HID event model and constants**

```python
# tests/unit/test_hid_keys.py
from interop.key import HID, KeyEvent


def test_key_event_uses_hid_fields():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    assert event.usage_page == 0x07
    assert event.usage == 0x04
    assert event.pressed is True


def test_key_event_to_local_payload_is_hid_first():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F11, pressed=False)
    assert event.to_local_payload() == {
        "usage_page": 0x07,
        "usage": 0x44,
        "pressed": False,
    }
```

```python
# tests/unit/test_protocol_serializer.py
from interop.key import HID, KeyEvent


def test_key_event_to_local_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    assert event.to_local_payload() == {
        "usage_page": 0x07,
        "usage": 0x04,
        "pressed": True,
    }
```

- [ ] **Step 2: Run the tests to verify they fail against the old model**

Run: `pytest tests/unit/test_hid_keys.py tests/unit/test_protocol_serializer.py::test_key_event_to_local_payload -v`
Expected: FAIL with `ImportError` for `HID` and/or `TypeError` because `KeyEvent` does not accept `usage_page` and `usage`.

- [ ] **Step 3: Add the HID constants module and replace the shared event shape**

```python
# src/interop/key/hid.py
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _HIDKeyboard:
    KEYBOARD_PAGE: int = 0x07
    A: int = 0x04
    B: int = 0x05
    C: int = 0x06
    D: int = 0x07
    E: int = 0x08
    F: int = 0x09
    G: int = 0x0A
    H: int = 0x0B
    I: int = 0x0C
    J: int = 0x0D
    K: int = 0x0E
    L: int = 0x0F
    M: int = 0x10
    N: int = 0x11
    O: int = 0x12
    P: int = 0x13
    Q: int = 0x14
    R: int = 0x15
    S: int = 0x16
    T: int = 0x17
    U: int = 0x18
    V: int = 0x19
    W: int = 0x1A
    X: int = 0x1B
    Y: int = 0x1C
    Z: int = 0x1D
    DIGIT_1: int = 0x1E
    DIGIT_2: int = 0x1F
    DIGIT_3: int = 0x20
    DIGIT_4: int = 0x21
    DIGIT_5: int = 0x22
    DIGIT_6: int = 0x23
    DIGIT_7: int = 0x24
    DIGIT_8: int = 0x25
    DIGIT_9: int = 0x26
    DIGIT_0: int = 0x27
    ENTER: int = 0x28
    ESCAPE: int = 0x29
    BACKSPACE: int = 0x2A
    TAB: int = 0x2B
    SPACE: int = 0x2C
    F1: int = 0x3A
    F2: int = 0x3B
    F3: int = 0x3C
    F4: int = 0x3D
    F5: int = 0x3E
    F6: int = 0x3F
    F7: int = 0x40
    F8: int = 0x41
    F9: int = 0x42
    F10: int = 0x43
    F11: int = 0x44
    F12: int = 0x45
    RIGHT: int = 0x4F
    LEFT: int = 0x50
    DOWN: int = 0x51
    UP: int = 0x52
    KEYPAD_ENTER: int = 0x58
    LEFT_CONTROL: int = 0xE0
    LEFT_SHIFT: int = 0xE1
    LEFT_ALT: int = 0xE2
    LEFT_META: int = 0xE3
    RIGHT_CONTROL: int = 0xE4
    RIGHT_SHIFT: int = 0xE5
    RIGHT_ALT: int = 0xE6
    RIGHT_META: int = 0xE7

    def is_keyboard_page(self, usage_page: int) -> bool:
        return usage_page == self.KEYBOARD_PAGE


HID = _HIDKeyboard()
```

```python
# src/interop/key/key_event.py
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KeyEvent:
    usage_page: int
    usage: int
    pressed: bool

    def to_local_payload(self) -> dict[str, int | bool]:
        return {
            "usage_page": self.usage_page,
            "usage": self.usage,
            "pressed": self.pressed,
        }
```

```python
# src/interop/key/__init__.py
from interop.key.hid import HID
from interop.key.key_event import KeyEvent

__all__ = ["HID", "KeyEvent"]
```

- [ ] **Step 4: Run the new core-model tests**

Run: `pytest tests/unit/test_hid_keys.py tests/unit/test_protocol_serializer.py::test_key_event_to_local_payload -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/interop/key/hid.py src/interop/key/key_event.py src/interop/key/__init__.py tests/unit/test_hid_keys.py tests/unit/test_protocol_serializer.py
git commit -m "feat: add HID keyboard event model"
```

## Task 2: Convert Windows and macOS Capture to HID

**Files:**
- Create: `src/adapters/windows/hid_map.py`
- Create: `src/adapters/macos/hid_map.py`
- Modify: `src/adapters/windows/keyboard_hook.py`
- Modify: `src/adapters/macos/keymap.py`
- Modify: `src/adapters/macos/keyboard_hook.py`
- Modify: `tests/unit/test_windows_adapters.py`
- Modify: `tests/unit/test_macos_adapters.py`

- [ ] **Step 1: Write failing platform mapping tests**

```python
# tests/unit/test_windows_adapters.py
from interop.key import HID, KeyEvent


def test_windows_keyboard_hook_callback_emits_hid_key_event():
    user32 = FakeKeyboardUser32()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(seen.append)
    capture.start()
    callback = user32.installed[0][1]
    key_data = FakeKbdLlHookStruct(vkCode=0x09, scanCode=15, flags=0)

    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert seen == [
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.TAB, pressed=True),
    ]
```

```python
# tests/unit/test_macos_adapters.py
from interop.key import HID, KeyEvent


def test_key_event_from_macos_maps_letter_keydown_to_hid():
    event = key_event_from_macos(key_code=0, pressed=True, is_repeat=False)
    assert event == KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)


def test_key_event_from_macos_maps_f11_keyup_to_hid():
    event = key_event_from_macos(key_code=103, pressed=False, is_repeat=False)
    assert event == KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F11, pressed=False)
```

- [ ] **Step 2: Run the platform tests to verify they fail**

Run: `pytest tests/unit/test_windows_adapters.py::test_windows_keyboard_hook_callback_emits_hid_key_event tests/unit/test_macos_adapters.py::test_key_event_from_macos_maps_letter_keydown_to_hid tests/unit/test_macos_adapters.py::test_key_event_from_macos_maps_f11_keyup_to_hid -v`
Expected: FAIL because adapters still build `KeyEvent(vk=..., scan=..., extended=...)`.

- [ ] **Step 3: Add focused HID mapping modules and switch capture output**

```python
# src/adapters/windows/hid_map.py
from interop.key import HID, KeyEvent

_SCAN_TO_USAGE: dict[tuple[int, bool], int] = {
    (1, False): HID.ESCAPE,
    (15, False): HID.TAB,
    (28, False): HID.ENTER,
    (28, True): HID.KEYPAD_ENTER,
    (30, False): HID.A,
    (48, False): HID.B,
    (50, False): HID.M,
    (57, False): HID.SPACE,
    (59, False): HID.F1,
    (60, False): HID.F2,
    (61, False): HID.F3,
    (62, False): HID.F4,
    (63, False): HID.F5,
    (64, False): HID.F6,
    (65, False): HID.F7,
    (66, False): HID.F8,
    (67, False): HID.F9,
    (68, False): HID.F10,
    (87, False): HID.F11,
    (88, False): HID.F12,
    (72, True): HID.UP,
    (75, True): HID.LEFT,
    (77, True): HID.RIGHT,
    (80, True): HID.DOWN,
    (29, False): HID.LEFT_CONTROL,
    (29, True): HID.RIGHT_CONTROL,
    (42, False): HID.LEFT_SHIFT,
    (54, False): HID.RIGHT_SHIFT,
    (56, False): HID.LEFT_ALT,
    (56, True): HID.RIGHT_ALT,
    (91, False): HID.LEFT_META,
    (92, False): HID.RIGHT_META,
}


def key_event_from_windows(*, vk_code: int, scan_code: int, extended: bool, pressed: bool) -> KeyEvent | None:
    del vk_code
    usage = _SCAN_TO_USAGE.get((scan_code, extended))
    if usage is None:
        return None
    return KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=pressed)
```

```python
# src/adapters/macos/hid_map.py
from interop.key import HID

KEYCODE_TO_USAGE: dict[int, int] = {
    0: HID.A,
    11: HID.B,
    8: HID.C,
    2: HID.D,
    14: HID.E,
    3: HID.F,
    5: HID.G,
    4: HID.H,
    34: HID.I,
    38: HID.J,
    40: HID.K,
    37: HID.L,
    46: HID.M,
    45: HID.N,
    31: HID.O,
    35: HID.P,
    12: HID.Q,
    15: HID.R,
    1: HID.S,
    17: HID.T,
    32: HID.U,
    9: HID.V,
    13: HID.W,
    7: HID.X,
    16: HID.Y,
    6: HID.Z,
    36: HID.ENTER,
    53: HID.ESCAPE,
    48: HID.TAB,
    49: HID.SPACE,
    51: HID.BACKSPACE,
    122: HID.F1,
    120: HID.F2,
    99: HID.F3,
    118: HID.F4,
    96: HID.F5,
    97: HID.F6,
    98: HID.F7,
    100: HID.F8,
    101: HID.F9,
    109: HID.F10,
    103: HID.F11,
    111: HID.F12,
    123: HID.LEFT,
    124: HID.RIGHT,
    125: HID.DOWN,
    126: HID.UP,
    59: HID.LEFT_CONTROL,
    62: HID.RIGHT_CONTROL,
    56: HID.LEFT_SHIFT,
    60: HID.RIGHT_SHIFT,
    58: HID.LEFT_ALT,
    61: HID.RIGHT_ALT,
    55: HID.LEFT_META,
    54: HID.RIGHT_META,
}
```

```python
# src/adapters/macos/keymap.py
from interop.key import HID, KeyEvent
from adapters.macos.hid_map import KEYCODE_TO_USAGE


def key_event_from_macos(*, key_code: int, pressed: bool, is_repeat: bool) -> KeyEvent | None:
    del is_repeat
    usage = KEYCODE_TO_USAGE.get(key_code)
    if usage is None:
        return None
    return KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=pressed)
```

```python
# src/adapters/windows/keyboard_hook.py
from adapters.windows.hid_map import key_event_from_windows

...
            event = key_event_from_windows(
                vk_code=int(data.vkCode),
                scan_code=int(data.scanCode),
                extended=bool(data.flags & LLKHF_EXTENDED),
                pressed=w_param in (WM_KEYDOWN, WM_SYSKEYDOWN),
            )
            decision = self._emit_for_tests(event)
...
    def _emit_for_tests(self, event: KeyEvent | None) -> KeyEventDecision:
        if event is None or self._listener is None:
            return KeyEventDecision.PASS_THROUGH
        return self._listener(event)
```

- [ ] **Step 4: Run the focused platform tests**

Run: `pytest tests/unit/test_windows_adapters.py::test_windows_keyboard_hook_callback_emits_hid_key_event tests/unit/test_macos_adapters.py::test_key_event_from_macos_maps_letter_keydown_to_hid tests/unit/test_macos_adapters.py::test_key_event_from_macos_maps_f11_keyup_to_hid -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/windows/hid_map.py src/adapters/macos/hid_map.py src/adapters/windows/keyboard_hook.py src/adapters/macos/keymap.py src/adapters/macos/keyboard_hook.py tests/unit/test_windows_adapters.py tests/unit/test_macos_adapters.py
git commit -m "feat: normalize platform key capture to HID"
```

## Task 3: Convert Shared Input Policies and Mode Management

**Files:**
- Modify: `src/application/input/active_key_policy.py`
- Modify: `src/application/input/state_transition_hotkeys.py`
- Modify: `src/apps/shared/mode_manager.py`
- Modify: `tests/unit/test_input_policies.py`
- Modify: `tests/unit/test_mode_manager.py`

- [ ] **Step 1: Write failing tests for HID-based policy and mode routing**

```python
# tests/unit/test_input_policies.py
from interop.key import HID, KeyEvent


def test_idle_hotkey_policy_matches_hid_keydown_only():
    policy = StateTransitionHotkeyPolicy(mapping={HID.F11: "enter_active"})
    assert policy.match(KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F11, pressed=True)) == "enter_active"
    assert policy.match(KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F11, pressed=False)) is None


def test_active_key_policy_uses_hid_exit_key_before_normal_handler():
    calls: list[str] = []
    policy = ActiveKeyEventPolicy(
        exit_usage=HID.ESCAPE,
        on_exit=lambda: calls.append("exit") or KeyEventDecision.SUPPRESS,
        on_key=lambda event: calls.append(f"key:{event.usage}") or KeyEventDecision.PASS_THROUGH,
    )
    policy.handle(KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.ESCAPE, pressed=True))
    policy.handle(KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True))
    assert calls == ["exit", f"key:{HID.A}"]
```

```python
# tests/unit/test_mode_manager.py
from interop.key import HID, KeyEvent


def test_mode_manager_routes_non_exit_hid_keys_to_active_mode():
    ...
    decision = manager.handle_key_event(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    )
    assert mode.events == [HID.A]


def test_mode_manager_exit_hid_key_deactivates_mode():
    ...
    decision = manager.handle_key_event(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.ESCAPE, pressed=True)
    )
    assert decision == KeyEventDecision.SUPPRESS
```

- [ ] **Step 2: Run the shared-policy tests to verify they fail**

Run: `pytest tests/unit/test_input_policies.py tests/unit/test_mode_manager.py -v`
Expected: FAIL because shared policy code still reads `event.vk` and mode classes still store `exit_vk`.

- [ ] **Step 3: Update policies and mode routing to compare HID usage**

```python
# src/application/input/active_key_policy.py
class ActiveKeyEventPolicy:
    def __init__(
        self,
        *,
        exit_usage: int,
        on_exit: Callable[[], KeyEventDecision],
        on_key: Callable[[KeyEvent], KeyEventDecision],
    ) -> None:
        self._exit_usage = exit_usage
        self._on_exit = on_exit
        self._on_key = on_key

    def handle(self, event: KeyEvent) -> KeyEventDecision:
        if event.pressed and event.usage == self._exit_usage:
            return self._on_exit()
        return self._on_key(event)
```

```python
# src/application/input/state_transition_hotkeys.py
class StateTransitionHotkeyPolicy:
    def __init__(self, *, mapping: dict[int, str]) -> None:
        self._mapping = dict(mapping)

    def match(self, event: KeyEvent) -> str | None:
        if not event.pressed:
            return None
        return self._mapping.get(event.usage)
```

```python
# src/apps/shared/mode_manager.py
class ModeManager:
    ...
    def handle_key_event(self, event: KeyEvent) -> KeyEventDecision:
        if self.active_mode_id is None:
            return KeyEventDecision.PASS_THROUGH
        mode = self._modes[self.active_mode_id]
        if event.pressed and event.usage == mode.exit_usage:
            return self.exit_active_mode()
        return mode.handle_key_event(event)
```

```python
# tests/unit/test_mode_manager.py
class FakeMode:
    mode_id = "echo"
    enter_usage = HID.ENTER
    exit_usage = HID.ESCAPE
    ...
    def handle_key_event(self, event):
        self.events.append(event.usage)
        return KeyEventDecision.SUPPRESS
```

- [ ] **Step 4: Run the shared-policy test slice**

Run: `pytest tests/unit/test_input_policies.py tests/unit/test_mode_manager.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/application/input/active_key_policy.py src/application/input/state_transition_hotkeys.py src/apps/shared/mode_manager.py tests/unit/test_input_policies.py tests/unit/test_mode_manager.py
git commit -m "refactor: use HID in shared input policies"
```

## Task 4: Convert Key Echo to HID Hotkeys and HID Speech Output

**Files:**
- Modify: `src/apps/key_echo/use_cases/echo_input.py`
- Modify: `src/apps/key_echo/use_cases/state_transition_hotkeys.py`
- Modify: `src/apps/key_echo/facade.py`
- Modify: `src/bootstrap/platform.py`
- Modify: `tests/unit/test_key_echo_use_cases.py`
- Modify: `tests/unit/test_key_echo_app_service.py`
- Modify: `tests/unit/test_bootstrap_platform.py`

- [ ] **Step 1: Write failing tests for HID key echo behavior**

```python
# tests/unit/test_key_echo_use_cases.py
from interop.key import HID, KeyEvent


def test_key_echo_hotkey_use_case_maps_enter_and_escape_by_hid():
    use_case = KeyEchoStateTransitionHotkeyUseCase(
        mapping={
            HID.ENTER: KeyEchoHotkeyAction.START_ECHO,
            HID.ESCAPE: KeyEchoHotkeyAction.STOP_ECHO,
        }
    )
    assert use_case.match(KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.ENTER, pressed=True)) == KeyEchoHotkeyAction.START_ECHO
    assert use_case.match(KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.ESCAPE, pressed=True)) == KeyEchoHotkeyAction.STOP_ECHO


def test_echo_input_use_case_speaks_hid_usage_text_on_keydown():
    calls = []
    use_case = KeyEchoInputUseCase(
        cancel=lambda: calls.append(("cancel", None)),
        speak=lambda sequence: calls.append(("speak", sequence)),
    )
    decision = use_case.handle(KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True))
    assert decision == KeyEventDecision.SUPPRESS
    assert calls[1][1].items == ("HID 0x07:0x04",)
```

```python
# tests/unit/test_key_echo_app_service.py
def test_key_echo_app_service_stops_echo_on_escape_usage():
    ...
    decision = service.handle_key_event(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.ESCAPE, pressed=True)
    )
    assert decision == KeyEventDecision.SUPPRESS
```

- [ ] **Step 2: Run the key echo tests to verify they fail**

Run: `pytest tests/unit/test_key_echo_use_cases.py tests/unit/test_key_echo_app_service.py -v`
Expected: FAIL because `key_echo` still compares `event.vk` and speaks `VK {event.vk}`.

- [ ] **Step 3: Update key echo hotkeys, mode metadata, spoken output, and bootstrap hotkey usage**

```python
# src/apps/key_echo/use_cases/state_transition_hotkeys.py
from interop.key import HID, KeyEvent

...
    @classmethod
    def default(cls) -> "KeyEchoStateTransitionHotkeyUseCase":
        return cls(
            mapping={
                HID.ENTER: KeyEchoHotkeyAction.START_ECHO,
                HID.ESCAPE: KeyEchoHotkeyAction.STOP_ECHO,
            }
        )

    def match(self, event: KeyEvent) -> KeyEchoHotkeyAction | None:
        if not event.pressed:
            return None
        return self._mapping.get(event.usage)
```

```python
# src/apps/key_echo/use_cases/echo_input.py
class KeyEchoInputUseCase:
    ...
    def handle(self, event: KeyEvent) -> KeyEventDecision:
        if event.pressed:
            self._cancel()
            self._speak(
                SpeechSequence(
                    items=(f"HID 0x{event.usage_page:02X}:0x{event.usage:02X}",)
                )
            )
        return KeyEventDecision.SUPPRESS
```

```python
# src/apps/key_echo/facade.py
from interop.key import HID


class EchoKeysMode:
    mode_id = "echo_keys"
    enter_usage = HID.F10
    exit_usage = HID.ESCAPE
```

```python
# src/bootstrap/platform.py
from interop.key import HID

_DEFAULT_HOTKEY_USAGE = HID.F11
_MACOS_HOTKEY_KEY_CODES: dict[int, int] = {
    HID.F11: 103,
    HID.F10: 109,
    HID.ENTER: 36,
}


def create_hotkey_capture(usage: int = _DEFAULT_HOTKEY_USAGE) -> HotkeyCapture:
    if sys.platform == "darwin":
        ...
        key_code = _MACOS_HOTKEY_KEY_CODES.get(usage)
        if key_code is None:
            raise ValueError(f"Unsupported macOS hotkey usage: 0x{usage:02X}")
        return _MacOSHotkeyCapture(manager=manager, key_code=key_code)
    if sys.platform == "win32":
        return _get_windows_hotkey_capture_class()(usage=usage, label=f"HID_0x{usage:02X}")
```

- [ ] **Step 4: Run the key echo and bootstrap test slice**

Run: `pytest tests/unit/test_key_echo_use_cases.py tests/unit/test_key_echo_app_service.py tests/unit/test_bootstrap_platform.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/apps/key_echo/use_cases/echo_input.py src/apps/key_echo/use_cases/state_transition_hotkeys.py src/apps/key_echo/facade.py src/bootstrap/platform.py tests/unit/test_key_echo_use_cases.py tests/unit/test_key_echo_app_service.py tests/unit/test_bootstrap_platform.py
git commit -m "refactor: move key echo to HID hotkeys"
```

## Task 5: Convert Hotkey Adapters and NVDA Remote Forwarding to HID With a Legacy Payload Adapter

**Files:**
- Modify: `src/adapters/windows/hotkey.py`
- Modify: `src/adapters/macos/hotkey.py`
- Create: `src/apps/nvda_remote/legacy_key_payload.py`
- Modify: `src/apps/nvda_remote/use_cases/state_transition_hotkeys.py`
- Modify: `src/apps/nvda_remote/use_cases/input_forwarding.py`
- Modify: `src/apps/nvda_remote/facade.py`
- Create: `tests/unit/test_nvda_remote_legacy_key_payload.py`
- Modify: `tests/unit/test_nvda_remote_use_cases.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`

- [ ] **Step 1: Write failing tests for HID hotkeys and legacy relay conversion**

```python
# tests/unit/test_nvda_remote_legacy_key_payload.py
from interop.key import HID, KeyEvent
from apps.nvda_remote.legacy_key_payload import key_event_to_legacy_remote_payload


def test_hid_a_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 65,
        "scan_code": 30,
        "extended": False,
        "pressed": True,
    }


def test_hid_f11_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F11, pressed=False)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 122,
        "scan_code": 87,
        "extended": False,
        "pressed": False,
    }
```

```python
# tests/unit/test_nvda_remote_use_cases.py
from interop.key import HID, KeyEvent


def test_nvda_hotkey_use_case_maps_f11_hid_to_toggle_control():
    use_case = NvdaRemoteStateTransitionHotkeyUseCase(
        mapping={HID.F11: NvdaRemoteHotkeyAction.TOGGLE_CONTROL}
    )
    action = use_case.match(KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F11, pressed=True))
    assert action == NvdaRemoteHotkeyAction.TOGGLE_CONTROL
```

```python
# tests/unit/test_nvda_remote_app_service.py
def test_nvda_remote_service_forwards_hid_keys_when_controlling():
    ...
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    decision = service.handle_key_event(event)
    assert decision == KeyEventDecision.SUPPRESS
    assert transport.sent == [
        (
            RemoteMessageType.KEY,
            {"vk_code": 65, "scan_code": 30, "extended": False, "pressed": True},
        )
    ]
```

- [ ] **Step 2: Run the NVDA Remote tests to verify they fail**

Run: `pytest tests/unit/test_nvda_remote_legacy_key_payload.py tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_app_service.py -v`
Expected: FAIL because no HID -> legacy adapter exists and forwarding still sends `event.to_remote_payload()`.

- [ ] **Step 3: Implement HID hotkey adapters and the single legacy payload converter**

```python
# src/adapters/windows/hotkey.py
from interop.key import KeyEvent
from adapters.windows.hid_map import key_event_from_windows

F11_USAGE = 0x44

class WindowsHotkeyCapture:
    def __init__(..., usage: int = F11_USAGE, label: str = "F11") -> None:
        ...
        self._usage = usage


class WindowsKeyPressHotkeyCapture:
    def __init__(..., usage: int) -> None:
        ...
        self._usage = usage

    def _handle_key_event(self, event: KeyEvent) -> KeyEventDecision:
        if event.usage != self._usage or not event.pressed:
            return KeyEventDecision.PASS_THROUGH
        if self._handler is not None:
            self._handler()
        return KeyEventDecision.SUPPRESS
```

```python
# src/apps/nvda_remote/legacy_key_payload.py
from interop.key import HID, KeyEvent

_USAGE_TO_LEGACY: dict[int, tuple[int, int, bool]] = {
    HID.A: (65, 30, False),
    HID.B: (66, 48, False),
    HID.ENTER: (13, 28, False),
    HID.ESCAPE: (27, 1, False),
    HID.TAB: (9, 15, False),
    HID.SPACE: (32, 57, False),
    HID.F11: (122, 87, False),
    HID.LEFT: (37, 75, True),
    HID.RIGHT: (39, 77, True),
    HID.UP: (38, 72, True),
    HID.DOWN: (40, 80, True),
    HID.LEFT_CONTROL: (17, 29, False),
    HID.RIGHT_CONTROL: (17, 29, True),
    HID.LEFT_SHIFT: (16, 42, False),
    HID.RIGHT_SHIFT: (16, 54, False),
    HID.LEFT_ALT: (18, 56, False),
    HID.RIGHT_ALT: (18, 56, True),
}


def key_event_to_legacy_remote_payload(event: KeyEvent) -> dict[str, int | bool]:
    if event.usage_page != HID.KEYBOARD_PAGE:
        raise ValueError(f"Unsupported HID usage page: 0x{event.usage_page:02X}")
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

```python
# src/apps/nvda_remote/use_cases/input_forwarding.py
from apps.nvda_remote.legacy_key_payload import key_event_to_legacy_remote_payload

...
        self._send_key(key_event_to_legacy_remote_payload(event))
        return KeyEventDecision.SUPPRESS
```

```python
# src/apps/nvda_remote/facade.py
from interop.key import HID


class RemoteControlMode:
    mode_id = "remote_control"
    enter_usage = HID.F11
    exit_usage = HID.F11


class NvdaRemoteAppFacade(KeyEventHandler):
    _LOCAL_STOP_USAGE = HID.F11
    ...
    self._suppressed_keyups: set[int] = set()
    ...
            local_stop_usage=self._LOCAL_STOP_USAGE,
    ...
        if not event.pressed and event.usage in self._suppressed_keyups:
            self._suppressed_keyups.discard(event.usage)
            return KeyEventDecision.SUPPRESS
        if event.pressed and event.usage == self._LOCAL_STOP_USAGE and self._mode_manager.active_mode_id is not None:
            self._suppressed_keyups.add(self._LOCAL_STOP_USAGE)
        return self._mode_manager.handle_key_event(event)
```

- [ ] **Step 4: Run the NVDA Remote slice**

Run: `pytest tests/unit/test_nvda_remote_legacy_key_payload.py tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_app_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/windows/hotkey.py src/adapters/macos/hotkey.py src/apps/nvda_remote/legacy_key_payload.py src/apps/nvda_remote/use_cases/state_transition_hotkeys.py src/apps/nvda_remote/use_cases/input_forwarding.py src/apps/nvda_remote/facade.py tests/unit/test_nvda_remote_legacy_key_payload.py tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_app_service.py
git commit -m "feat: add HID forwarding with legacy relay adapter"
```

## Task 6: Finish the Remaining Regression Sweep and Full Test Pass

**Files:**
- Modify: `tests/unit/test_app_wx.py`
- Modify: `tests/unit/test_keyboard_input_service.py`
- Modify: `tests/unit/test_windows_adapters.py`
- Modify: `tests/unit/test_macos_adapters.py`
- Modify: `tests/unit/test_key_echo_app_service.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`
- Modify: `tests/integration/test_relay_session.py`

- [ ] **Step 1: Write or update the remaining regression assertions for HID hotkey factory requests and unchanged wire format**

```python
# tests/unit/test_app_wx.py
from interop.key import HID


def test_build_runtime_requests_hid_f11_hotkey(monkeypatch):
    requested_hotkeys = []
    monkeypatch.setattr(
        main_module,
        "create_hotkey_capture",
        lambda usage=HID.F11: requested_hotkeys.append(usage) or FakeHotkeyCapture(),
    )
    runtime = main_module.build_runtime()
    assert requested_hotkeys == [HID.F11]
```

```python
# tests/integration/test_relay_session.py
def test_relay_transport_still_serializes_legacy_key_payload():
    serializer = JSONSerializer()
    payload = serializer.serialize(
        RemoteMessageType.KEY,
        vk_code=65,
        scan_code=30,
        extended=False,
        pressed=True,
    )
    decoded = serializer.deserialize(payload.strip())
    assert decoded == {
        "type": "key",
        "vk_code": 65,
        "scan_code": 30,
        "extended": False,
        "pressed": True,
    }
```

- [ ] **Step 2: Run the broad regression slice and note any remaining failures**

Run: `pytest tests/unit/test_app_wx.py tests/unit/test_key_echo_app_service.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_windows_adapters.py tests/unit/test_macos_adapters.py tests/integration/test_relay_session.py -v`
Expected: Any remaining failures should now be isolated to missed VK-based assertions or hotkey factory defaults.

- [ ] **Step 3: Resolve the remaining VK-era assertions so the suite is internally consistent**

```python
# tests/unit/test_key_echo_app_service.py
decision = capture.listener(
    KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.B, pressed=True)
)
assert speech_output.calls == [
    ("cancel", None),
    ("speak", SpeechSequence(items=("HID 0x07:0x05",))),
]
```

```python
# tests/unit/test_windows_adapters.py
assert seen == [
    KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.TAB, pressed=True),
    KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.TAB, pressed=False),
]
```

```python
# tests/unit/test_macos_adapters.py
assert seen == [
    KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
]
```

- [ ] **Step 4: Run the full targeted suite**

Run: `pytest tests/unit/test_hid_keys.py tests/unit/test_input_policies.py tests/unit/test_mode_manager.py tests/unit/test_key_echo_use_cases.py tests/unit/test_key_echo_app_service.py tests/unit/test_nvda_remote_legacy_key_payload.py tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_windows_adapters.py tests/unit/test_macos_adapters.py tests/unit/test_bootstrap_platform.py tests/unit/test_app_wx.py tests/unit/test_keyboard_input_service.py tests/integration/test_relay_session.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_app_wx.py tests/unit/test_keyboard_input_service.py tests/unit/test_windows_adapters.py tests/unit/test_macos_adapters.py tests/unit/test_key_echo_app_service.py tests/unit/test_nvda_remote_app_service.py tests/integration/test_relay_session.py
git commit -m "test: complete HID keyboard regression coverage"
```

## Self-Review

### Spec Coverage

- HID core event model: covered by Task 1.
- Windows and macOS normalization to HID: covered by Task 2.
- Shared hotkey/mode logic moved to HID: covered by Task 3.
- `key_echo` internal behavior moved to HID: covered by Task 4.
- NVDA Remote compatibility via single HID -> legacy adapter: covered by Task 5.
- Relay wire format unchanged and regression sweep: covered by Task 6.

### Placeholder Scan

- No `TODO`, `TBD`, or deferred implementation markers are present.
- Each task names exact files and concrete commands.
- Each test and code step includes explicit snippets rather than “similar to previous task”.

### Type Consistency

- Shared event model uses `usage_page`, `usage`, `pressed` everywhere.
- Shared hotkey/mode terms use `enter_usage` and `exit_usage`.
- Legacy relay payload conversion is centralized in `key_event_to_legacy_remote_payload`.
- Hotkey factory signature moves to `usage` consistently across bootstrap and adapters.
