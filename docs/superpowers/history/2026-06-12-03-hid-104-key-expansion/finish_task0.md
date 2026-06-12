# HID 104-Key Expansion — Completion Report

## Implementation Summary

Expanded the existing HID-first keyboard model from partial coverage to full ANSI 104-key coverage plus the ISO `NonUsBackslash` key across all layers (shared HID constants, Windows/macOS platform adapters, and NVDA Remote relay adapter).

## Verification

```
pytest tests/unit tests/integration -v  →  309 passed in 0.50s
```

## Commit List

| Commit | Description |
|--------|-------------|
| `c4cd6db` | `feat: expand hid constants for 104-key coverage` — Added 35 new HID usage constants (punctuation, navigation, numpad, caps lock, ISO extra) to `src/interop/key/hid.py` |
| `e2ca947` | `feat: expand windows hid mappings for 104-key coverage` — Added 32 scan-code mappings to `src/adapters/windows/hid_map.py` |
| `83f1944` | `feat: expand macos hid mappings for 104-key coverage` — Added 35 key-code mappings to `src/adapters/macos/hid_map.py` |
| `a8ffea3` | `feat: complete ansi hid relay mappings` — Added 33 ANSI relay mappings + explicit `NON_US_BACKSLASH` rejection in `src/apps/nvda_remote/legacy_key_payload.py` |
| `12fd20f` | `test: lock unsupported iso relay suppression behavior` — Added forwarding regression test for `NON_US_BACKSLASH` in control mode |

## Files Modified

- `src/interop/key/hid.py` — HID constants (101 total, grouped by keyboard region)
- `src/adapters/windows/hid_map.py` — Windows scan-code → HID lookup table
- `src/adapters/macos/hid_map.py` — macOS key-code → HID lookup table
- `src/apps/nvda_remote/legacy_key_payload.py` — HID → legacy relay payload adapter
- `tests/unit/test_hid_keys.py` — Added constant verification + main/numpad distinction tests
- `tests/unit/test_windows_adapters.py` — Added 4 Windows mapping tests
- `tests/unit/test_macos_adapters.py` — Added 4 macOS mapping tests
- `tests/unit/test_nvda_remote_legacy_key_payload.py` — Added 5 relay mapping tests
- `tests/unit/test_nvda_remote_use_cases.py` — Added forwarding suppression test

## Key Design Decisions

1. **Architecture unchanged** — HID remains the only shared input representation; no new abstractions introduced
2. **NON_US_BACKSLASH local-only** — Supported in HID constants and platform adapters, but explicitly rejected at the relay boundary with a clear `ValueError` message
3. **Grouped constants** — HID constants organized by keyboard region (alphanumeric, punctuation, function keys, navigation, numpad, modifiers)
4. **Main-cluster vs numpad distinction** — Preserved throughout (e.g., `SLASH` ≠ `KEYPAD_DIVIDE`, `PERIOD` ≠ `KEYPAD_DECIMAL`)
