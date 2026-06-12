# HID 104-Key Expansion Review — Fix Report

## Review Feedback from `docs/superpowers/review_task0.md`

Two findings were raised:

### Finding 1 (Accepted & Fixed): Windows KEYPAD_EQUALS gap

**Finding:** Windows normalization drops `HID.KEYPAD_EQUALS` (no scan-code mapping).

**Verification:** Confirmed. macOS and the relay adapter both support KEYPAD_EQUALS, but `src/adapters/windows/hid_map.py` had no entry — causing the key to normalize to `None`.

**Fix:** Added `(89, False): HID.KEYPAD_EQUALS` to `_SCAN_TO_USAGE` and a corresponding test `test_windows_keyboard_hook_emits_hid_for_keypad_equals`.

**Commit:** `8befb43` — `fix: add missing windows keypad_equals mapping to hid normalization`

### Finding 2 (Rejected — By Design): Collapsed KEYPAD_EQUALS in relay

**Finding:** Legacy relay maps both `HID.EQUALS` and `HID.KEYPAD_EQUALS` to identical payload `(187, 13, False)`.

**Verification:** The implementation plan explicitly specified identical values for both. The HID model preserves the distinction (EQUALS=0x2E vs KEYPAD_EQUALS=0x67) for local use. The legacy relay protocol uses vk_code/scan_code/extended which cannot distinguish these keys — VK_OEM_PLUS (187) and scan code 13 are the same for both on standard US keyboards. This limitation is acknowledged in the spec's Risks section: "Even with a broader HID model, the relay still depends on old Windows-style payload fields. That is acceptable for ANSI 104-key."

**Resolution:** No change needed. The HID distinction is preserved internally; relay collapse is an inherent limitation of the legacy protocol.

## Verification

```
pytest tests/unit tests/integration -q → 310 passed in 0.50s
```

## Commit List (This Round)

| Commit | Description |
|--------|-------------|
| `8befb43` | `fix: add missing windows keypad_equals mapping to hid normalization` |

## All Commits (Entire Feature)

| Commit | Description |
|--------|-------------|
| `c4cd6db` | `feat: expand hid constants for 104-key coverage` |
| `e2ca947` | `feat: expand windows hid mappings for 104-key coverage` |
| `83f1944` | `feat: expand macos hid mappings for 104-key coverage` |
| `a8ffea3` | `feat: complete ansi hid relay mappings` |
| `12fd20f` | `test: lock unsupported iso relay suppression behavior` |
| `8befb43` | `fix: add missing windows keypad_equals mapping to hid normalization` |
