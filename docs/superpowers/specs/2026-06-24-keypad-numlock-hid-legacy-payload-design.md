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
including Windows. On Windows, forwarding should be able to choose between the native
`WindowsNativeKeyContext` payload and the HID-derived payload using a variable switch.

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

Add a Windows forwarding mode switch for `nvda_remote`, for example:

```python
use_windows_native_key_payload: bool = False
```

Meaning:

- `False`: use the unified HID-to-Windows-style converter, even on Windows.
- `True`: preserve the current Windows behavior and forward the native `WindowsNativeKeyContext`
  values directly when they are available.

The default should be `False` so the new cross-platform path is the normal path. The native
Windows path remains available as an explicit compatibility or diagnostics mode.

## Forwarding Data Flow

The default `nvda_remote` forwarding path becomes:

```text
platform capture
-> CapturedKeyEvent(key_event=HID usage, num_lock_on=...)
-> legacy_payload_from_captured_event()
-> key_event_to_legacy_remote_payload(event, num_lock_on=...)
-> RemoteMessageType.KEY payload
```

When `use_windows_native_key_payload=False`, `legacy_payload_from_captured_event()` should ignore
`WindowsNativeKeyContext` for this payload conversion and always call the HID converter.

When `use_windows_native_key_payload=True` and `WindowsNativeKeyContext` is present, the converter
should preserve the current Windows behavior:

```text
platform capture
-> CapturedKeyEvent(key_event=HID usage, native_context=WindowsNativeKeyContext(...))
-> legacy_payload_from_captured_event(use_windows_native_key_payload=True)
-> native Windows vk_code / scan_code / extended payload
-> RemoteMessageType.KEY payload
```

`WindowsNativeKeyContext` can remain in the codebase for this explicit Windows native mode, other
uses, or future diagnostics. It should not be required for the default `nvda_remote` forwarding path.

## Keypad Mapping Rules

The converter should use this complete keypad mapping table:

| HID usage | `num_lock_on=True` | `num_lock_on=False` |
| --- | --- | --- |
| `KEYPAD_0` | `vk=0x60, scan=82, extended=False` | `vk=0x2D, scan=82, extended=False` |
| `KEYPAD_1` | `vk=0x61, scan=79, extended=False` | `vk=0x23, scan=79, extended=False` |
| `KEYPAD_2` | `vk=0x62, scan=80, extended=False` | `vk=0x28, scan=80, extended=False` |
| `KEYPAD_3` | `vk=0x63, scan=81, extended=False` | `vk=0x22, scan=81, extended=False` |
| `KEYPAD_4` | `vk=0x64, scan=75, extended=False` | `vk=0x25, scan=75, extended=False` |
| `KEYPAD_5` | `vk=0x65, scan=76, extended=False` | `vk=0x0C, scan=76, extended=False` |
| `KEYPAD_6` | `vk=0x66, scan=77, extended=False` | `vk=0x27, scan=77, extended=False` |
| `KEYPAD_7` | `vk=0x67, scan=71, extended=False` | `vk=0x24, scan=71, extended=False` |
| `KEYPAD_8` | `vk=0x68, scan=72, extended=False` | `vk=0x26, scan=72, extended=False` |
| `KEYPAD_9` | `vk=0x69, scan=73, extended=False` | `vk=0x21, scan=73, extended=False` |
| `KEYPAD_DECIMAL` | `vk=0x6E, scan=83, extended=False` | `vk=0x2E, scan=83, extended=False` |
| `KEYPAD_DIVIDE` | `vk=0x6F, scan=53, extended=True` | `vk=0x6F, scan=53, extended=True` |
| `KEYPAD_MULTIPLY` | `vk=0x6A, scan=55, extended=False` | `vk=0x6A, scan=55, extended=False` |
| `KEYPAD_SUBTRACT` | `vk=0x6D, scan=74, extended=False` | `vk=0x6D, scan=74, extended=False` |
| `KEYPAD_ADD` | `vk=0x6B, scan=78, extended=False` | `vk=0x6B, scan=78, extended=False` |
| `KEYPAD_ENTER` | `vk=0x0D, scan=28, extended=True` | `vk=0x0D, scan=28, extended=True` |
| `KEYPAD_EQUALS` | `vk=0xBB, scan=89, extended=False` | `vk=0xBB, scan=89, extended=False` |

Notes:

- `KEYPAD_0..9` and `KEYPAD_DECIMAL` change `vk_code` based on `num_lock_on`.
- Their `scan_code` stays the same across NumLock on/off.
- Their `extended` value stays `False` so NVDA sees keypad semantics rather than main navigation
  cluster semantics.
- `KEYPAD_DIVIDE`, `KEYPAD_MULTIPLY`, `KEYPAD_SUBTRACT`, `KEYPAD_ADD`, `KEYPAD_ENTER`, and
  `KEYPAD_EQUALS` keep the same mapping regardless of `num_lock_on`.
- `HID.NUM_LOCK` itself also keeps its current mapping and does not use `num_lock_on`.

When `num_lock_on is None`, keep the existing mapping behavior. In practice, this means keeping the
current `legacy_key_payload.py` mapping for the given HID usage until a reliable NumLock state is
available.

Main navigation keys remain distinct. For example, `HID.DOWN` continues to map to
`vk=0x28`, `scan=80`, `extended=True`.

## Platform Capture Behavior

Windows capture should read `GetKeyState(VK_NUMLOCK)` and set `CapturedKeyEvent.num_lock_on` to a
known boolean value when emitting a captured event.

macOS capture may initially set `num_lock_on=None` if no reliable source is available. The field
gives macOS a place to provide NumLock state later without changing the forwarding contract.

## NumLock Forwarding Behavior

`HID.NUM_LOCK` is a special case in `nvda_remote` controlling mode. It should be forwarded to the
remote side and also passed through to the local system.

This differs from ordinary remote-control keys:

| Behavior | Forward to remote | Send to local system | Pipeline result |
| --- | --- | --- | --- |
| Ordinary remote key | Yes | No | `send_to_system=False`, `app_result=HANDLED_STOP` |
| `HID.NUM_LOCK` in controlling mode | Yes | Yes | `send_to_system=True`, `app_result=HANDLED_STOP` |
| `HID.NUM_LOCK` outside controlling mode | No | Yes | `send_to_system=True`, `app_result=UNHANDLED` |

`HID.NUM_LOCK` should be passed through locally because the local NumLock state is used to populate
`CapturedKeyEvent.num_lock_on` for later keypad events. It should also be forwarded so the remote
machine's NumLock state can be controlled by the controlling side.

Both key down and key up should be forwarded:

```text
HID.NUM_LOCK pressed=True  -> vk=0x90, scan=69, extended=True, pressed=True
HID.NUM_LOCK pressed=False -> vk=0x90, scan=69, extended=True, pressed=False
```

The current early `should_pass_through_system_toggle()` return in `nvda_remote` should be adjusted
so `HID.NUM_LOCK` can take this `forward + pass-through` path while controlling. Non-controlling
mode can keep the current local pass-through behavior.

## Tests

Add focused tests for:

- `HID.KEYPAD_0..9` and `HID.KEYPAD_DECIMAL` with `num_lock_on=True`.
- `HID.KEYPAD_0..9` and `HID.KEYPAD_DECIMAL` with `num_lock_on=False`.
- `HID.KEYPAD_0..9` and `HID.KEYPAD_DECIMAL` with `num_lock_on=None` preserving current behavior.
- `HID.KEYPAD_DIVIDE`, `HID.KEYPAD_MULTIPLY`, `HID.KEYPAD_SUBTRACT`, `HID.KEYPAD_ADD`,
  `HID.KEYPAD_ENTER`, and `HID.KEYPAD_EQUALS` staying constant across NumLock on/off.
- Main navigation keys, especially `HID.DOWN`, still mapping to `extended=True`.
- `legacy_payload_from_captured_event()` ignoring `WindowsNativeKeyContext` and using HID plus
  `num_lock_on` when `use_windows_native_key_payload=False`.
- `legacy_payload_from_captured_event()` preserving the current Windows native payload behavior
  when `use_windows_native_key_payload=True` and `WindowsNativeKeyContext` is present.
- Windows capture filling `CapturedKeyEvent.num_lock_on` from `GetKeyState(VK_NUMLOCK)`.
- `HID.NUM_LOCK` in controlling mode forwarding key down and key up to the remote side while
  returning `send_to_system=True`.
- `HID.NUM_LOCK` outside controlling mode passing through locally without forwarding.
