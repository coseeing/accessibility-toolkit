# Task 0 Finish Report

## Summary

Implemented the keypad NumLock HID legacy payload work across capture, payload conversion, bridge selection, runtime wiring, and NumLock forwarding behavior.

Completed outcomes:

- `CapturedKeyEvent` now carries `num_lock_on: bool | None`, and Windows capture populates it from `GetKeyState(VK_NUMLOCK)` when available.
- Legacy HID-to-Windows payload conversion now distinguishes keypad numeric/editing behavior when `num_lock_on=False`, while preserving existing behavior when `num_lock_on=None`.
- The legacy payload bridge now defaults to HID conversion and only uses `WindowsNativeKeyContext` when explicit native compatibility mode is enabled.
- `NvdaRemoteAppService` and the runtime bootstrap now expose the Windows native payload compatibility switch. The runtime toggle is available through `NVDA_REMOTE_USE_WINDOWS_NATIVE_KEY_PAYLOAD`.
- In controlling mode, `HID.NUM_LOCK` now forwards to the remote side while still passing through locally. Outside controlling mode, it still passes through locally without forwarding.

## Verification

Focused verification:

```bash
pytest tests/unit/test_nvda_remote_legacy_key_payload.py \
  tests/unit/test_nvda_remote_legacy_key_payload_bridge.py \
  tests/unit/test_nvda_remote_use_cases.py \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_windows_adapters.py -v
```

Result: `135 passed`

Full verification:

```bash
pytest tests/unit tests/integration -v
```

Result: `529 passed`

## Commit List

Commits added during this implementation:

```text
facf0c1 feat: capture numlock state with key events
0d6a617 feat: cover numlock state edge cases
fd51649 feat: map keypad payloads by numlock state
5db088f fix: require keyword numlock payload arg
6f5b68d feat: default remote payload bridge to hid mapping
88636dd feat: add windows native payload forwarding switch
a2f1ff0 fix: wire native payload bootstrap flag
1cbe5ae fix: forward numlock while passing through locally
eb092c3 refactor: clarify numlock pass-through
```

## Notes

`git status --short` still shows pre-existing docs changes outside this task:

```text
 D docs/superpowers/specs/2026-06-23-keypad-numlock-hid-legacy-payload-design.md
?? docs/superpowers/plans/2026-06-24-keypad-numlock-hid-legacy-payload.md
?? docs/superpowers/specs/2026-06-24-keypad-numlock-hid-legacy-payload-design.md
?? docs/superpowers/specs/2026-06-24-keypad-numlock-hid-legacy-payload-design_zh-TW.md
```

These were left untouched.
