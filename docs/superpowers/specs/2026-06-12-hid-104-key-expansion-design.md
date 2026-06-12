# HID 104-Key Expansion Design

## Overview

This design extends the current HID-first keyboard model from partial `usage page` `0x07` coverage to full ANSI 104-key coverage, plus the ISO extra key (`NonUsBackslash`). The goal is to make the shared input model complete for ordinary desktop keyboard use while preserving the current relay wire format and keeping the relay boundary explicit.

This is an expansion of the existing HID-first migration, not a redesign of the architecture. HID remains the only shared keyboard representation inside the application. Platform adapters still normalize native events to HID, and `apps/nvda_remote` remains the only boundary that converts HID back into legacy `vk_code/scan_code/extended/pressed` payloads.

## Goals

- Complete ANSI 104-key coverage in the shared HID model.
- Add ISO extra key support to the shared HID model and platform normalization layers.
- Complete Windows and macOS platform mappings for the expanded key set.
- Complete ANSI 104-key coverage in the legacy relay adapter.
- Preserve the current control-mode safety rule: unsupported relay keys are suppressed locally and logged, not passed through.

## Non-Goals

- Do not add JIS-specific keys in this round.
- Do not change the relay wire format.
- Do not add consumer/media keys or other `usage page` values outside `0x07`.
- Do not redesign the current adapter layering or introduce code generation for mapping tables.
- Do not guarantee relay compatibility for the ISO extra key if a reliable legacy mapping is not available.

## Scope

### In Scope

#### ANSI 104-Key Coverage

The following groups must be fully represented in HID and normalized by both platform adapters:

- Letters: `A-Z`
- Digits: `0-9`
- Core controls: `Enter`, `Escape`, `Backspace`, `Tab`, `Space`, `CapsLock`
- Main-cluster punctuation:
  - `Minus`
  - `Equals`
  - `LeftBracket`
  - `RightBracket`
  - `Backslash`
  - `Semicolon`
  - `Quote`
  - `Grave`
  - `Comma`
  - `Period`
  - `Slash`
- Function keys: `F1-F12`
- Navigation/editing:
  - `Insert`
  - `Delete`
  - `Home`
  - `End`
  - `PageUp`
  - `PageDown`
  - `Up`
  - `Down`
  - `Left`
  - `Right`
- Modifiers:
  - `LeftControl`
  - `RightControl`
  - `LeftShift`
  - `RightShift`
  - `LeftAlt`
  - `RightAlt`
  - `LeftMeta`
  - `RightMeta`
- Numpad:
  - `Keypad0-Keypad9`
  - `KeypadDecimal`
  - `KeypadDivide`
  - `KeypadMultiply`
  - `KeypadSubtract`
  - `KeypadAdd`
  - `KeypadEnter`
  - `KeypadEquals`

#### ISO Extra Key

- `NonUsBackslash` is in scope for:
  - HID constants
  - Windows normalization if a stable scan-code mapping exists
  - macOS normalization if a stable virtual-key mapping exists
  - local application behavior

### Out of Scope

- JIS-only keys
- `PrintScreen`
- `ScrollLock`
- `Pause`
- `NumLock`
- application/menu key

These keys may be addressed later, but they are intentionally excluded from this expansion so the work stays focused on the user-requested 104-key layout plus the ISO extra key.

## Architecture

The architecture does not change:

- `src/interop/key/*` defines HID constants and the shared `KeyEvent`
- `src/adapters/windows/*` normalizes Windows events to HID
- `src/adapters/macos/*` normalizes macOS events to HID
- `src/application/*` and `src/apps/*` use HID only
- `src/apps/nvda_remote/legacy_key_payload.py` remains the only HID -> legacy relay conversion layer

The expansion is a controlled broadening of existing lookup tables and tests, not a change in layering or control flow.

## Design Decisions

### 1. Keep HID as the Only Shared Input Model

No new parallel model is introduced. The expanded key set is added to the existing HID-first representation:

```python
@dataclass(frozen=True, slots=True)
class KeyEvent:
    usage_page: int
    usage: int
    pressed: bool
```

This preserves the architectural decision already made in the HID migration and avoids reintroducing Windows-specific semantics into the core.

### 2. Group HID Constants by Keyboard Region

The current `hid.py` file should be expanded in grouped sections rather than appending ad hoc values. The file should stay flat and readable, but the constants should be organized conceptually:

- alphanumeric
- main-cluster punctuation
- function keys
- navigation/editing
- modifiers
- numpad
- ISO extra key

This is a readability and maintenance decision only. It should not introduce a new abstraction layer.

### 3. Distinguish Main-Cluster and Numpad Keys

The expanded mappings must preserve distinct HID usages for visually similar keys:

- main `Enter` vs `KeypadEnter`
- main digits vs `Keypad0-Keypad9`
- main `Minus` vs `KeypadSubtract`
- main `Equals` vs `KeypadEquals`
- main `Period` vs `KeypadDecimal`
- main `Slash` vs `KeypadDivide`

This distinction is required for correctness and is one of the main reasons to finish the HID expansion rather than relying on textual or Windows-VK identity.

### 4. ANSI 104-Key Must Be Relay-Compatible

All ANSI 104-key keys listed in the in-scope section must be supported by the legacy relay adapter:

- HID -> `vk_code`
- HID -> `scan_code`
- HID -> `extended`

This must be true even though the relay protocol itself remains unchanged.

### 5. ISO Extra Key May Remain Local-Only

`NonUsBackslash` should be supported in the shared HID model and platform adapters. However, relay forwarding for that key is not required if a stable legacy mapping cannot be justified across the current target environments.

If the key remains unsupported at the relay boundary:

- the adapter should raise `ValueError`
- forwarding logic should log and suppress it in control mode
- tests should assert that behavior explicitly

This keeps the boundary honest and avoids inventing unstable compatibility behavior.

## File-Level Changes

### `src/interop/key/hid.py`

Add missing HID constants for:

- remaining main-cluster punctuation
- navigation/editing keys
- `CapsLock`
- numpad keys
- `NonUsBackslash`

The file should remain a single focused constant definition module.

### `src/adapters/windows/hid_map.py`

Expand scan-code mappings to cover:

- remaining punctuation keys
- navigation/editing keys
- `CapsLock`
- numpad keys
- ISO extra key if Windows scan-code handling is stable

Windows mappings must continue to rely primarily on:

- `scanCode`
- `extended`

and only secondarily on `vkCode` if needed for ambiguity resolution.

### `src/adapters/macos/hid_map.py`

Expand macOS virtual-key mappings to cover:

- remaining punctuation keys
- navigation/editing keys
- `CapsLock`
- numpad keys
- ISO extra key if a stable key-code mapping is available

As with the previous HID migration, this remains a pure table-driven translation layer.

### `src/apps/nvda_remote/legacy_key_payload.py`

Expand the legacy adapter so ANSI 104-key coverage is complete:

- punctuation
- navigation/editing
- `CapsLock` if supported by the old protocol semantics used here
- numpad keys

`NonUsBackslash` should be included only if the mapping is reliable. If not, it should remain unsupported explicitly rather than guessed.

### `src/apps/nvda_remote/use_cases/input_forwarding.py`

No new behavior model is needed. Keep the current contract:

- supported HID key -> relay payload -> suppress locally
- unsupported HID key while controlling -> log + suppress locally

This behavior is already safer than the previous pass-through bug and should remain unchanged in this round.

## Data Flow

### Local Input

1. Platform adapter captures native key event.
2. Platform adapter maps to HID `KeyEvent`.
3. Shared application/app logic consumes HID only.
4. `key_echo` and local mode logic continue to work directly on HID usages.

### Remote Forwarding

1. `nvda_remote` receives a HID `KeyEvent`.
2. If the event is ANSI 104-key and relay-compatible, convert it through `legacy_key_payload.py`.
3. If the event is the ISO extra key and no stable relay mapping exists, reject conversion.
4. Forwarding logic logs and suppresses unsupported relay keys while control mode is active.

## Testing Strategy

### Unit Tests: HID Constants

Add direct tests for newly introduced HID constants:

- punctuation usages
- numpad usages
- `NonUsBackslash`

### Unit Tests: Windows Mapping

Add mapping tests for:

- `Semicolon`
- `Quote`
- `Comma`
- `Period`
- `Slash`
- `LeftBracket`
- `RightBracket`
- `Backslash`
- `Grave`
- numpad digits
- numpad operators
- `KeypadEnter`
- ISO extra key if implemented

### Unit Tests: macOS Mapping

Add equivalent macOS mapping tests for:

- main-cluster punctuation
- numpad digits
- numpad operators
- `KeypadEnter`
- ISO extra key if implemented

### Unit Tests: Legacy Relay Adapter

Add relay payload conversion tests for:

- punctuation keys
- navigation/editing keys
- numpad keys
- meta/modifier keys where relay compatibility matters

If `NonUsBackslash` stays unsupported for relay:

- add an explicit failing-conversion test
- assert `ValueError`

### Unit Tests: Forwarding Behavior

Ensure unsupported relay keys:

- do not send payloads
- do not pass through locally
- return `SUPPRESS`

### Regression Expectations

After implementation:

- main-cluster punctuation should work in both local HID use cases and relay forwarding
- numpad keys should remain distinct from main-cluster equivalents
- ISO extra key should be available in HID even if relay conversion remains unsupported

## Risks

### Mapping Ambiguity

The largest correctness risk is confusing:

- main-cluster vs numpad keys
- ANSI backslash vs ISO extra key
- keys whose Windows identity depends on `extended`

This must be handled through explicit test coverage, not inference.

### Legacy Relay Limits

Even with a broader HID model, the relay still depends on old Windows-style payload fields. That is acceptable for ANSI 104-key, but ISO support must remain explicitly conditional.

### Table Growth

The mapping files will grow significantly. The mitigation is clear grouping and focused tests, not a new abstraction layer in this round.

## Recommended Approach

Proceed with a table-expansion implementation that:

- keeps the current architecture
- groups constants and mappings by keyboard region
- fully covers ANSI 104-key relay compatibility
- adds ISO extra key only to local HID unless relay support is clearly stable

This is the smallest correct expansion that satisfies the user request without turning the work into a broader redesign.
