# HID-First Keyboard Input Design

## Overview

This design changes the shared low-level keyboard input model in `nvda-remote-client` to USB HID-first. Platform layers are responsible for normalizing captured native keyboard events into a neutral HID keyboard event; the application layer and each app then depend only on HID, not directly on Windows `vk`, `scan`, `extended`, or macOS `key_code`.

The first phase supports only standard keyboard `usage page` `0x07`. The goal is to get a stable cross-platform physical key event model running end-to-end while preserving compatibility with the existing NVDA Remote relay protocol.

## Goals

- Change the project's core keyboard event model to HID-first.
- Make both Windows and macOS keyboard capture produce the same neutral event shape.
- Move `application`, `key_echo`, hotkey and mode management, and local control logic to HID-based decisions.
- Preserve compatibility with the existing NVDA Remote wire protocol without changing the relay `key` message format.
- Restrict legacy Windows-style `vk/scan/extended` semantics to a protocol-boundary adapter.

## Non-Goals

- Do not support consumer/media keys such as `usage page` `0x0C` in this round.
- Do not handle IME, text input, character output, or keyboard layout derivation in this round.
- Do not redesign the relay server or change the network protocol format in this round.
- Do not guarantee full coverage for every regional keyboard layout or every special key in one pass.
- Do not expose HID events directly as a new external network protocol.

## Problem Statement

The project currently uses a Windows-style shared model: `KeyEvent(vk, scan, extended, pressed)`. Windows produces that event shape directly. macOS translates `key_code` into Windows `vk/scan` through a lookup table before sending it upward. This creates several problems:

- The core layer is driven by Windows semantics.
- Cross-platform logic depends on Windows representation rather than a neutral physical key model.
- `key_echo` and mode/hotkey logic cannot naturally share a truly platform-neutral input model.
- As more platforms or input sources are added, platform codes will continue leaking into the core.

The normalization target needs to change from "convert to Windows" to "convert to HID".

## HID Model

### Definitions

- `usage_page`: HID usage page. In phase 1 this is fixed to `0x07`, which means Keyboard/Keypad.
- `usage`: The specific key within that usage page, for example `A=0x04`, `Enter=0x28`, `Escape=0x29`, `F11=0x44`.
- `pressed`: `True` means key down, `False` means key up.

### Core Event Shape

The new shared keyboard event is:

```python
@dataclass(frozen=True, slots=True)
class KeyEvent:
    usage_page: int
    usage: int
    pressed: bool
```

This model represents only physical key events. It does not carry higher-level semantics such as characters, layout-derived meaning, modified text, or platform codes.

## Architecture

### Layer Responsibilities

#### `adapters/*`

Platform-specific input capture and mapping.

- Windows: native event -> HID `KeyEvent`
- macOS: native event -> HID `KeyEvent`
- Must not expose `vk`, `scan`, `extended`, or `key_code` upward as the shared model

#### `application/*`

Consumes only HID `KeyEvent`.

- hotkey policy
- mode manager
- activation
- key echo
- app facade keyboard-event behavior

#### `apps/nvda_remote/*`

Uses HID `KeyEvent` as the internal app event model, but converts it to the legacy `vk_code/scan_code/extended/pressed` payload through a single adapter before sending the existing relay protocol.

#### `interop/protocol/*`

Keeps the existing wire format in phase 1 and does not introduce a HID-native network message.

## Platform Mapping Strategy

### Windows

The Windows low-level keyboard hook still captures raw events, but its normalization target becomes HID.

Mapping rules:

- Use `scanCode + extended flag` as the primary source of truth.
- Use `vkCode` only when necessary as a secondary aid.
- Preserve clear distinctions for left/right modifiers, arrow keys, function keys, and keypad-related keys.

Reasoning:

- `vkCode` reflects Windows logical key semantics and is not sufficient for stable physical key identity.
- Physical-key normalization should primarily depend on scan code and extended flag.

Windows mapping should be centralized in a single module such as `adapters/windows/hid_map.py`, called by the hook adapter.

### macOS

The macOS event tap still captures `key_code` and key down/up state, but it no longer converts those values into Windows `vk/scan`. Instead it maps directly to HID usage.

Mapping rules:

- Map macOS virtual key codes to HID usage.
- Preserve current distinguishability for regular keys, function keys, arrow keys, and left/right modifiers.
- Centralize the lookup table in a single module such as `adapters/macos/hid_map.py`.

The role of `adapters/macos/keymap.py` changes from "macOS -> Windows-style" to "macOS -> HID".

## Application Model Changes

All upper-layer keyboard logic becomes HID-first:

- `ModeManager`
- `InputActivationUseCase`
- `active_key_policy`
- `state_transition_hotkeys`
- `key_echo`
- `nvda_remote` local start/stop control hotkey decisions

Places that currently check values such as `event.vk == 0x7A` or `event.vk == 0x1B` will instead compare against fixed HID usage constants.

A shared set of HID constants or an enum should be introduced, covering at least:

- letters A-Z
- digits 0-9
- `Enter`
- `Escape`
- `Tab`
- `Space`
- `Backspace`
- arrow keys
- `F1-F12`
- left/right `Shift`
- left/right `Control`
- left/right `Alt/Option`
- left/right `Meta/Command`

## Legacy Relay Protocol Compatibility

The existing NVDA Remote wire protocol remains unchanged. The `type="key"` payload stays:

```json
{
  "type": "key",
  "vk_code": 65,
  "scan_code": 30,
  "extended": false,
  "pressed": true
}
```

### Boundary Adapter

Add a single protocol adapter responsible for:

- HID `KeyEvent` -> legacy remote payload

This adapter is the only place in the project that is allowed to deal with `vk_code/scan_code/extended`. The core layer and app logic must not depend on those fields directly.

### Adapter Behavior

- Only guarantee support for phase-1 standard keyboard keys under `usage_page=0x07`.
- If a HID usage cannot be mapped reliably to the legacy payload, reject sending it and produce a clear status signal or log entry rather than guessing.
- The protocol adapter must not drive the core model backward; it is a compatibility layer only.

## Data Flow

### Local Input Flow

1. A platform adapter captures a native keyboard event.
2. The platform adapter converts the native event into HID `KeyEvent`.
3. `application` and app use cases consume only HID `KeyEvent`.
4. If the current app is `key_echo`, it uses HID directly for local output or control decisions.
5. If the current app is `nvda_remote` and the event must be forwarded, the legacy protocol adapter converts it to the existing payload before network transmission.

### Remote Forwarding Flow

1. `nvda_remote` receives a local HID `KeyEvent`.
2. App logic uses HID to decide mode and hotkey behavior.
3. If the event should be sent to the relay, app logic calls the legacy protocol adapter.
4. The adapter produces the existing `key` message payload.
5. Transport and serializer send it through the existing path.

## Migration Plan

### Step 1: Introduce HID Core Model

- Redefine the shared `interop.key.KeyEvent`
- Introduce HID constants/enums
- Remove or phase out core-layer dependencies on `vk/scan/extended`

### Step 2: Convert Platform Capture Output

- Make the Windows hook emit HID `KeyEvent`
- Make the macOS event tap emit HID `KeyEvent`
- Update unit tests to validate HID mappings

### Step 3: Convert Application and App Logic

- Convert all hotkey/mode/use-case decisions to HID usage
- Update `key_echo` behavior and tests
- Update `nvda_remote` local control flow and tests

### Step 4: Add Legacy Protocol Adapter

- Add a HID -> legacy payload converter at the right boundary in `apps/nvda_remote` or `interop/protocol`
- Update protocol and app-service tests
- Validate interoperability with the existing relay protocol

## Testing Strategy

### Unit Tests

- Mapping tests from Windows native events to HID usage
- Mapping tests from macOS `key_code` to HID usage
- HID hotkey decision tests
- HID -> legacy remote payload conversion tests

### Integration Tests

- Keep existing relay session tests to confirm the wire format remains unchanged
- Add an end-to-end path test from HID `KeyEvent` to transmitted payload

### Regression Coverage

At minimum, cover:

- `F11` entering and exiting control
- `Escape` and related existing local-control behavior
- regular letter key press/release
- left/right modifiers
- arrow keys
- keypad vs. non-keypad distinction

## Risks

### Mapping Accuracy

If Windows HID normalization uses `vkCode` as the primary source, left/right modifiers, arrow keys, and keypad-related keys can be distorted. The mapping must primarily use `scanCode + extended`.

### Legacy Compatibility Gaps

While keeping the old relay protocol, some HID keys may not map 1:1 back into legacy `vk/scan/extended`. Phase 1 must explicitly limit the supported scope and only guarantee that standard `0x07` keyboard keys work end-to-end.

### Migration Scope

Full replacement touches:

- adapters
- application
- shared mode logic
- key echo
- nvda remote forwarding
- core testing assumptions

Implementation should therefore be split into clear steps and must avoid mixing model migration with unrelated refactors in the same commit.

## Decisions Finalized By This Design

- The core model is HID-first rather than a retained Windows-style model.
- Phase 1 supports only `usage page` `0x07`.
- `KeyEvent` keeps the full `usage_page + usage + pressed` shape.
- Hotkey and mode decisions move fully to HID.
- The relay wire protocol remains compatible, with a single boundary adapter performing HID -> legacy conversion.
