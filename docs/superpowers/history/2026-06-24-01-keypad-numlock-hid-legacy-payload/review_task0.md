# Review Task 0

## Findings

### Important: Windows default HID forwarding sends `KEYPAD_EQUALS` with the wrong scan code

Commit: `6f5b68d feat: default remote payload bridge to hid mapping` makes Windows default to HID conversion even when `WindowsNativeKeyContext` exists. That exposes an existing stale mapping in `src/apps/nvda_remote/legacy_key_payload.py`.

Reference:
- `src/apps/nvda_remote/legacy_key_payload.py:103` maps `HID.KEYPAD_EQUALS` to `vk=0xBB, scan=13, extended=False`.
- `src/adapters/windows/hid_map.py:107` maps Windows scan `(89, False)` to `HID.KEYPAD_EQUALS`.

Why this matters:
- With native forwarding enabled, a Windows `KEYPAD_EQUALS` event can preserve its native scan code.
- With the new default HID path, the same captured HID usage is serialized back as scan `13`, which is also the main `HID.EQUALS` scan code in `src/apps/nvda_remote/legacy_key_payload.py:47` and `src/adapters/windows/hid_map.py:21`.
- This loses the keypad-origin distinction for this key and can make the remote NVDA side interpret keypad equals as the main equals key, depending on its Windows/NVDA key-name resolution.

This mismatch is also present in the spec and plan:
- `docs/superpowers/specs/2026-06-24-keypad-numlock-hid-legacy-payload-design.md:111`
- `docs/superpowers/plans/2026-06-24-keypad-numlock-hid-legacy-payload.md:207`

Recommendation:
- Validate `KEYPAD_EQUALS` against actual Windows low-level hook data and the repo's own Windows HID map.
- If scan `89` is the intended Windows keypad-equals scan code, update the spec, plan, implementation, and tests to use `HID.KEYPAD_EQUALS -> vk=0xBB, scan=89, extended=False`.
- Add a round-trip consistency test for Windows keypad usages so any HID usage produced by `src/adapters/windows/hid_map.py` serializes back to the same Windows-style `scan_code` and `extended` tuple unless an explicit NumLock semantic remap is expected.

## Reviewed Commit Order

Reviewed only the commits listed in `docs/superpowers/finish_task0.md`, ordered by commit time from old to new:

1. `facf0c1 feat: capture numlock state with key events`
2. `0d6a617 feat: cover numlock state edge cases`
3. `fd51649 feat: map keypad payloads by numlock state`
4. `5db088f fix: require keyword numlock payload arg`
5. `6f5b68d feat: default remote payload bridge to hid mapping`
6. `88636dd feat: add windows native payload forwarding switch`
7. `a2f1ff0 fix: wire native payload bootstrap flag`
8. `1cbe5ae fix: forward numlock while passing through locally`
9. `eb092c3 refactor: clarify numlock pass-through`

## Scope Notes

The NumLock-sensitive keypad mapping for `KEYPAD_0..9` and `KEYPAD_DECIMAL` matches the requested Windows semantics: NumLock on emits `VK_NUMPAD*`, NumLock off emits navigation/editing `vk_code` with keypad scan code and `extended=False`.

The bridge behavior matches the requested default: `use_windows_native_key_payload=False` ignores `WindowsNativeKeyContext` and uses HID plus `num_lock_on`; native forwarding remains available through the explicit switch.

The runtime bootstrap wires `NVDA_REMOTE_USE_WINDOWS_NATIVE_KEY_PAYLOAD` into `NvdaRemoteAppService`, with default `False`.

The controlling-mode NumLock path now forwards keydown and keyup to the remote side while passing through locally when a Windows native context exists. Non-controlling mode remains local pass-through without forwarding.

## Residual Risks

No Windows hardware test was run as part of this review. The review relied on commit diffs, repository tests, and internal table consistency.

The tests cover the requested numpad NumLock table, but they do not currently protect consistency between `src/adapters/windows/hid_map.py` and `src/apps/nvda_remote/legacy_key_payload.py` for all keypad/operator usages. That is the gap that allowed the `KEYPAD_EQUALS` inconsistency to survive while still passing the suite.
