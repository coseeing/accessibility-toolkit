# HID Keyboard Input — Implementation Complete

## Summary

Migrated the shared keyboard event model from Windows-style `(vk, scan, extended, pressed)` to HID-first `(usage_page, usage, pressed)` across all layers: platform adapters, application logic, key echo, and NVDA remote forwarding. The existing relay wire protocol remains unchanged thanks to a single legacy payload adapter.

## Commit List

| Commit | Message |
|--------|---------|
| `95bef54` | feat: add HID keyboard event model |
| `236ebf3` | feat: normalize platform key capture to HID |
| `1b28104` | refactor: use HID in shared input policies |
| `20eb32c` | test: complete HID keyboard regression coverage |

## Test Results

**278 passed, 0 failed** — all unit and integration tests pass.

## What Changed

### New Files
- `src/interop/key/hid.py` — HID keyboard usage constants (`HID` singleton)
- `src/adapters/windows/hid_map.py` — Windows `scanCode + extended` → HID usage mapping
- `src/adapters/macos/hid_map.py` — macOS `key_code` → HID usage mapping
- `src/apps/nvda_remote/legacy_key_payload.py` — single HID → legacy vk/scan/extended adapter
- `tests/unit/test_hid_keys.py` — HID core model tests
- `tests/unit/test_nvda_remote_legacy_key_payload.py` — legacy payload adapter tests

### Modified Files
- `src/interop/key/key_event.py` — new `(usage_page, usage, pressed)` shape
- `src/interop/key/__init__.py` — exports `HID` and `KeyEvent`
- `src/adapters/windows/keyboard_hook.py` — emits HID `KeyEvent` via `key_event_from_windows()`
- `src/adapters/windows/hotkey.py` — accepts `usage` parameter, matches HID usage
- `src/adapters/macos/keymap.py` — simplified to use `KEYCODE_TO_USAGE` mapping
- `src/application/input/active_key_policy.py` — `exit_vk` → `exit_usage`
- `src/application/input/state_transition_hotkeys.py` — matches `event.usage`
- `src/apps/shared/mode_manager.py` — compares `event.usage` and `mode.exit_usage`
- `src/apps/shared/mode_types.py` — protocol uses `enter_usage`/`exit_usage`
- `src/apps/key_echo/use_cases/echo_input.py` — speaks HID format: `HID 0x07:0x04`
- `src/apps/key_echo/use_cases/state_transition_hotkeys.py` — maps HID constants
- `src/apps/key_echo/facade.py` — `enter_usage`/`exit_usage` with HID constants
- `src/apps/key_echo/main.py` — passes `enter_usage`
- `src/apps/nvda_remote/use_cases/input_forwarding.py` — uses `key_event_to_legacy_remote_payload()`
- `src/apps/nvda_remote/use_cases/state_transition_hotkeys.py` — maps HID constants
- `src/apps/nvda_remote/facade.py` — `_LOCAL_STOP_USAGE`, `enter_usage`/`exit_usage`
- `src/apps/nvda_remote/main.py` — passes `enter_usage`
- `src/bootstrap/platform.py` — `create_hotkey_capture(usage=...)` with HID constants
- All test files in `tests/unit/` and `tests/integration/` — updated to HID `KeyEvent` constructor

## Architecture

```
Platform Adapters → HID KeyEvent → Application/App Logic → Legacy Payload Adapter → Relay Wire Protocol
                                           ↕
                                    Key Echo (HID speech output)
```

- Platform layers normalize native events to `KeyEvent(usage_page, usage, pressed)`
- Application and app code compare only HID usage values
- `apps/nvda_remote/legacy_key_payload.py` is the **only** place that converts HID back to `vk_code/scan_code/extended` for the relay protocol
