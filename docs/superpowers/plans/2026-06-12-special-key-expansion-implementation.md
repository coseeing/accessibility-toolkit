# Special Key Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the HID-first keyboard model to cover special control keys and common JIS-only keys, with best-effort legacy relay support and explicit local-only behavior for unsupported keys.

**Architecture:** Keep HID as the only shared keyboard representation inside `src/`. Expand `src/interop/key/hid.py` first, then teach the Windows and macOS adapters to normalize the new native events into HID `KeyEvent`s, and finally extend `src/apps/nvda_remote/legacy_key_payload.py` and forwarding tests so relay-capable keys forward and unsupported keys remain suppressed with logging.

**Tech Stack:** Python 3.11, `pytest`, `ctypes`, Quartz/PyObjC adapter shims, dataclasses, existing NVDA Remote legacy relay payload format

---

## File Structure

### Modify

- `src/interop/key/hid.py`
- `src/adapters/windows/hid_map.py`
- `src/adapters/macos/hid_map.py`
- `src/apps/nvda_remote/legacy_key_payload.py`
- `tests/unit/test_hid_keys.py`
- `tests/unit/test_windows_adapters.py`
- `tests/unit/test_macos_adapters.py`
- `tests/unit/test_nvda_remote_legacy_key_payload.py`
- `tests/unit/test_nvda_remote_use_cases.py`

### Responsibilities

- `src/interop/key/hid.py`: canonical `usage page 0x07` constants for special control keys and common JIS-only keys.
- `src/adapters/windows/hid_map.py`: Windows `scanCode + extended (+ vkCode only when needed)` to HID normalization.
- `src/adapters/macos/hid_map.py`: macOS virtual key code to HID normalization.
- `src/apps/nvda_remote/legacy_key_payload.py`: the only HID-to-legacy relay adapter, extended with safe mappings for relay-capable special keys and explicit rejection of local-only keys.
- `tests/unit/test_hid_keys.py`: verifies exact HID constant values and key distinctions.
- `tests/unit/test_windows_adapters.py`: verifies Windows hook normalization for the new special keys and JIS keys.
- `tests/unit/test_macos_adapters.py`: verifies macOS key-code normalization for the new special keys and JIS keys.
- `tests/unit/test_nvda_remote_legacy_key_payload.py`: verifies legacy relay mappings and explicit unsupported behavior.
- `tests/unit/test_nvda_remote_use_cases.py`: verifies forwarding keeps unsupported keys suppressed in control mode.

## Task 1: Expand the Shared HID Constant Set

**Files:**
- Modify: `src/interop/key/hid.py`
- Modify: `tests/unit/test_hid_keys.py`

- [ ] **Step 1: Write the failing HID constant tests**

```python
from interop.key import HID, KeyEvent


def test_hid_constants_cover_special_control_keys():
    assert HID.PRINT_SCREEN == 0x46
    assert HID.SCROLL_LOCK == 0x47
    assert HID.PAUSE == 0x48
    assert HID.NUM_LOCK == 0x53
    assert HID.APPLICATION == 0x65


def test_hid_constants_cover_common_jis_only_keys():
    assert HID.NON_US_HASH == 0x32
    assert HID.INTERNATIONAL1 == 0x87
    assert HID.INTERNATIONAL3 == 0x89
    assert HID.INTERNATIONAL4 == 0x8A
    assert HID.INTERNATIONAL5 == 0x8B


def test_hid_distinguishes_special_and_jis_keys_from_existing_keys():
    assert HID.PRINT_SCREEN != HID.F12
    assert HID.NUM_LOCK != HID.KEYPAD_0
    assert HID.APPLICATION != HID.RIGHT_META
    assert HID.NON_US_HASH != HID.BACKSLASH
```

- [ ] **Step 2: Run the HID constant tests to confirm they fail**

Run: `pytest tests/unit/test_hid_keys.py -v`

Expected: FAIL with `AttributeError` for names such as `PRINT_SCREEN`, `NUM_LOCK`, `NON_US_HASH`, or `INTERNATIONAL1`.

- [ ] **Step 3: Add the missing HID constants in grouped sections**

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _HIDKeyboard:
    KEYBOARD_PAGE: int = 0x07

    # Alphanumeric
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

    # Core controls and punctuation
    ENTER: int = 0x28
    ESCAPE: int = 0x29
    BACKSPACE: int = 0x2A
    TAB: int = 0x2B
    SPACE: int = 0x2C
    MINUS: int = 0x2D
    EQUALS: int = 0x2E
    LEFT_BRACKET: int = 0x2F
    RIGHT_BRACKET: int = 0x30
    BACKSLASH: int = 0x31
    NON_US_HASH: int = 0x32
    SEMICOLON: int = 0x33
    QUOTE: int = 0x34
    GRAVE: int = 0x35
    COMMA: int = 0x36
    PERIOD: int = 0x37
    SLASH: int = 0x38
    CAPS_LOCK: int = 0x39

    # Function and special control keys
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
    PRINT_SCREEN: int = 0x46
    SCROLL_LOCK: int = 0x47
    PAUSE: int = 0x48

    # Navigation and editing
    INSERT: int = 0x49
    HOME: int = 0x4A
    PAGE_UP: int = 0x4B
    DELETE: int = 0x4C
    END: int = 0x4D
    PAGE_DOWN: int = 0x4E
    RIGHT: int = 0x4F
    LEFT: int = 0x50
    DOWN: int = 0x51
    UP: int = 0x52

    # Numpad and application
    NUM_LOCK: int = 0x53
    KEYPAD_DIVIDE: int = 0x54
    KEYPAD_MULTIPLY: int = 0x55
    KEYPAD_SUBTRACT: int = 0x56
    KEYPAD_ADD: int = 0x57
    KEYPAD_ENTER: int = 0x58
    KEYPAD_1: int = 0x59
    KEYPAD_2: int = 0x5A
    KEYPAD_3: int = 0x5B
    KEYPAD_4: int = 0x5C
    KEYPAD_5: int = 0x5D
    KEYPAD_6: int = 0x5E
    KEYPAD_7: int = 0x5F
    KEYPAD_8: int = 0x60
    KEYPAD_9: int = 0x61
    KEYPAD_0: int = 0x62
    KEYPAD_DECIMAL: int = 0x63
    NON_US_BACKSLASH: int = 0x64
    APPLICATION: int = 0x65
    KEYPAD_EQUALS: int = 0x67

    # International / JIS
    INTERNATIONAL1: int = 0x87
    INTERNATIONAL3: int = 0x89
    INTERNATIONAL4: int = 0x8A
    INTERNATIONAL5: int = 0x8B

    # Modifiers
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

- [ ] **Step 4: Run the HID tests again**

Run: `pytest tests/unit/test_hid_keys.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/interop/key/hid.py tests/unit/test_hid_keys.py
git commit -m "feat: add hid support for special and jis keys"
```

## Task 2: Add Windows HID Normalization for Special and JIS Keys

**Files:**
- Modify: `src/adapters/windows/hid_map.py`
- Modify: `tests/unit/test_windows_adapters.py`

- [ ] **Step 1: Write failing Windows adapter tests for special keys**

```python
def test_windows_keyboard_hook_emits_hid_for_print_screen_scroll_lock_pause_num_lock_and_application():
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

    callback(0, WM_KEYDOWN, ctypes.addressof(FakeKbdLlHookStruct(vkCode=0x2C, scanCode=55, flags=LLKHF_EXTENDED)))
    callback(0, WM_KEYDOWN, ctypes.addressof(FakeKbdLlHookStruct(vkCode=0x91, scanCode=70, flags=0)))
    callback(0, WM_KEYDOWN, ctypes.addressof(FakeKbdLlHookStruct(vkCode=0x13, scanCode=69, flags=0)))
    callback(0, WM_KEYDOWN, ctypes.addressof(FakeKbdLlHookStruct(vkCode=0x90, scanCode=69, flags=LLKHF_EXTENDED)))
    callback(0, WM_KEYDOWN, ctypes.addressof(FakeKbdLlHookStruct(vkCode=0x5D, scanCode=93, flags=LLKHF_EXTENDED)))

    assert seen == [
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.PRINT_SCREEN, pressed=True),
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.SCROLL_LOCK, pressed=True),
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.PAUSE, pressed=True),
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.NUM_LOCK, pressed=True),
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.APPLICATION, pressed=True),
    ]
```

- [ ] **Step 2: Write failing Windows adapter tests for JIS keys**

```python
def test_windows_keyboard_hook_emits_hid_for_common_jis_keys_when_available():
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

    callback(0, WM_KEYDOWN, ctypes.addressof(FakeKbdLlHookStruct(vkCode=0xC0, scanCode=41, flags=0)))
    callback(0, WM_KEYDOWN, ctypes.addressof(FakeKbdLlHookStruct(vkCode=0xE2, scanCode=115, flags=0)))
    callback(0, WM_KEYDOWN, ctypes.addressof(FakeKbdLlHookStruct(vkCode=0xF3, scanCode=121, flags=0)))
    callback(0, WM_KEYDOWN, ctypes.addressof(FakeKbdLlHookStruct(vkCode=0xF4, scanCode=123, flags=0)))

    assert seen == [
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.NON_US_HASH, pressed=True),
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.INTERNATIONAL1, pressed=True),
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.INTERNATIONAL4, pressed=True),
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.INTERNATIONAL5, pressed=True),
    ]
```

- [ ] **Step 3: Run the Windows adapter tests to confirm they fail**

Run: `pytest tests/unit/test_windows_adapters.py::test_windows_keyboard_hook_emits_hid_for_print_screen_scroll_lock_pause_num_lock_and_application tests/unit/test_windows_adapters.py::test_windows_keyboard_hook_emits_hid_for_common_jis_keys_when_available -v`

Expected: FAIL with `seen == []` or missing events because `_SCAN_TO_USAGE` has no entries for the new keys.

- [ ] **Step 4: Add the Windows scan-code mappings**

```python
from interop.key import HID, KeyEvent

_SCAN_TO_USAGE: dict[tuple[int, bool], int] = {
    # ...existing entries...
    (55, True): HID.PRINT_SCREEN,
    (70, False): HID.SCROLL_LOCK,
    (69, False): HID.PAUSE,
    (69, True): HID.NUM_LOCK,
    (93, True): HID.APPLICATION,
    (41, False): HID.NON_US_HASH,
    (115, False): HID.INTERNATIONAL1,
    (121, False): HID.INTERNATIONAL4,
    (123, False): HID.INTERNATIONAL5,
}


def key_event_from_windows(*, vk_code: int, scan_code: int, extended: bool, pressed: bool) -> KeyEvent | None:
    usage = _SCAN_TO_USAGE.get((scan_code, extended))
    if usage is None and vk_code == 0xF2:
        usage = HID.INTERNATIONAL3
    if usage is None:
        return None
    return KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=pressed)
```

- [ ] **Step 5: Add the direct `vkCode` fallback test for `INTERNATIONAL3`**

```python
def test_windows_key_event_from_windows_maps_international3_via_vkcode_fallback():
    assert key_event_from_windows(
        vk_code=0xF2,
        scan_code=0,
        extended=False,
        pressed=True,
    ) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.INTERNATIONAL3,
        pressed=True,
    )
```

- [ ] **Step 6: Run the Windows adapter tests again**

Run: `pytest tests/unit/test_windows_adapters.py::test_windows_keyboard_hook_emits_hid_for_print_screen_scroll_lock_pause_num_lock_and_application tests/unit/test_windows_adapters.py::test_windows_keyboard_hook_emits_hid_for_common_jis_keys_when_available tests/unit/test_windows_adapters.py::test_windows_key_event_from_windows_maps_international3_via_vkcode_fallback -v`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/adapters/windows/hid_map.py tests/unit/test_windows_adapters.py
git commit -m "feat: add windows hid mappings for special and jis keys"
```

## Task 3: Add macOS HID Normalization for Special and JIS Keys

**Files:**
- Modify: `src/adapters/macos/hid_map.py`
- Modify: `tests/unit/test_macos_adapters.py`

- [ ] **Step 1: Write failing macOS adapter tests for special keys**

```python
def test_key_event_from_macos_maps_special_control_keys_to_hid():
    assert key_event_from_macos(key_code=105, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.PRINT_SCREEN,
        pressed=True,
    )
    assert key_event_from_macos(key_code=107, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.SCROLL_LOCK,
        pressed=True,
    )
    assert key_event_from_macos(key_code=113, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.PAUSE,
        pressed=True,
    )
    assert key_event_from_macos(key_code=71, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.NUM_LOCK,
        pressed=True,
    )
    assert key_event_from_macos(key_code=110, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.APPLICATION,
        pressed=True,
    )
```

- [ ] **Step 2: Write failing macOS adapter tests for JIS keys**

```python
def test_key_event_from_macos_maps_common_jis_keys_to_hid():
    assert key_event_from_macos(key_code=94, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.NON_US_HASH,
        pressed=True,
    )
    assert key_event_from_macos(key_code=93, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.INTERNATIONAL1,
        pressed=True,
    )
    assert key_event_from_macos(key_code=102, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.INTERNATIONAL3,
        pressed=True,
    )
    assert key_event_from_macos(key_code=104, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.INTERNATIONAL4,
        pressed=True,
    )
    assert key_event_from_macos(key_code=95, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.INTERNATIONAL5,
        pressed=True,
    )
```

- [ ] **Step 3: Run the macOS adapter tests to confirm they fail**

Run: `pytest tests/unit/test_macos_adapters.py::test_key_event_from_macos_maps_special_control_keys_to_hid tests/unit/test_macos_adapters.py::test_key_event_from_macos_maps_common_jis_keys_to_hid -v`

Expected: FAIL because `KEYCODE_TO_USAGE` does not yet include the new key codes.

- [ ] **Step 4: Add the macOS key-code mappings**

```python
from interop.key import HID

KEYCODE_TO_USAGE: dict[int, int] = {
    # ...existing entries...
    71: HID.NUM_LOCK,
    93: HID.INTERNATIONAL1,
    94: HID.NON_US_HASH,
    95: HID.INTERNATIONAL5,
    102: HID.INTERNATIONAL3,
    104: HID.INTERNATIONAL4,
    105: HID.PRINT_SCREEN,
    107: HID.SCROLL_LOCK,
    110: HID.APPLICATION,
    113: HID.PAUSE,
}
```

- [ ] **Step 5: Run the macOS adapter tests again**

Run: `pytest tests/unit/test_macos_adapters.py::test_key_event_from_macos_maps_special_control_keys_to_hid tests/unit/test_macos_adapters.py::test_key_event_from_macos_maps_common_jis_keys_to_hid -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/adapters/macos/hid_map.py tests/unit/test_macos_adapters.py
git commit -m "feat: add macos hid mappings for special and jis keys"
```

## Task 4: Extend Relay Mapping and Preserve Local-Only Safety

**Files:**
- Modify: `src/apps/nvda_remote/legacy_key_payload.py`
- Modify: `tests/unit/test_nvda_remote_legacy_key_payload.py`
- Modify: `tests/unit/test_nvda_remote_use_cases.py`

- [ ] **Step 1: Write failing relay adapter tests for relay-capable special keys**

```python
def test_print_screen_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.PRINT_SCREEN, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 44,
        "scan_code": 55,
        "extended": True,
        "pressed": True,
    }


def test_scroll_lock_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.SCROLL_LOCK, pressed=False)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 145,
        "scan_code": 70,
        "extended": False,
        "pressed": False,
    }


def test_num_lock_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.NUM_LOCK, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 144,
        "scan_code": 69,
        "extended": True,
        "pressed": True,
    }


def test_application_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.APPLICATION, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 93,
        "scan_code": 93,
        "extended": True,
        "pressed": True,
    }
```

- [ ] **Step 2: Write failing relay adapter tests for local-only keys**

```python
def test_pause_is_explicitly_unsupported_for_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.PAUSE, pressed=True)
    try:
        key_event_to_legacy_remote_payload(event)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "PAUSE" in str(exc)


def test_jis_keys_are_explicitly_unsupported_for_legacy_remote_payload():
    for usage_name, usage in [
        ("NON_US_HASH", HID.NON_US_HASH),
        ("INTERNATIONAL1", HID.INTERNATIONAL1),
        ("INTERNATIONAL3", HID.INTERNATIONAL3),
        ("INTERNATIONAL4", HID.INTERNATIONAL4),
        ("INTERNATIONAL5", HID.INTERNATIONAL5),
    ]:
        try:
            key_event_to_legacy_remote_payload(
                KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=True)
            )
            assert False, f"Expected ValueError for {usage_name}"
        except ValueError as exc:
            assert usage_name in str(exc)
```

- [ ] **Step 3: Write the forwarding safety regression test**

```python
def test_forwarding_suppresses_unsupported_jis_key_in_control_mode(caplog):
    import logging
    from apps.nvda_remote.use_cases.input_forwarding import NvdaRemoteInputForwardingUseCase

    logging.getLogger("apps.nvda_remote.use_cases.input_forwarding").setLevel(logging.DEBUG)

    sent = []
    use_case = NvdaRemoteInputForwardingUseCase(
        is_connected=lambda: True,
        is_controlling=lambda: True,
        send_key=lambda payload: sent.append(payload),
        on_local_stop=lambda: None,
    )

    decision = use_case.handle(
        KeyEvent(
            usage_page=HID.KEYBOARD_PAGE,
            usage=HID.INTERNATIONAL3,
            pressed=True,
        )
    )

    assert decision == KeyEventDecision.SUPPRESS
    assert sent == []
    assert "0x89" in caplog.text
    assert "unsupported usage" in caplog.text
```

- [ ] **Step 4: Run the relay and forwarding tests to confirm they fail**

Run: `pytest tests/unit/test_nvda_remote_legacy_key_payload.py tests/unit/test_nvda_remote_use_cases.py::test_forwarding_suppresses_unsupported_jis_key_in_control_mode -v`

Expected: FAIL because `_USAGE_TO_LEGACY` does not yet include the relay-capable special keys and because unsupported JIS keys do not yet raise named `ValueError`s.

- [ ] **Step 5: Add the relay mappings and explicit unsupported names**

```python
from interop.key import HID, KeyEvent

_USAGE_TO_LEGACY: dict[int, tuple[int, int, bool]] = {
    # ...existing entries...
    HID.PRINT_SCREEN: (44, 55, True),
    HID.SCROLL_LOCK: (145, 70, False),
    HID.NUM_LOCK: (144, 69, True),
    HID.APPLICATION: (93, 93, True),
}

_EXPLICIT_UNSUPPORTED: dict[int, str] = {
    HID.NON_US_BACKSLASH: "NON_US_BACKSLASH",
    HID.PAUSE: "PAUSE",
    HID.NON_US_HASH: "NON_US_HASH",
    HID.INTERNATIONAL1: "INTERNATIONAL1",
    HID.INTERNATIONAL3: "INTERNATIONAL3",
    HID.INTERNATIONAL4: "INTERNATIONAL4",
    HID.INTERNATIONAL5: "INTERNATIONAL5",
}


def key_event_to_legacy_remote_payload(event: KeyEvent) -> dict[str, int | bool]:
    if event.usage_page != HID.KEYBOARD_PAGE:
        raise ValueError(f"Unsupported HID usage page: 0x{event.usage_page:02X}")
    unsupported_name = _EXPLICIT_UNSUPPORTED.get(event.usage)
    if unsupported_name is not None:
        raise ValueError(f"Unsupported HID usage for legacy relay: {unsupported_name}")
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

- [ ] **Step 6: Run the relay and forwarding tests again**

Run: `pytest tests/unit/test_nvda_remote_legacy_key_payload.py tests/unit/test_nvda_remote_use_cases.py::test_forwarding_suppresses_unsupported_jis_key_in_control_mode -v`

Expected: PASS

- [ ] **Step 7: Run the full focused suite**

Run: `pytest tests/unit/test_hid_keys.py tests/unit/test_windows_adapters.py tests/unit/test_macos_adapters.py tests/unit/test_nvda_remote_legacy_key_payload.py tests/unit/test_nvda_remote_use_cases.py -v`

Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/apps/nvda_remote/legacy_key_payload.py tests/unit/test_nvda_remote_legacy_key_payload.py tests/unit/test_nvda_remote_use_cases.py
git commit -m "feat: add relay support for special keys"
```
