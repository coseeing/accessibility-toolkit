# Review Task 1

## Findings

No Critical or Important findings.

### Minor: Windows adapter test name now describes the opposite precedence

Reference:
- `tests/unit/test_windows_adapters.py:997`

The test function is still named `test_key_event_from_windows_prefers_vk_for_numlock_sensitive_keypad_navigation_events`, but the repaired implementation now intentionally resolves by `(scan_code, extended)` before falling back to `vk_code`.

This is not a runtime bug. The assertions are correct and protect the desired behavior: NumLock-off keypad navigation events such as `vk=0x28, scan=80, extended=False` resolve to `HID.KEYPAD_2`, not the main `HID.DOWN`. The stale test name is still worth cleaning up because it can mislead future maintainers into reintroducing the previous VK-priority behavior.

Recommendation:
- Rename the test to something like `test_key_event_from_windows_preserves_keypad_origin_for_numlock_off_navigation_vks`.

## Completion Assessment

The fix completes the finding from `docs/superpowers/review_task0.md`.

Verified repair points:
- `src/apps/nvda_remote/legacy_key_payload.py:103` now maps `HID.KEYPAD_EQUALS` to `vk=0xBB, scan=89, extended=False`.
- `tests/unit/test_nvda_remote_legacy_key_payload.py:217` now expects scan `89` for `HID.KEYPAD_EQUALS`.
- `tests/unit/test_nvda_remote_legacy_key_payload.py:237` adds round-trip coverage from Windows HID map output into legacy payload scan/extended preservation.
- `src/adapters/windows/hid_map.py:155` now resolves by `(scan_code, extended)` before `vk_code` fallback, which is necessary to preserve keypad origin for NumLock-off events.
- The English spec, Traditional Chinese spec, and implementation plan all now document `KEYPAD_EQUALS -> vk=0xBB, scan=89, extended=False`.

The scan-first Windows HID parsing change does not appear to introduce a regression for main navigation keys because those still carry `extended=True`, for example main Down is `(scan=80, extended=True) -> HID.DOWN`, while numpad 2 with NumLock off is `(scan=80, extended=False) -> HID.KEYPAD_2`.

## Commit Scope

`docs/superpowers/finish_task1.md` does not list commit hashes. `git log` also shows `HEAD` still at `eb092c3`, with the Task 1 repair present as uncommitted working-tree changes. Because the requested "listed commits only" set is empty, there was no commit chronology to review.

Reviewed the current working-tree diff described by `docs/superpowers/finish_task1.md` instead:
- `src/apps/nvda_remote/legacy_key_payload.py`
- `src/adapters/windows/hid_map.py`
- `tests/unit/test_nvda_remote_legacy_key_payload.py`
- `tests/unit/test_windows_adapters.py`
- `docs/superpowers/specs/2026-06-24-keypad-numlock-hid-legacy-payload-design.md`
- `docs/superpowers/specs/2026-06-24-keypad-numlock-hid-legacy-payload-design_zh-TW.md`
- `docs/superpowers/plans/2026-06-24-keypad-numlock-hid-legacy-payload.md`

## Verification

Ran focused review verification:

```bash
pytest tests/unit/test_nvda_remote_legacy_key_payload.py::test_keypad_operator_keys_ignore_num_lock_state \
  tests/unit/test_nvda_remote_legacy_key_payload.py::test_windows_keypad_hid_payload_preserves_scan_and_extended \
  tests/unit/test_windows_adapters.py::test_key_event_from_windows_prefers_vk_for_numlock_sensitive_keypad_navigation_events -v
```

Result: `44 passed`.

I did not rerun the full suite during this review. `docs/superpowers/finish_task1.md` reports `pytest tests/unit tests/integration -v` as `565 passed`.

## Residual Risks

No Windows hardware test was run. The review relies on repository-level Windows hook fixtures, internal map consistency, and pytest coverage.
