# HID 104-Key Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the existing HID-first keyboard model to full ANSI 104-key coverage plus the ISO extra key in platform normalization, and complete ANSI relay compatibility without changing the current relay wire format.

**Architecture:** Keep the current layering unchanged. `src/interop/key` remains the single shared HID model, Windows and macOS adapters continue to normalize native events into HID `KeyEvent`s, and `src/apps/nvda_remote/legacy_key_payload.py` remains the only HID-to-legacy relay adapter. ANSI 104-key coverage must be complete end to end, while `NonUsBackslash` may remain local-only if the relay mapping is not reliable.

**Tech Stack:** Python 3.11, `pytest`, `ctypes`, Quartz/PyObjC adapter shims, dataclasses, existing NVDA Remote legacy relay payload format

---

## File Structure

### Modify

- `src/interop/key/hid.py`
- `src/adapters/windows/hid_map.py`
- `src/adapters/macos/hid_map.py`
- `src/apps/nvda_remote/legacy_key_payload.py`
- `src/apps/nvda_remote/use_cases/input_forwarding.py`
- `tests/unit/test_hid_keys.py`
- `tests/unit/test_windows_adapters.py`
- `tests/unit/test_macos_adapters.py`
- `tests/unit/test_nvda_remote_legacy_key_payload.py`
- `tests/unit/test_nvda_remote_use_cases.py`

### Responsibilities

- `src/interop/key/hid.py`: canonical HID `usage page 0x07` constants used everywhere else in the project.
- `src/adapters/windows/hid_map.py`: Windows `scanCode + extended` to HID usage normalization for ordinary desktop keyboard keys.
- `src/adapters/macos/hid_map.py`: macOS `key_code` to HID usage normalization for the same key set.
- `src/apps/nvda_remote/legacy_key_payload.py`: ANSI 104-key HID to legacy `vk_code/scan_code/extended/pressed` adapter.
- `src/apps/nvda_remote/use_cases/input_forwarding.py`: keeps the safety rule for unsupported relay keys explicit and unchanged.
- `tests/unit/test_hid_keys.py`: verifies newly added HID constants and key distinctions.
- `tests/unit/test_windows_adapters.py`: verifies Windows capture emits the correct HID events for the expanded key set.
- `tests/unit/test_macos_adapters.py`: verifies macOS key translation emits the correct HID events for the expanded key set.
- `tests/unit/test_nvda_remote_legacy_key_payload.py`: verifies ANSI 104-key relay mappings and explicit ISO rejection behavior.
- `tests/unit/test_nvda_remote_use_cases.py`: verifies unsupported relay keys are suppressed and logged in control mode.

## Task 1: Expand the Shared HID Constant Set

**Files:**
- Modify: `src/interop/key/hid.py`
- Modify: `tests/unit/test_hid_keys.py`

- [ ] **Step 1: Write the failing HID constant tests**

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


def test_hid_constants_cover_main_cluster_punctuation_navigation_and_numpad():
    assert HID.SEMICOLON == 0x33
    assert HID.QUOTE == 0x34
    assert HID.GRAVE == 0x35
    assert HID.COMMA == 0x36
    assert HID.PERIOD == 0x37
    assert HID.SLASH == 0x38
    assert HID.CAPS_LOCK == 0x39
    assert HID.INSERT == 0x49
    assert HID.HOME == 0x4A
    assert HID.PAGE_UP == 0x4B
    assert HID.DELETE == 0x4C
    assert HID.END == 0x4D
    assert HID.PAGE_DOWN == 0x4E
    assert HID.KEYPAD_DIVIDE == 0x54
    assert HID.KEYPAD_MULTIPLY == 0x55
    assert HID.KEYPAD_SUBTRACT == 0x56
    assert HID.KEYPAD_ADD == 0x57
    assert HID.KEYPAD_1 == 0x59
    assert HID.KEYPAD_0 == 0x62
    assert HID.KEYPAD_DECIMAL == 0x63
    assert HID.NON_US_BACKSLASH == 0x64
    assert HID.KEYPAD_EQUALS == 0x67


def test_hid_distinguishes_main_cluster_from_numpad_keys():
    assert HID.ENTER != HID.KEYPAD_ENTER
    assert HID.DIGIT_1 != HID.KEYPAD_1
    assert HID.SLASH != HID.KEYPAD_DIVIDE
    assert HID.PERIOD != HID.KEYPAD_DECIMAL
```

- [ ] **Step 2: Run the HID tests to confirm the missing constants fail**

Run: `pytest tests/unit/test_hid_keys.py -v`

Expected: FAIL with `AttributeError` for names such as `SEMICOLON`, `INSERT`, `KEYPAD_1`, or `NON_US_BACKSLASH`.

- [ ] **Step 3: Add the missing HID constants in grouped sections**

```python
# src/interop/key/hid.py
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _HIDKeyboard:
    KEYBOARD_PAGE: int = 0x07

    # Alphanumeric
    A: int = 0x04
    Z: int = 0x1D
    DIGIT_1: int = 0x1E
    DIGIT_0: int = 0x27

    # Core controls and main-cluster punctuation
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
    SEMICOLON: int = 0x33
    QUOTE: int = 0x34
    GRAVE: int = 0x35
    COMMA: int = 0x36
    PERIOD: int = 0x37
    SLASH: int = 0x38
    CAPS_LOCK: int = 0x39

    # Function keys
    F1: int = 0x3A
    F12: int = 0x45

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

    # Numpad
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
    KEYPAD_EQUALS: int = 0x67

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

- [ ] **Step 5: Commit the HID constant expansion**

```bash
git add src/interop/key/hid.py tests/unit/test_hid_keys.py
git commit -m "feat: expand hid constants for 104-key coverage"
```

## Task 2: Complete Windows HID Normalization for ANSI 104-Key and ISO Extra Key

**Files:**
- Modify: `src/adapters/windows/hid_map.py`
- Modify: `tests/unit/test_windows_adapters.py`

- [ ] **Step 1: Write failing Windows adapter tests for punctuation, navigation, numpad, and ISO**

```python
# tests/unit/test_windows_adapters.py
def test_windows_keyboard_hook_emits_hid_for_semicolon_and_quote():
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

    callback(0, WM_KEYDOWN, ctypes.addressof(FakeKbdLlHookStruct(vkCode=0xBA, scanCode=39, flags=0)))
    callback(0, WM_KEYDOWN, ctypes.addressof(FakeKbdLlHookStruct(vkCode=0xDE, scanCode=40, flags=0)))

    assert seen == [
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.SEMICOLON, pressed=True),
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.QUOTE, pressed=True),
    ]


def test_windows_keyboard_hook_emits_hid_for_insert_delete_and_page_down():
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

    callback(0, WM_KEYDOWN, ctypes.addressof(FakeKbdLlHookStruct(vkCode=0x2D, scanCode=82, flags=LLKHF_EXTENDED)))
    callback(0, WM_KEYDOWN, ctypes.addressof(FakeKbdLlHookStruct(vkCode=0x2E, scanCode=83, flags=LLKHF_EXTENDED)))
    callback(0, WM_KEYDOWN, ctypes.addressof(FakeKbdLlHookStruct(vkCode=0x22, scanCode=81, flags=LLKHF_EXTENDED)))

    assert seen == [
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.INSERT, pressed=True),
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.DELETE, pressed=True),
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.PAGE_DOWN, pressed=True),
    ]


def test_windows_keyboard_hook_distinguishes_numpad_from_main_cluster_keys():
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

    callback(0, WM_KEYDOWN, ctypes.addressof(FakeKbdLlHookStruct(vkCode=0x61, scanCode=79, flags=0)))
    callback(0, WM_KEYDOWN, ctypes.addressof(FakeKbdLlHookStruct(vkCode=0x6F, scanCode=53, flags=LLKHF_EXTENDED)))
    callback(0, WM_KEYDOWN, ctypes.addressof(FakeKbdLlHookStruct(vkCode=0x6E, scanCode=83, flags=0)))

    assert seen == [
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_1, pressed=True),
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_DIVIDE, pressed=True),
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_DECIMAL, pressed=True),
    ]


def test_windows_keyboard_hook_emits_hid_for_non_us_backslash_when_available():
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

    callback(0, WM_KEYDOWN, ctypes.addressof(FakeKbdLlHookStruct(vkCode=0xE2, scanCode=86, flags=0)))

    assert seen == [
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.NON_US_BACKSLASH, pressed=True),
    ]
```

- [ ] **Step 2: Run the Windows adapter tests to confirm missing mappings**

Run: `pytest tests/unit/test_windows_adapters.py -k "semicolon or insert or numpad or non_us_backslash" -v`

Expected: FAIL because one or more events are dropped or mapped to the wrong HID usage.

- [ ] **Step 3: Extend the Windows scan-code table without changing capture flow**

```python
# src/adapters/windows/hid_map.py
from interop.key import HID


SCAN_CODE_TO_USAGE = {
    (12, False): HID.MINUS,
    (13, False): HID.EQUALS,
    (26, False): HID.LEFT_BRACKET,
    (27, False): HID.RIGHT_BRACKET,
    (43, False): HID.BACKSLASH,
    (39, False): HID.SEMICOLON,
    (40, False): HID.QUOTE,
    (41, False): HID.GRAVE,
    (51, False): HID.COMMA,
    (52, False): HID.PERIOD,
    (53, False): HID.SLASH,
    (58, False): HID.CAPS_LOCK,
    (82, True): HID.INSERT,
    (83, True): HID.DELETE,
    (71, True): HID.HOME,
    (79, True): HID.END,
    (73, True): HID.PAGE_UP,
    (81, True): HID.PAGE_DOWN,
    (55, True): HID.KEYPAD_DIVIDE,
    (55, False): HID.KEYPAD_MULTIPLY,
    (74, False): HID.KEYPAD_SUBTRACT,
    (78, False): HID.KEYPAD_ADD,
    (79, False): HID.KEYPAD_1,
    (80, False): HID.KEYPAD_2,
    (81, False): HID.KEYPAD_3,
    (75, False): HID.KEYPAD_4,
    (76, False): HID.KEYPAD_5,
    (77, False): HID.KEYPAD_6,
    (71, False): HID.KEYPAD_7,
    (72, False): HID.KEYPAD_8,
    (73, False): HID.KEYPAD_9,
    (82, False): HID.KEYPAD_0,
    (83, False): HID.KEYPAD_DECIMAL,
    (86, False): HID.NON_US_BACKSLASH,
}
```

- [ ] **Step 4: Run the focused Windows tests and then the full Windows adapter file**

Run: `pytest tests/unit/test_windows_adapters.py -k "semicolon or insert or numpad or non_us_backslash" -v`

Expected: PASS

Run: `pytest tests/unit/test_windows_adapters.py -v`

Expected: PASS

- [ ] **Step 5: Commit the Windows mapping expansion**

```bash
git add src/adapters/windows/hid_map.py tests/unit/test_windows_adapters.py
git commit -m "feat: expand windows hid mappings for 104-key coverage"
```

## Task 3: Complete macOS HID Normalization for ANSI 104-Key and ISO Extra Key

**Files:**
- Modify: `src/adapters/macos/hid_map.py`
- Modify: `tests/unit/test_macos_adapters.py`

- [ ] **Step 1: Write failing macOS mapping tests for punctuation, navigation, numpad, and ISO**

```python
# tests/unit/test_macos_adapters.py
def test_key_event_from_macos_maps_semicolon_quote_and_grave_to_hid():
    assert key_event_from_macos(key_code=41, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.SEMICOLON,
        pressed=True,
    )
    assert key_event_from_macos(key_code=39, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.QUOTE,
        pressed=True,
    )
    assert key_event_from_macos(key_code=50, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.GRAVE,
        pressed=True,
    )


def test_key_event_from_macos_maps_navigation_keys_to_hid():
    assert key_event_from_macos(key_code=114, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.INSERT,
        pressed=True,
    )
    assert key_event_from_macos(key_code=117, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.DELETE,
        pressed=True,
    )
    assert key_event_from_macos(key_code=121, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.PAGE_DOWN,
        pressed=True,
    )


def test_key_event_from_macos_distinguishes_numpad_keys_from_main_cluster_keys():
    assert key_event_from_macos(key_code=83, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.KEYPAD_1,
        pressed=True,
    )
    assert key_event_from_macos(key_code=75, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.KEYPAD_DIVIDE,
        pressed=True,
    )
    assert key_event_from_macos(key_code=65, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.KEYPAD_DECIMAL,
        pressed=True,
    )


def test_key_event_from_macos_maps_non_us_backslash_to_hid():
    assert key_event_from_macos(key_code=10, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.NON_US_BACKSLASH,
        pressed=True,
    )
```

- [ ] **Step 2: Run the focused macOS tests to confirm the gaps**

Run: `pytest tests/unit/test_macos_adapters.py -k "semicolon or navigation or numpad or non_us_backslash" -v`

Expected: FAIL because one or more `key_code` values still return `None` or the wrong HID usage.

- [ ] **Step 3: Extend the macOS key-code table in place**

```python
# src/adapters/macos/hid_map.py
from interop.key import HID


KEYCODE_TO_USAGE = {
    24: HID.EQUALS,
    27: HID.MINUS,
    30: HID.RIGHT_BRACKET,
    33: HID.LEFT_BRACKET,
    42: HID.BACKSLASH,
    41: HID.SEMICOLON,
    39: HID.QUOTE,
    50: HID.GRAVE,
    43: HID.COMMA,
    47: HID.PERIOD,
    44: HID.SLASH,
    57: HID.CAPS_LOCK,
    114: HID.INSERT,
    117: HID.DELETE,
    115: HID.HOME,
    119: HID.END,
    116: HID.PAGE_UP,
    121: HID.PAGE_DOWN,
    75: HID.KEYPAD_DIVIDE,
    67: HID.KEYPAD_MULTIPLY,
    78: HID.KEYPAD_SUBTRACT,
    69: HID.KEYPAD_ADD,
    76: HID.KEYPAD_ENTER,
    83: HID.KEYPAD_1,
    84: HID.KEYPAD_2,
    85: HID.KEYPAD_3,
    86: HID.KEYPAD_4,
    87: HID.KEYPAD_5,
    88: HID.KEYPAD_6,
    89: HID.KEYPAD_7,
    91: HID.KEYPAD_8,
    92: HID.KEYPAD_9,
    82: HID.KEYPAD_0,
    65: HID.KEYPAD_DECIMAL,
    81: HID.KEYPAD_EQUALS,
    10: HID.NON_US_BACKSLASH,
}
```

- [ ] **Step 4: Run the focused macOS tests and then the full macOS adapter file**

Run: `pytest tests/unit/test_macos_adapters.py -k "semicolon or navigation or numpad or non_us_backslash" -v`

Expected: PASS

Run: `pytest tests/unit/test_macos_adapters.py -v`

Expected: PASS

- [ ] **Step 5: Commit the macOS mapping expansion**

```bash
git add src/adapters/macos/hid_map.py tests/unit/test_macos_adapters.py
git commit -m "feat: expand macos hid mappings for 104-key coverage"
```

## Task 4: Complete ANSI 104-Key Relay Mapping and Keep ISO Explicitly Unsupported

**Files:**
- Modify: `src/apps/nvda_remote/legacy_key_payload.py`
- Modify: `tests/unit/test_nvda_remote_legacy_key_payload.py`

- [ ] **Step 1: Write failing relay adapter tests for punctuation, navigation, numpad, and ISO rejection**

```python
# tests/unit/test_nvda_remote_legacy_key_payload.py
def test_hid_semicolon_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.SEMICOLON, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 186,
        "scan_code": 39,
        "extended": False,
        "pressed": True,
    }


def test_hid_page_down_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.PAGE_DOWN, pressed=False)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 34,
        "scan_code": 81,
        "extended": True,
        "pressed": False,
    }


def test_hid_keypad_1_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_1, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 97,
        "scan_code": 79,
        "extended": False,
        "pressed": True,
    }


def test_hid_keypad_divide_maps_to_legacy_remote_payload():
    event = KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_DIVIDE, pressed=True)
    assert key_event_to_legacy_remote_payload(event) == {
        "vk_code": 111,
        "scan_code": 53,
        "extended": True,
        "pressed": True,
    }


def test_non_us_backslash_is_explicitly_unsupported_for_legacy_remote_payload():
    event = KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.NON_US_BACKSLASH,
        pressed=True,
    )
    try:
        key_event_to_legacy_remote_payload(event)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "NON_US_BACKSLASH" in str(exc)
```

- [ ] **Step 2: Run the relay adapter tests to verify the missing coverage**

Run: `pytest tests/unit/test_nvda_remote_legacy_key_payload.py -k "semicolon or page_down or keypad or non_us_backslash" -v`

Expected: FAIL because ANSI keys are missing or `NON_US_BACKSLASH` is not rejected explicitly.

- [ ] **Step 3: Add the missing ANSI mappings and leave ISO unsupported on purpose**

```python
# src/apps/nvda_remote/legacy_key_payload.py
from interop.key import HID


USAGE_TO_LEGACY_KEY = {
    HID.LEFT_BRACKET: (219, 26, False),
    HID.RIGHT_BRACKET: (221, 27, False),
    HID.BACKSLASH: (220, 43, False),
    HID.SEMICOLON: (186, 39, False),
    HID.QUOTE: (222, 40, False),
    HID.GRAVE: (192, 41, False),
    HID.COMMA: (188, 51, False),
    HID.PERIOD: (190, 52, False),
    HID.SLASH: (191, 53, False),
    HID.CAPS_LOCK: (20, 58, False),
    HID.INSERT: (45, 82, True),
    HID.DELETE: (46, 83, True),
    HID.HOME: (36, 71, True),
    HID.END: (35, 79, True),
    HID.PAGE_UP: (33, 73, True),
    HID.PAGE_DOWN: (34, 81, True),
    HID.KEYPAD_DIVIDE: (111, 53, True),
    HID.KEYPAD_MULTIPLY: (106, 55, False),
    HID.KEYPAD_SUBTRACT: (109, 74, False),
    HID.KEYPAD_ADD: (107, 78, False),
    HID.KEYPAD_1: (97, 79, False),
    HID.KEYPAD_2: (98, 80, False),
    HID.KEYPAD_3: (99, 81, False),
    HID.KEYPAD_4: (100, 75, False),
    HID.KEYPAD_5: (101, 76, False),
    HID.KEYPAD_6: (102, 77, False),
    HID.KEYPAD_7: (103, 71, False),
    HID.KEYPAD_8: (104, 72, False),
    HID.KEYPAD_9: (105, 73, False),
    HID.KEYPAD_0: (96, 82, False),
    HID.KEYPAD_DECIMAL: (110, 83, False),
    HID.KEYPAD_EQUALS: (187, 13, False),
}


def key_event_to_legacy_remote_payload(event):
    if not HID.is_keyboard_page(event.usage_page):
        raise ValueError(f"Unsupported usage page: {event.usage_page}")
    if event.usage == HID.NON_US_BACKSLASH:
        raise ValueError("Unsupported HID usage for legacy relay: NON_US_BACKSLASH")
```

- [ ] **Step 4: Run the focused relay tests and then the full relay adapter file**

Run: `pytest tests/unit/test_nvda_remote_legacy_key_payload.py -k "semicolon or page_down or keypad or non_us_backslash" -v`

Expected: PASS

Run: `pytest tests/unit/test_nvda_remote_legacy_key_payload.py -v`

Expected: PASS

- [ ] **Step 5: Commit the relay adapter expansion**

```bash
git add src/apps/nvda_remote/legacy_key_payload.py tests/unit/test_nvda_remote_legacy_key_payload.py
git commit -m "feat: complete ansi hid relay mappings"
```

## Task 5: Lock In Unsupported Relay Suppression for ISO Extra Key

**Files:**
- Modify: `src/apps/nvda_remote/use_cases/input_forwarding.py`
- Modify: `tests/unit/test_nvda_remote_use_cases.py`

- [ ] **Step 1: Write the failing forwarding test for unsupported ISO relay keys**

```python
# tests/unit/test_nvda_remote_use_cases.py
from adapters.inputs.base import KeyEventDecision
from interop.key import HID, KeyEvent


def test_forwarding_suppresses_unsupported_non_us_backslash_in_control_mode():
    logs = []
    sent = []

    class FakeTransport:
        def send_key(self, payload):
            sent.append(payload)

    use_case = NvdaRemoteInputForwardingUseCase(
        mode_getter=lambda: "control",
        sender=FakeTransport(),
        logger=lambda message: logs.append(message),
    )

    decision = use_case.handle_key_event(
        KeyEvent(
            usage_page=HID.KEYBOARD_PAGE,
            usage=HID.NON_US_BACKSLASH,
            pressed=True,
        )
    )

    assert decision == KeyEventDecision.SUPPRESS
    assert sent == []
    assert any("NON_US_BACKSLASH" in message for message in logs)
```

- [ ] **Step 2: Run the forwarding test to confirm the safety contract is enforced explicitly**

Run: `pytest tests/unit/test_nvda_remote_use_cases.py -k "non_us_backslash" -v`

Expected: FAIL if the use case does not log the unsupported HID usage clearly or if the test fixture shape no longer matches the actual constructor.

- [ ] **Step 3: Keep the current suppression behavior explicit in the use case**

```python
# src/apps/nvda_remote/use_cases/input_forwarding.py
from adapters.inputs.base import KeyEventDecision
from apps.nvda_remote.legacy_key_payload import key_event_to_legacy_remote_payload


def handle_key_event(self, event):
    if not self._is_controlling():
        return KeyEventDecision.PASS_THROUGH
    try:
        payload = key_event_to_legacy_remote_payload(event)
    except ValueError as exc:
        self._logger(f"Suppressing unsupported relay HID key: {exc}")
        return KeyEventDecision.SUPPRESS
    self._sender.send_key(payload)
    return KeyEventDecision.SUPPRESS
```

- [ ] **Step 4: Run the focused forwarding test and then the directly related unit suite**

Run: `pytest tests/unit/test_nvda_remote_use_cases.py -k "non_us_backslash" -v`

Expected: PASS

Run: `pytest tests/unit/test_hid_keys.py tests/unit/test_windows_adapters.py tests/unit/test_macos_adapters.py tests/unit/test_nvda_remote_legacy_key_payload.py tests/unit/test_nvda_remote_use_cases.py -v`

Expected: PASS

- [ ] **Step 5: Commit the forwarding regression lock**

```bash
git add src/apps/nvda_remote/use_cases/input_forwarding.py tests/unit/test_nvda_remote_use_cases.py
git commit -m "test: lock unsupported iso relay suppression behavior"
```

## Task 6: Final Verification

**Files:**
- Modify: none
- Test: `tests/unit/test_hid_keys.py`
- Test: `tests/unit/test_windows_adapters.py`
- Test: `tests/unit/test_macos_adapters.py`
- Test: `tests/unit/test_nvda_remote_legacy_key_payload.py`
- Test: `tests/unit/test_nvda_remote_use_cases.py`

- [ ] **Step 1: Run the targeted verification suite**

Run: `pytest tests/unit/test_hid_keys.py tests/unit/test_windows_adapters.py tests/unit/test_macos_adapters.py tests/unit/test_nvda_remote_legacy_key_payload.py tests/unit/test_nvda_remote_use_cases.py -v`

Expected: PASS

- [ ] **Step 2: Run the full test suite before closing the branch**

Run: `pytest tests/unit tests/integration -v`

Expected: PASS

- [ ] **Step 3: Record the verification commands in the finishing notes or PR description**

```text
Verified:
- pytest tests/unit/test_hid_keys.py tests/unit/test_windows_adapters.py tests/unit/test_macos_adapters.py tests/unit/test_nvda_remote_legacy_key_payload.py tests/unit/test_nvda_remote_use_cases.py -v
- pytest tests/unit tests/integration -v
```

- [ ] **Step 4: Commit only if any final test-fixture adjustments were needed**

```bash
git status --short
```

Expected: no uncommitted changes, or only intentional final fixture adjustments ready for a small follow-up commit.

## Self-Review

- Spec coverage:
  - HID constants expanded for punctuation, navigation, numpad, and ISO: covered by Task 1.
  - Windows normalization completed for ANSI 104-key plus ISO where stable: covered by Task 2.
  - macOS normalization completed for ANSI 104-key plus ISO where stable: covered by Task 3.
  - ANSI relay compatibility completed without changing wire format: covered by Task 4.
  - Unsupported ISO relay behavior remains suppress-and-log: covered by Task 5.
- Placeholder scan:
  - No `TODO`, `TBD`, or “similar to above” placeholders remain.
  - Every code-changing step includes concrete snippets and exact commands.
- Type consistency:
  - Uses the existing `HID`, `KeyEvent`, `key_event_to_legacy_remote_payload`, and `KeyEventDecision` naming already present in the repo.
  - Keeps `NON_US_BACKSLASH` spelled consistently across constants, mappings, relay rejection, and tests.
