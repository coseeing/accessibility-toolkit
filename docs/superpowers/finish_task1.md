# Review Response — HID Keyboard Input Fixes

## Review Findings Verified

All three findings in `docs/superpowers/review_task0.md` were confirmed correct against the spec and plan.

### Finding 1: Windows hotkey F10/ENTER fallback to F11

**Confirmed.** `WindowsHotkeyCapture._USAGE_TO_VK` only contained `F11_USAGE → F11_VK`, causing `HID.F10` (key echo enter) and `HID.ENTER` to silently resolve to VK `0x7A` (F11).

**Fix:** Added `F10_VK = 0x79` and `ENTER_VK = 0x0D` to `_USAGE_TO_VK` in `src/adapters/windows/hotkey.py:17`.

### Finding 2: Platform HID maps missing standard keys

**Confirmed.** Windows `_SCAN_TO_USAGE` omitted C-Z, digits 0-9, and Backspace. macOS `KEYCODE_TO_USAGE` omitted digits 0-9. This caused these keys to return `None` and be dropped by the platform adapters.

**Fix:** Expanded both mapping tables to cover all standard `0x07` keys:
- Windows (`src/adapters/windows/hid_map.py`): Added 28 entries covering all A-Z letters, digits 0-9, and Backspace
- macOS (`src/adapters/macos/hid_map.py`): Added digits 0-9 entries

### Finding 3: Legacy relay adapter only supporting 16 usages + no error handling

**Confirmed.** `_USAGE_TO_LEGACY` only mapped 16 usages, and `NvdaRemoteInputForwardingUseCase.handle()` called it without guarding the `ValueError`, which would crash on any unsupported key.

**Fix:**
- Expanded `_USAGE_TO_LEGACY` in `src/apps/nvda_remote/legacy_key_payload.py` to 68 entries covering A-Z, 0-9, all F1-F12, Backspace, KEYPAD_ENTER, LEFT_META, RIGHT_META
- Added `try/except ValueError` + logging in `src/apps/nvda_remote/use_cases/input_forwarding.py:41-47`, returning `PASS_THROUGH` for unsupported usages per the spec

## New Tests Added

| Test | File |
|------|------|
| `test_windows_keyboard_hook_emits_hid_for_digit_and_letter` | `tests/unit/test_windows_adapters.py` |
| `test_windows_keyboard_hook_emits_hid_for_backspace` | `tests/unit/test_windows_adapters.py` |
| `test_key_event_from_macos_maps_digit_to_hid` | `tests/unit/test_macos_adapters.py` |
| `test_hid_c_maps_to_legacy_remote_payload` | `tests/unit/test_nvda_remote_legacy_key_payload.py` |
| `test_hid_digit_1_maps_to_legacy_remote_payload` | `tests/unit/test_nvda_remote_legacy_key_payload.py` |
| `test_hid_backspace_maps_to_legacy_remote_payload` | `tests/unit/test_nvda_remote_legacy_key_payload.py` |
| `test_hid_left_meta_maps_to_legacy_remote_payload` | `tests/unit/test_nvda_remote_legacy_key_payload.py` |
| `test_hid_f1_maps_to_legacy_remote_payload` | `tests/unit/test_nvda_remote_legacy_key_payload.py` |
| `test_input_forwarding_passes_through_unsupported_usage` | `tests/unit/test_nvda_remote_use_cases.py` |

## Test Results

**287 passed, 0 failed** (+9 new tests)

## Commit

| Commit | Message |
|--------|---------|
| `757d679` | fix: expand HID maps and legacy adapter to cover all standard 0x07 keys |
