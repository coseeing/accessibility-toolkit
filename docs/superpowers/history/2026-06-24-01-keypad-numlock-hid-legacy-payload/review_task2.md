# Review Task 2

## Findings

No Critical or Important findings.

### Minor: Implementation plan still references deleted 2026-06-23 spec paths

Commit: `d313e04 fix: preserve keypad equals legacy scan`

References:
- `docs/superpowers/plans/2026-06-24-keypad-numlock-hid-legacy-payload.md:702`
- `docs/superpowers/plans/2026-06-24-keypad-numlock-hid-legacy-payload.md:703`
- `docs/superpowers/plans/2026-06-24-keypad-numlock-hid-legacy-payload.md:739`
- `docs/superpowers/plans/2026-06-24-keypad-numlock-hid-legacy-payload.md:740`
- `docs/superpowers/plans/2026-06-24-keypad-numlock-hid-legacy-payload.md:754`

The same commit deletes `docs/superpowers/specs/2026-06-23-keypad-numlock-hid-legacy-payload-design.md` and adds the 2026-06-24 spec files, but the implementation plan still tells readers to verify, read, and `git add` the deleted 2026-06-23 paths.

This is not a runtime issue and does not affect the keypad fix. It is still worth correcting because anyone following the plan later will run commands against paths that no longer exist.

Recommendation:
- Update those plan references to:
  - `docs/superpowers/specs/2026-06-24-keypad-numlock-hid-legacy-payload-design.md`
  - `docs/superpowers/specs/2026-06-24-keypad-numlock-hid-legacy-payload-design_zh-TW.md`

## Completion Assessment

The Task 2 fix completes the finding from `docs/superpowers/review_task1.md`.

Verified repair points:
- `tests/unit/test_windows_adapters.py:997` now uses `test_key_event_from_windows_preserves_keypad_origin_for_numlock_off_navigation_vks`, so the test name matches the scan/extended-first behavior.
- `src/adapters/windows/hid_map.py:155` still resolves by `(scan_code, extended)` before `vk_code` fallback, preserving keypad origin for NumLock-off navigation Vks.
- `src/apps/nvda_remote/legacy_key_payload.py:103` still maps `HID.KEYPAD_EQUALS` to `vk=0xBB, scan=89, extended=False`.
- `tests/unit/test_nvda_remote_legacy_key_payload.py:237` keeps the Windows keypad HID-to-legacy scan/extended preservation coverage.

I did not find a new code-level regression from the test rename or the committed Task 1 repair. Main navigation keys remain distinguishable from numpad-origin keys through `extended=True` vs `extended=False`.

## Reviewed Commit Order

Reviewed only the commit listed in `docs/superpowers/finish_task2.md`:

1. `d313e04 fix: preserve keypad equals legacy scan`

Note: `f8eef42 docs: record keypad scan review finish` exists after `d313e04`, but `finish_task2.md` explicitly says the finish report is committed separately after the repair commit. It is not included in the listed repair commits, so it was not reviewed as implementation scope.

## Verification

Ran focused review verification:

```bash
pytest tests/unit/test_nvda_remote_legacy_key_payload.py::test_keypad_operator_keys_ignore_num_lock_state \
  tests/unit/test_nvda_remote_legacy_key_payload.py::test_windows_keypad_hid_payload_preserves_scan_and_extended \
  tests/unit/test_windows_adapters.py::test_key_event_from_windows_preserves_keypad_origin_for_numlock_off_navigation_vks -v
```

Result: `44 passed`.

I did not rerun the full suite during this review. `docs/superpowers/finish_task2.md` reports `pytest tests/unit tests/integration -v` as `565 passed`.

## Residual Risks

No Windows hardware test was run. The review relies on repository-level Windows hook fixtures, internal map consistency, commit diff inspection, and focused pytest coverage.
