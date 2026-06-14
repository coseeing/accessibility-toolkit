# Review Task 0

## Scope

Reviewed the implementation described in `docs/superpowers/finish_task0.md` against:

- `docs/superpowers/specs/2026-06-14-captured-key-event-design.md`
- `docs/superpowers/plans/2026-06-14-captured-key-event-implementation.md`

Reviewed commits in chronological order as requested:

1. `4c8c039` `refactor: add captured key event contract`
2. `9c6c2d7` `feat: emit captured key events from adapters`
3. `db9bd93` `feat: forward native windows payloads for nvda remote`
4. `834c336` `fix: stabilize windows keypad hid mapping`

## Findings

No blocking findings.

## Review Notes

### `4c8c039` `refactor: add captured key event contract`

- `CapturedKeyEvent` was introduced at the adapter boundary without polluting `interop.key.KeyEvent`.
- `InputCapture` and `KeyboardInputService` were updated consistently to pass the wrapper end-to-end.
- `KeyEchoAppService` unwraps to `event.key_event`, which matches the spec and preserves `ModeManager`'s plain-`KeyEvent` contract.

### `9c6c2d7` `feat: emit captured key events from adapters`

- Windows and macOS capture implementations now emit `CapturedKeyEvent` consistently.
- Windows capture preserves raw `vk_code`, `scan_code`, and `extended` via `WindowsNativeKeyContext`.
- `WindowsKeyPressHotkeyCapture` was correctly adapted to unwrap `event.key_event` before comparing usage and pressed state.

### `db9bd93` `feat: forward native windows payloads for nvda remote`

- `legacy_payload_from_captured_event()` correctly prefers `WindowsNativeKeyContext` and falls back to HID mapping when native context is absent.
- `NvdaRemoteInputForwardingUseCase` now accepts `CapturedKeyEvent` and uses the bridge helper, which matches the Phase 1 design.
- `NvdaRemoteAppService.handle_key_event()` preserves native context during controlling mode by routing captured events directly into input forwarding, while still handling F11 exit logic through `ModeManager`.

### `834c336` `fix: stabilize windows keypad hid mapping`

- The VK-assisted mapping path was narrowed to the keypad/navigation key group and kept subordinate to scan-code lookup.
- Existing `INTERNATIONAL3` fallback behavior was preserved explicitly instead of remaining mixed into the keypad/navigation table.
- Added regression coverage is aligned with the spec's "scan first, keypad/navigation VK fallback second" rule.

## Verification

Executed:

```bash
pytest tests/unit -q
```

Observed:

```text
355 passed in 1.58s
```

## Residual Risks

- `NvdaRemoteAppService` now preserves native context during controlling mode by bypassing `ModeManager` for non-exit keys. That is intentional and consistent with the Phase 1 design, but future input modes added under the same service will need to preserve this routing invariant explicitly.
- The current review did not include runtime validation on physical Windows hardware with the problematic keyboards; confidence is based on code inspection plus the existing unit coverage.
