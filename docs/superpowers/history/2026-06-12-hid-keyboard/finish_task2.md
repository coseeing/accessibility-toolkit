# Review Response #2 — HID Keyboard Fixes

## Review Findings Verified

All three findings in `docs/superpowers/review_task1.md` were confirmed correct against the spec, the original codebase behavior, and the plan.

### Finding 1: MINUS and EQUALS still unsupported

**Confirmed.** HID usages `0x2D` (minus) and `0x2E` (equals) are standard `0x07` keys. They were present in the old keymap but missing from the new HID model, platform maps, and legacy adapter.

**Fix:**
- Added `HID.MINUS = 0x2D` and `HID.EQUALS = 0x2E` to `src/interop/key/hid.py`
- Added Windows scan codes `(12, False) → MINUS`, `(13, False) → EQUALS` to `src/adapters/windows/hid_map.py`
- Added macOS key codes `27 → MINUS`, `24 → EQUALS` to `src/adapters/macos/hid_map.py`
- Added legacy mappings: MINUS `(VK 189, scan 12, no extended)`, EQUALS `(VK 187, scan 13, no extended)` to `src/apps/nvda_remote/legacy_key_payload.py`

### Finding 2: Unsupported keys leak locally during control mode

**Confirmed.** Returning `PASS_THROUGH` for unsupported HID usages during remote control mode violates the original design where control mode suppresses all local keyboard effects. The spec says "reject sending it and produce a clear status signal or log entry" — not "let it pass through."

**Fix:** Changed `return KeyEventDecision.PASS_THROUGH` to `return KeyEventDecision.SUPPRESS` in `src/apps/nvda_remote/use_cases/input_forwarding.py:48`.

### Finding 3: Meta keys incorrectly marked non-extended

**Confirmed.** The original macOS keymap (`EXTENDED_KEY_CODES`) included key codes 54 (RightCommand) and 55 (LeftCommand), generating `extended=True`. The Windows low-level keyboard hook sets `LLKHF_EXTENDED` for both Windows keys (scan 0x5B/0x5C). The new legacy adapter hardcoded `extended=False`, breaking remote Windows injection compatibility.

**Fix:**
- Changed legacy adapter: `LEFT_META: (91, 91, True)`, `RIGHT_META: (92, 92, True)` in `src/apps/nvda_remote/legacy_key_payload.py`
- Changed Windows hid_map: `(91, True) → LEFT_META`, `(92, True) → RIGHT_META` in `src/adapters/windows/hid_map.py`

## New Tests Added

| Test | File |
|------|------|
| `test_hid_minus_maps_to_legacy_remote_payload` | `tests/unit/test_nvda_remote_legacy_key_payload.py` |
| `test_hid_equals_maps_to_legacy_remote_payload` | `tests/unit/test_nvda_remote_legacy_key_payload.py` |
| `test_hid_right_meta_maps_to_legacy_remote_payload` | `tests/unit/test_nvda_remote_legacy_key_payload.py` |
| `test_key_event_from_macos_maps_minus_equals_to_hid` | `tests/unit/test_macos_adapters.py` |
| `test_windows_keyboard_hook_emits_hid_for_minus_equals` | `tests/unit/test_windows_adapters.py` |
| `test_windows_keyboard_hook_emits_hid_for_left_meta_with_extended` | `tests/unit/test_windows_adapters.py` |

## Updated Tests

| Test | Change |
|------|--------|
| `test_hid_left_meta_maps_to_legacy_remote_payload` | `extended: False` → `extended: True` |
| `test_input_forwarding_suppresses_unsupported_usage` | renamed + `PASS_THROUGH` → `SUPPRESS` |

## Test Results

**293 passed, 0 failed** (+6 new tests)

## Commit

| Commit | Message |
|--------|---------|
| `ad2a928` | fix: add minus/equals HID support, fix meta-key extended flag, suppress unsupported keys in control mode |
