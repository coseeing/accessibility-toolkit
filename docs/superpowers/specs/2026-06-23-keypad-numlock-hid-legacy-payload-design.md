# Keypad NumLock HID Legacy Payload Design

## Problem

`nvda_remote` currently forwards Windows key events to the remote side using native Windows
`vk_code`, `scan_code`, and `extended` values when a `WindowsNativeKeyContext` is present. Other
platforms fall back to converting HID usages to the same Windows-style payload.

The fallback path cannot currently express the Windows/NVDA distinction between a main navigation
key and a numeric keypad key when NumLock is off. For example:

- Main down arrow: `vk=0x28`, `scan=80`, `extended=True`
- Numpad 2 with NumLock off: `vk=0x28`, `scan=80`, `extended=False`
- Numpad 2 with NumLock on: `vk=0x62`, `scan=80`, `extended=False`

NVDA uses the `vk_code` plus `extended` pair to distinguish gestures such as `downArrow`,
`numpad2`, and `numLockNumpad2`. Losing that distinction prevents the remote NVDA instance from
receiving the intended keypad gesture.

## Goal

Use a unified HID-to-Windows-style payload path for `nvda_remote` forwarding on all platforms,
including Windows. The forwarding path should no longer depend on `WindowsNativeKeyContext`.

The HID event should remain the physical key identity, while `CapturedKeyEvent` carries the
optional NumLock state needed to select the correct Windows-style payload for numeric keypad keys.

## Data Model

Add this field to `CapturedKeyEvent`:

```python
num_lock_on: bool | None = None
```

Meaning:

- `True`: the capture source knows NumLock is on.
- `False`: the capture source knows NumLock is off.
- `None`: the capture source does not provide reliable NumLock state.

`KeyEvent` stays unchanged. It continues to represent HID usage page, usage, and pressed state.

## Forwarding Data Flow

The `nvda_remote` forwarding path becomes:

```text
platform capture
-> CapturedKeyEvent(key_event=HID usage, num_lock_on=...)
-> legacy_payload_from_captured_event()
-> key_event_to_legacy_remote_payload(event, num_lock_on=...)
-> RemoteMessageType.KEY payload
```

`legacy_payload_from_captured_event()` should ignore `WindowsNativeKeyContext` for this payload
conversion and always call the HID converter. `WindowsNativeKeyContext` can remain in the codebase
for other uses or future diagnostics, but it should not be required for `nvda_remote` forwarding.

## Keypad Mapping Rules

`num_lock_on` affects only these HID usages:

- `HID.KEYPAD_0`
- `HID.KEYPAD_1`
- `HID.KEYPAD_2`
- `HID.KEYPAD_3`
- `HID.KEYPAD_4`
- `HID.KEYPAD_5`
- `HID.KEYPAD_6`
- `HID.KEYPAD_7`
- `HID.KEYPAD_8`
- `HID.KEYPAD_9`
- `HID.KEYPAD_DECIMAL`

When `num_lock_on is True`, keep the current numeric keypad virtual-key mappings:

| HID usage | vk_code | scan_code | extended |
| --- | ---: | ---: | --- |
| `KEYPAD_0` | `0x60` | `82` | `False` |
| `KEYPAD_1` | `0x61` | `79` | `False` |
| `KEYPAD_2` | `0x62` | `80` | `False` |
| `KEYPAD_3` | `0x63` | `81` | `False` |
| `KEYPAD_4` | `0x64` | `75` | `False` |
| `KEYPAD_5` | `0x65` | `76` | `False` |
| `KEYPAD_6` | `0x66` | `77` | `False` |
| `KEYPAD_7` | `0x67` | `71` | `False` |
| `KEYPAD_8` | `0x68` | `72` | `False` |
| `KEYPAD_9` | `0x69` | `73` | `False` |
| `KEYPAD_DECIMAL` | `0x6E` | `83` | `False` |

When `num_lock_on is False`, use the Windows keypad-navigation virtual-key mappings while keeping
`extended=False` so NVDA sees the keypad gesture rather than the main navigation cluster:

| HID usage | vk_code | scan_code | extended |
| --- | ---: | ---: | --- |
| `KEYPAD_0` | `0x2D` | `82` | `False` |
| `KEYPAD_1` | `0x23` | `79` | `False` |
| `KEYPAD_2` | `0x28` | `80` | `False` |
| `KEYPAD_3` | `0x22` | `81` | `False` |
| `KEYPAD_4` | `0x25` | `75` | `False` |
| `KEYPAD_5` | `0x0C` | `76` | `False` |
| `KEYPAD_6` | `0x27` | `77` | `False` |
| `KEYPAD_7` | `0x24` | `71` | `False` |
| `KEYPAD_8` | `0x26` | `72` | `False` |
| `KEYPAD_9` | `0x21` | `73` | `False` |
| `KEYPAD_DECIMAL` | `0x2E` | `83` | `False` |

When `num_lock_on is None`, keep the existing mapping behavior. This preserves current behavior for
platforms or tests that do not yet provide NumLock state.

## Non-Affected Keys

These keypad keys should keep their current mappings regardless of `num_lock_on`:

- `HID.KEYPAD_DIVIDE`
- `HID.KEYPAD_MULTIPLY`
- `HID.KEYPAD_SUBTRACT`
- `HID.KEYPAD_ADD`
- `HID.KEYPAD_ENTER`
- `HID.KEYPAD_EQUALS`

`HID.NUM_LOCK` itself also keeps its current mapping and does not use `num_lock_on`.

Main navigation keys remain distinct. For example, `HID.DOWN` continues to map to
`vk=0x28`, `scan=80`, `extended=True`.

## Platform Capture Behavior

Windows capture should read `GetKeyState(VK_NUMLOCK)` and set `CapturedKeyEvent.num_lock_on` to a
known boolean value when emitting a captured event.

macOS capture may initially set `num_lock_on=None` if no reliable source is available. The field
gives macOS a place to provide NumLock state later without changing the forwarding contract.

## Tests

Add focused tests for:

- `HID.KEYPAD_0..9` and `HID.KEYPAD_DECIMAL` with `num_lock_on=True`.
- `HID.KEYPAD_0..9` and `HID.KEYPAD_DECIMAL` with `num_lock_on=False`.
- `HID.KEYPAD_0..9` and `HID.KEYPAD_DECIMAL` with `num_lock_on=None` preserving current behavior.
- Main navigation keys, especially `HID.DOWN`, still mapping to `extended=True`.
- `legacy_payload_from_captured_event()` ignoring `WindowsNativeKeyContext` and using HID plus
  `num_lock_on`.
- Windows capture filling `CapturedKeyEvent.num_lock_on` from `GetKeyState(VK_NUMLOCK)`.

