# Special Key Expansion - Implementation Complete

## Summary

Implemented the HID-first special key and JIS key expansion as specified in `docs/superpowers/specs/2026-06-12-special-key-expansion-design.md` following the plan in `docs/superpowers/plans/2026-06-12-special-key-expansion-implementation.md`.

All 320 unit tests pass with no regressions.

## Commits

| Commit | Message |
|--------|---------|
| `398725d` | feat: add hid support for special and jis keys |
| `2de98fd` | feat: add windows hid mappings for special and jis keys |
| `739946d` | feat: add macos hid mappings for special and jis keys |
| `ad4f30c` | feat: add relay support for special keys |

## What Was Implemented

### Task 1: HID Constants (`398725d`)
- Added 10 new HID usage constants: `PRINT_SCREEN`, `SCROLL_LOCK`, `PAUSE`, `NUM_LOCK`, `APPLICATION`, `NON_US_HASH`, `INTERNATIONAL1`, `INTERNATIONAL3`, `INTERNATIONAL4`, `INTERNATIONAL5`
- All placed in correct numerical order within `_HIDKeyboard`
- Added 3 new tests (value assertions + distinction tests)

### Task 2: Windows Adapter (`2de98fd`)
- Added 10 scan-code and vk_code fallback mappings to `_SCAN_TO_USAGE` and `key_event_from_windows`
- Resolved `(41, False)` conflict between GRAVE and NON_US_HASH by using scan code 125 for NON_US_HASH
- Used vk_code fallback (0xF2) for INTERNATIONAL3 which cannot be mapped by scan code alone
- Added 3 new integration-level tests via the hook callback pipeline

### Task 3: macOS Adapter (`739946d`)
- Added 10 virtual key-code mappings to `KEYCODE_TO_USAGE`
- Key codes: 71 (NumLock), 93 (Int1), 94 (NonUSHash), 95 (Int5), 102 (Int3), 104 (Int4), 105 (PrintScreen), 107 (ScrollLock), 110 (Application), 113 (Pause)
- Added 2 new test functions covering all 10 keys

### Task 4: Relay & Safety (`ad4f30c`)
- **Relay-capable keys** added to `_USAGE_TO_LEGACY`: `PRINT_SCREEN` (44/55/True), `SCROLL_LOCK` (145/70/False), `NUM_LOCK` (144/69/True), `APPLICATION` (93/93/True)
- **Local-only keys** added to `_EXPLICIT_UNSUPPORTED`: `PAUSE`, `NON_US_HASH`, `INTERNATIONAL1/3/4/5` (plus existing `NON_US_BACKSLASH`)
- Refactored `key_event_to_legacy_remote_payload` to use dict-based lookup instead of inline if-statement
- Added 7 new tests: 4 positive (relay mapping), 2 negative (explicit unsupported), 1 forwarding safety (suppress + log in control mode)

## Key Design Decisions

1. **Pause is explicitly local-only** — The Pause key requires a 6-byte scan code sequence that cannot be expressed as a single (vk_code, scan_code, extended) tuple in the legacy relay format.
2. **JIS keys are HID-capable but relay-local-only** — All JIS keys are fully normalized into HID on both Windows and macOS, usable by local app logic. None are relayed through the legacy payload due to mapping instability.
3. **Safety preserved** — Unsupported relay keys continue to raise `ValueError` in `legacy_key_payload.py`, the forwarding use case logs the failure and returns `SUPPRESS` in control mode.

## Test Results

```
320 passed in 0.52s
```
