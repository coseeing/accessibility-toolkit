# Task 1 Finish Report

## Review Finding

Confirmed.

`docs/superpowers/review_task0.md` reported that Windows default HID forwarding could serialize
`HID.KEYPAD_EQUALS` with the wrong scan code. The repository's Windows HID map treats Windows
`scan_code=89, extended=False` as `HID.KEYPAD_EQUALS`, but the legacy payload table serialized the
same HID usage back as `scan_code=13`, which is the main `HID.EQUALS` scan code.

The suggestion is correct for this codebase because the new default forwarding path ignores the
native Windows payload and uses the HID-derived legacy payload. That made the existing
`KEYPAD_EQUALS` collapse observable on Windows, not only on non-Windows senders.

## Changes

- Updated `src/apps/nvda_remote/legacy_key_payload.py` so `HID.KEYPAD_EQUALS` maps to
  `vk=0xBB, scan=89, extended=False`.
- Updated the keypad operator mapping test to expect scan `89` for `HID.KEYPAD_EQUALS`.
- Added a Windows keypad HID-to-legacy round-trip consistency test that verifies keypad/operator
  usages produced by `adapters.windows.hid_map.key_event_from_windows()` serialize back with the
  same Windows-style `scan_code` and `extended` values. Numeric keypad keys still allow their
  NumLock-dependent `vk_code` semantic remap while preserving scan/extended.
- Updated the English and Traditional Chinese design specs plus the implementation plan to use
  `KEYPAD_EQUALS -> vk=0xBB, scan=89, extended=False`.

## Red/Green Verification

Before changing production code, the focused tests failed as expected:

```bash
pytest tests/unit/test_nvda_remote_legacy_key_payload.py::test_keypad_operator_keys_ignore_num_lock_state \
  tests/unit/test_nvda_remote_legacy_key_payload.py::test_windows_keypad_hid_payload_preserves_scan_and_extended -v
```

Result: `2 failed, 32 passed`

The failures were both the intended `KEYPAD_EQUALS` scan mismatch: actual `scan_code=13`, expected
`scan_code=89`.

After the fix, the same focused tests passed:

```bash
pytest tests/unit/test_nvda_remote_legacy_key_payload.py::test_keypad_operator_keys_ignore_num_lock_state \
  tests/unit/test_nvda_remote_legacy_key_payload.py::test_windows_keypad_hid_payload_preserves_scan_and_extended -v
```

Result: `34 passed`

Related test set:

```bash
pytest tests/unit/test_nvda_remote_legacy_key_payload.py tests/unit/test_windows_adapters.py -v
```

Result: `137 passed`

Full suite:

```bash
pytest tests/unit tests/integration -v
```

Result: `565 passed`

## Notes

No Windows hardware test was run in this environment. The validation is based on the repository's
own Windows low-level hook test data, the Windows HID map, the legacy payload table, and the full
pytest suite.
