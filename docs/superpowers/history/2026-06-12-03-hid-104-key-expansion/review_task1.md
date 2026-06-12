# HID 104-Key Expansion Review — Task 1

Reviewed commits in chronological order from `docs/superpowers/finish_task1.md`:

1. `8befb43` `fix: add missing windows keypad_equals mapping to hid normalization`

Reviewed against:

- `docs/superpowers/specs/2026-06-12-hid-104-key-expansion-design.md`
- `docs/superpowers/plans/2026-06-12-hid-104-key-expansion-implementation.md`
- `docs/superpowers/review_task0.md`

## Findings

1. Low: the new Windows `KEYPAD_EQUALS` regression test is flaky when run in isolation, so it does not reliably prove the fix it was added to cover. In [`tests/unit/test_windows_adapters.py`](/workspace/nvda-remote-client/tests/unit/test_windows_adapters.py:562), the test passes a pointer to a temporary `FakeKbdLlHookStruct(...)` inline. Running `pytest tests/unit/test_windows_adapters.py::test_windows_keyboard_hook_emits_hid_for_keypad_equals -q` currently fails with `seen == []`, while the same code path works if the struct is first stored in a local variable before `ctypes.addressof(...)`. The product fix itself appears correct, but this test should be rewritten to use a named `key_data` object like the stable tests elsewhere in the file.

## Notes

- Functional status:
  - The Windows mapping gap from `review_task0.md` is fixed. `src/adapters/windows/hid_map.py` now includes `(89, False): HID.KEYPAD_EQUALS`, and direct verification of `key_event_from_windows(vk_code=0xBB, scan_code=89, extended=False, pressed=True)` returns `KeyEvent(... usage=HID.KEYPAD_EQUALS ...)`.
  - I do not consider the relay `KEYPAD_EQUALS` collapse a new finding in this round. This fix did not change relay behavior, and the current implementation remains consistent with the written implementation plan.
- Verification run:
  - `pytest tests/unit/test_windows_adapters.py -q` → pass
  - `pytest tests/unit tests/integration -q` → `310 passed`
  - `pytest tests/unit/test_windows_adapters.py::test_windows_keyboard_hook_emits_hid_for_keypad_equals -q` → fails due to the flaky test setup described above
