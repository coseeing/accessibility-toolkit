# HID 104-Key Expansion Review

Reviewed commits in chronological order from `docs/superpowers/finish_task0.md`:

1. `c4cd6db` `feat: expand hid constants for 104-key coverage`
2. `e2ca947` `feat: expand windows hid mappings for 104-key coverage`
3. `83f1944` `feat: expand macos hid mappings for 104-key coverage`
4. `a8ffea3` `feat: complete ansi hid relay mappings`
5. `12fd20f` `test: lock unsupported iso relay suppression behavior`

Reviewed against:

- `docs/superpowers/specs/2026-06-12-hid-104-key-expansion-design.md`
- `docs/superpowers/plans/2026-06-12-hid-104-key-expansion-implementation.md`

## Findings

1. Medium: Windows normalization still drops `HID.KEYPAD_EQUALS`, so the new HID model is not actually complete across platforms. `src/adapters/windows/hid_map.py` adds the rest of the expanded keypad set, but there is no `(89, False)` entry for keypad equals, while the spec and plan both include `KeypadEquals` in scope and macOS already emits it (`src/adapters/windows/hid_map.py:3`, `src/adapters/macos/hid_map.py:88`). On Windows, a keypad-equals event will still normalize to `None` and disappear before any app logic can see it.

2. Medium: The legacy relay adapter collapses `HID.KEYPAD_EQUALS` into the main `=` key, which loses the HID distinction the spec explicitly required to preserve. `src/apps/nvda_remote/legacy_key_payload.py:103` maps `HID.KEYPAD_EQUALS` to `(187, 13, False)`, the same payload used by `HID.EQUALS` at `src/apps/nvda_remote/legacy_key_payload.py:47`. That means a macOS sender can capture keypad equals as a distinct HID usage, but once it is forwarded through NVDA Remote it will be injected on the receiver as the main-cluster equals key instead of keypad equals.

## Notes

- I reran the directly affected unit suite:
  - `pytest tests/unit/test_hid_keys.py tests/unit/test_windows_adapters.py tests/unit/test_macos_adapters.py tests/unit/test_nvda_remote_legacy_key_payload.py tests/unit/test_nvda_remote_use_cases.py -q`
  - Result: `105 passed`
- I did not find additional issues in the other expanded punctuation, navigation, numpad, or `NON_US_BACKSLASH` paths beyond the `KEYPAD_EQUALS` gaps above.
