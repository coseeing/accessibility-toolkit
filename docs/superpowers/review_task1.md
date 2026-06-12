# HID Keyboard Input Fix Review

## Findings

1. **High: The fix is still incomplete for ordinary standard keyboard keys because `-` and `=` remain unsupported end-to-end on both platforms.**
   The previous review explicitly called out missing ordinary keys such as `=` and `-`. This fix expands letters, digits, and a subset of controls, but the shared HID model still has no constants for those keys ([src/interop/key/hid.py](/workspace/nvda-remote-client/src/interop/key/hid.py:5)), the Windows and macOS platform maps still return `None` for those scan/key codes ([src/adapters/windows/hid_map.py](/workspace/nvda-remote-client/src/adapters/windows/hid_map.py:3), [src/adapters/macos/hid_map.py](/workspace/nvda-remote-client/src/adapters/macos/hid_map.py:3)), and the legacy relay adapter cannot possibly forward them because it has no corresponding usages to map ([src/apps/nvda_remote/legacy_key_payload.py](/workspace/nvda-remote-client/src/apps/nvda_remote/legacy_key_payload.py:3)). I verified this directly: Windows drops scan codes `12`/`13` and macOS drops key codes `27`/`24`. So this does not fully resolve the earlier “ordinary keys disappear” finding, despite `finish_task1.md` claiming coverage for “all standard `0x07` keys”.

2. **High: Unsupported HID usages now pass through locally during remote-control mode, which can trigger actions on the controlling machine instead of being safely contained.**
   The new error handling in `NvdaRemoteInputForwardingUseCase.handle()` catches `ValueError` from the relay adapter and returns `KeyEventDecision.PASS_THROUGH` ([src/apps/nvda_remote/use_cases/input_forwarding.py](/workspace/nvda-remote-client/src/apps/nvda_remote/use_cases/input_forwarding.py:41)). That avoids the previous crash, but it introduces a new behavioral risk: while remote control is active, any still-unsupported key now leaks to the local machine. In this project, active control mode has otherwise been built around suppressing local keyboard effects while forwarding remotely, so letting unsupported keys fall through can fire local shortcuts or edit local content unexpectedly. The spec required rejecting unsupported relay mappings with a clear signal or log, not re-enabling local key delivery during control mode.

3. **Medium: The new Meta-key relay mapping likely breaks compatibility because it marks Windows logo keys as non-extended.**
   The fix adds `LEFT_META` and `RIGHT_META` to the legacy relay adapter, but hardcodes `extended=False` for both ([src/apps/nvda_remote/legacy_key_payload.py](/workspace/nvda-remote-client/src/apps/nvda_remote/legacy_key_payload.py:18)). That is inconsistent with this codebase’s earlier Windows-style semantics: before the HID migration, the macOS-to-Windows translation treated both Command keys as extended keys when generating the old `(vk, scan, extended)` event model. Using scan codes `91`/`92` with `extended=False` is therefore a likely compatibility regression for remote Windows injection of Meta/Command/Windows keys.

## Verified Fixes

- The original Windows hotkey fallback bug is fixed. `HID.F10` now maps to `0x79` and `HID.ENTER` maps to `0x0D` in [src/adapters/windows/hotkey.py](/workspace/nvda-remote-client/src/adapters/windows/hotkey.py:12).
- The mapping coverage for letters, digits, and several control keys is materially better than before.
- The previous crash path on unsupported relay mappings is gone; the code now logs and returns instead of raising out of the forwarding use case.

## Review Inputs

- Completion note: [docs/superpowers/finish_task1.md](/workspace/nvda-remote-client/docs/superpowers/finish_task1.md)
- Previous review: [docs/superpowers/review_task0.md](/workspace/nvda-remote-client/docs/superpowers/review_task0.md)
- Spec: [docs/superpowers/specs/2026-06-12-hid-keyboard-design.md](/workspace/nvda-remote-client/docs/superpowers/specs/2026-06-12-hid-keyboard-design.md)
- Plan: [docs/superpowers/plans/2026-06-12-hid-keyboard-implementation.md](/workspace/nvda-remote-client/docs/superpowers/plans/2026-06-12-hid-keyboard-implementation.md)

## Commit Review Order

Reviewed in commit-time order as requested:

1. `757d679` `fix: expand HID maps and legacy adapter to cover all standard 0x07 keys`

## Verification Notes

- I verified the hotkey fix directly: `HID.F10 -> 0x79`, `HID.ENTER -> 0x0D`, `HID.F11 -> 0x7A`.
- I verified that `-` and `=` are still unsupported in both current platform maps.
- I ran the newly added targeted tests for Windows digits/letters, macOS digits, and unsupported relay pass-through; those tests pass, but they do not cover the remaining unsupported ordinary keys or the local pass-through risk.
