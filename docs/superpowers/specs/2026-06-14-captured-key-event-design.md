# CapturedKeyEvent and Windows Native Context Design

## Summary

This design addresses two coupled problems in the keyboard input pipeline:

1. Windows keyboard capture must continue to produce correct HID semantics even on hardware that reports non-standard scan code formats.
2. Certain downstream consumers, especially NVDA Remote legacy key forwarding, must preserve the original Windows `vk/scan/extended` values instead of reconstructing them from HID.

The design introduces a cross-platform `CapturedKeyEvent` container at the input capture boundary while keeping `interop.key.KeyEvent` as a pure HID model. Windows capture attaches a Windows-specific native context, and NVDA Remote uses a dedicated bridge helper to prefer that native context when building legacy payloads.

## Problem

The current `KeyEvent` model serves two different responsibilities:

- represent platform-neutral HID key semantics
- indirectly support reconstruction of Windows legacy key payloads

Those goals diverge on real hardware. In particular, Num Lock-sensitive keypad and navigation keys can be misclassified or dropped when Windows low-level hook scan code values differ from the normalized values expected by the static scan code lookup. The previously validated raw-values fix worked because it preserved original Windows fields, but that solution leaked Windows-specific fields into a shared HID model.

The design must therefore satisfy both of these requirements:

- preserve correct HID semantics for business logic that cares about keypad vs navigation meaning
- preserve original Windows native values for downstream consumers that must emit Windows-compatible payloads

## Goals

- Keep `KeyEvent` platform-neutral and HID-only.
- Introduce a capture-layer event container that can carry optional native metadata.
- Preserve original Windows `vk_code`, `scan_code`, and `extended` values for forwarding.
- Improve `key_event_from_windows()` so Num Lock-related keypad and navigation keys remain semantically correct on problematic hardware.
- Keep existing macOS behavior working without inventing synthetic native metadata.
- Limit platform-specific knowledge to adapter and app-boundary code.

## Non-Goals

- Redesign the entire input system or mode manager.
- Introduce a deep cross-platform native metadata abstraction hierarchy.
- Convert all Windows key mapping to VK-driven logic.
- Expand the change to unrelated unsupported legacy payload keys.
- Add new behavior changes to key echo, control mode, or hotkey activation beyond the event container migration.

## Design Overview

### Core Types

`interop.key.KeyEvent`

- Remains the shared, platform-neutral HID semantic model.
- Continues to represent only:
  - `usage_page`
  - `usage`
  - `pressed`
- Must not include Windows raw fields.

`CapturedKeyEvent`

- New cross-platform input-capture output container.
- Lives in the input adapter boundary layer rather than `interop`.
- Fields:
  - `key_event: KeyEvent`
  - `native_context: object | None`

`WindowsNativeKeyContext`

- New Windows-specific native metadata type.
- Lives under `adapters.windows`.
- Fields:
  - `vk_code: int`
  - `scan_code: int`
  - `extended: bool`

### Placement and Dependency Direction

Recommended placement:

- `KeyEvent`: `interop.key`
- `CapturedKeyEvent`: `adapters.inputs`
- `WindowsNativeKeyContext`: `adapters.windows`

Dependency direction:

- Platform capture implementations produce `CapturedKeyEvent`.
- `application.keyboard` and app services accept `CapturedKeyEvent`.
- General business logic should immediately use `captured.key_event` and ignore `native_context`.
- Only platform-specific compatibility bridges may inspect `native_context`.
- App and application layers should not directly depend on Windows adapter details except via narrow helper functions at the app boundary.

## Data Flow

### Windows

1. Windows low-level hook receives raw `vkCode`, `scanCode`, `flags`.
2. `key_event_from_windows()` converts those values into a semantic `KeyEvent`.
3. `WindowsKeyboardCapture` emits:
   - `CapturedKeyEvent(key_event=<hid event>, native_context=WindowsNativeKeyContext(...))`

### macOS

1. macOS event tap receives a raw event.
2. `key_event_from_macos()` converts it into a semantic `KeyEvent`.
3. `MacOSKeyboardCapture` emits:
   - `CapturedKeyEvent(key_event=<hid event>, native_context=None)`

## Windows HID Mapping Strategy

### Principle

Windows key interpretation will use key-class-specific rules:

- keep scan code as the primary source for ordinary keys
- allow VK-assisted interpretation for Num Lock-sensitive keypad and navigation keys

This preserves the existing HID design intent for most of the keyboard while fixing the known problem domain where scan code format instability on certain hardware breaks semantic interpretation.

### Resolution Order

`key_event_from_windows()` should resolve usage in this order:

1. Lookup by `(scan_code, extended)` using the current static scan map.
2. If the event is extended and the scan code appears to include prefixed or abnormal formatting, normalize and retry using the existing scan normalization rule.
3. If lookup still fails, and `vk_code` belongs to the Num Lock-sensitive keypad/navigation group, resolve via a dedicated VK-to-HID mapping for that key group.
4. If still unresolved, return `None`.

### VK-Assisted Scope

The VK-assisted fallback is intentionally limited to the Num Lock-related keypad and navigation problem set:

- `VK_NUMPAD0` through `VK_NUMPAD9`
- `VK_INSERT`
- `VK_DELETE`
- `VK_HOME`
- `VK_END`
- `VK_PRIOR`
- `VK_NEXT`
- `VK_LEFT`
- `VK_RIGHT`
- `VK_UP`
- `VK_DOWN`
- `VK_DIVIDE`
- `VK_MULTIPLY`
- `VK_ADD`
- `VK_SUBTRACT`
- `VK_DECIMAL`
- `VK_NUMLOCK`

This change does not make VK the default authority for letters, main-cluster digits, or general modifiers.

## Capture Interface Changes

### Input Capture Protocol

`InputCapture.set_listener()` changes from:

- `Callable[[KeyEvent], KeyEventDecision]`

to:

- `Callable[[CapturedKeyEvent], KeyEventDecision]`

This change propagates through:

- `adapters.inputs.base.InputCapture`
- `application.keyboard.KeyEventHandler`
- `application.keyboard.KeyboardInputService`
- app services that currently receive raw `KeyEvent`

### General Consumption Rule

Most code should treat `CapturedKeyEvent` as a wrapper:

- read `captured.key_event`
- ignore `captured.native_context`

This keeps native metadata from leaking into general business logic.

## NVDA Remote Legacy Bridge

NVDA Remote requires Windows-compatible legacy payload fields. That need should be handled by a dedicated app-layer bridge rather than by extending `KeyEvent`.

### New Helper

Introduce:

- `legacy_payload_from_captured_event(captured: CapturedKeyEvent) -> dict[str, int | bool]`

Behavior:

1. If `captured.native_context` is a Windows native context:
   - build the legacy payload directly from:
     - `vk_code`
     - `scan_code`
     - `extended`
   - use `captured.key_event.pressed` for the `pressed` field
2. Otherwise:
   - fall back to the existing HID-based `key_event_to_legacy_remote_payload(captured.key_event)`

### Rationale

This isolates Windows payload preservation to the NVDA Remote compatibility boundary:

- HID semantic correctness remains the Windows adapter's job.
- raw Windows field preservation remains the capture native-context job.
- legacy reconstruction remains an NVDA Remote concern.

These responsibilities are no longer conflated inside `KeyEvent`.

## App and Use Case Behavior

### NVDA Remote

- `NvdaRemoteAppService` and `NvdaRemoteInputForwardingUseCase` will accept `CapturedKeyEvent`.
- Forwarding code will use `legacy_payload_from_captured_event()`.
- Key suppression and mode behavior will continue to rely on `captured.key_event`.

### Key Echo and Shared Mode Logic

- `KeyEchoAppService`, shared mode management, and input policies will accept `CapturedKeyEvent`.
- They should immediately unwrap to `captured.key_event`.
- No behavior change is intended beyond the container type migration.

## Testing Strategy

### Unit Tests

Add or update tests for:

- `CapturedKeyEvent` propagation through input capture and service boundaries
- Windows capture producing `CapturedKeyEvent` with `WindowsNativeKeyContext`
- macOS capture producing `CapturedKeyEvent(native_context=None)`
- `key_event_from_windows()` resolving the full keypad/navigation VK-assisted scope
- direct scan path still taking precedence when a standard scan code is available
- `legacy_payload_from_captured_event()` preferring Windows native context when present
- `legacy_payload_from_captured_event()` falling back to HID mapping when native context is absent

### Regression Tests

Preserve coverage for:

- NVDA Remote control-mode start/stop key suppression behavior
- NVDA Remote forwarded key behavior for keypad/navigation keys
- key echo activation and speech behavior
- macOS keypad vs main-cluster distinction

## Risks

- The listener signature change affects many test doubles and fake capture objects. The migration is broad but mostly mechanical.
- Allowing Windows-native type checks to spread beyond bridge helpers would undermine the layering goal.
- Expanding VK-assisted mapping outside the keypad/navigation problem set could accidentally weaken scan-based semantics for unrelated keys.

## Alternatives Considered

### Extend `KeyEvent` with Windows Raw Fields

Pros:

- minimal code churn
- already validated as functionally correct

Cons:

- pollutes a shared HID model with Windows-only fields
- encourages future platform exceptions to accumulate in the wrong layer

### Side-Channel Native Lookup

Pros:

- smaller apparent interface change

Cons:

- weak event association
- higher risk of timing bugs
- harder to reason about and test

The proposed `CapturedKeyEvent` design is preferred because it preserves both semantics and native fidelity without corrupting the shared model.

## Implementation Outline

1. Add `CapturedKeyEvent` at the input adapter boundary.
2. Add `WindowsNativeKeyContext` under the Windows adapter package.
3. Update `InputCapture`, `KeyEventHandler`, and `KeyboardInputService` to pass `CapturedKeyEvent`.
4. Update Windows and macOS capture implementations to emit `CapturedKeyEvent`.
5. Refine `key_event_from_windows()` to use the key-class-specific resolution order described above.
6. Add `legacy_payload_from_captured_event()` under the NVDA Remote app layer.
7. Update NVDA Remote and Key Echo services/use cases to unwrap `captured.key_event` as needed.
8. Update unit and regression tests.
