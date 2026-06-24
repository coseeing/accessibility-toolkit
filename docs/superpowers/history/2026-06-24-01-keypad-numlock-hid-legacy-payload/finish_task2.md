# Task 2 Finish Report

## Review Finding

Confirmed.

`docs/superpowers/review_task1.md` reported a stale Windows adapter test name:
`test_key_event_from_windows_prefers_vk_for_numlock_sensitive_keypad_navigation_events`.

The finding is correct. `src/adapters/windows/hid_map.py` now resolves by `(scan_code, extended)`
before falling back to `vk_code`, and the test assertions now protect NumLock-off keypad origin
preservation. For example, `vk=0x28, scan=80, extended=False` resolves to `HID.KEYPAD_2`, not
`HID.DOWN`. The old `prefers_vk` name described the opposite precedence and could mislead future
changes.

## Changes

- Renamed the test to
  `test_key_event_from_windows_preserves_keypad_origin_for_numlock_off_navigation_vks`.
- Kept the assertions unchanged because they already matched the intended behavior.
- Committed the pending Task 1 repair together with this review cleanup, including the
  `KEYPAD_EQUALS` scan-code fix, scan-first Windows HID parsing, round-trip coverage, and matching
  spec/plan/review/finish docs.

## Verification

Focused review verification:

```bash
pytest tests/unit/test_nvda_remote_legacy_key_payload.py::test_keypad_operator_keys_ignore_num_lock_state \
  tests/unit/test_nvda_remote_legacy_key_payload.py::test_windows_keypad_hid_payload_preserves_scan_and_extended \
  tests/unit/test_windows_adapters.py::test_key_event_from_windows_preserves_keypad_origin_for_numlock_off_navigation_vks -v
```

Result: `44 passed`

Full suite:

```bash
pytest tests/unit tests/integration -v
```

Result: `565 passed`

## New Commits

```text
d313e04 fix: preserve keypad equals legacy scan
```

Note: this finish report is committed separately after the repair commit so it can include the
repair commit hash.
