# HID Keyboard Input Review

## Findings

1. **High: Windows hotkey registration silently falls back to F11 for unsupported HID usages, so `key_echo` cannot be activated with its configured `F10` hotkey on Windows.**
   `KeyEchoAppFacade` now declares `enter_usage = HID.F10` and `build_runtime()` passes that usage into `create_hotkey_capture()` ([src/apps/key_echo/facade.py](/workspace/nvda-remote-client/src/apps/key_echo/facade.py:15), [src/apps/key_echo/main.py](/workspace/nvda-remote-client/src/apps/key_echo/main.py:34)). However, `WindowsHotkeyCapture` only knows how to translate `HID.F11`; every other usage falls back to `F11_VK` via `_USAGE_TO_VK.get(self._usage, F11_VK)` ([src/adapters/windows/hotkey.py](/workspace/nvda-remote-client/src/adapters/windows/hotkey.py:17), [src/adapters/windows/hotkey.py](/workspace/nvda-remote-client/src/adapters/windows/hotkey.py:119)). I confirmed this directly: both `HID.F10` and `HID.ENTER` resolve to `0x7a` under the current code path. This is a user-visible functional break on Windows introduced in `20eb32c`.

2. **High: The HID capture maps cover only a small subset of `usage page 0x07`, so many ordinary keyboard keys now disappear before they reach application logic.**
   The design and plan call for the HID-first pipeline to support standard keyboard keys such as letters A-Z, digits 0-9, Enter, Escape, Tab, Space, arrows, and modifiers. The actual platform maps are much narrower. On Windows, `_SCAN_TO_USAGE` only contains `A`, `B`, `M`, a few navigation keys, function keys, and modifiers ([src/adapters/windows/hid_map.py](/workspace/nvda-remote-client/src/adapters/windows/hid_map.py:3)); keys like `C` (scan 46) and `1` (scan 2) return `None`. On macOS, `KEYCODE_TO_USAGE` includes letters and a handful of control keys, but omits digits and common punctuation such as `=` and `-` ([src/adapters/macos/hid_map.py](/workspace/nvda-remote-client/src/adapters/macos/hid_map.py:3)). I verified this with direct calls: Windows drops `C` and `1`, and macOS drops `1` and `=`. This regression was introduced by `236ebf3`, which replaced the much larger `macOS -> Windows-style` table with a significantly smaller HID table.

3. **High: NVDA Remote forwarding now rejects many standard HID keys, so relay compatibility is preserved only for a tiny subset of the keyboard.**
   The approved design explicitly keeps the relay wire format unchanged while supporting standard `0x07` keyboard keys end-to-end. The new `key_event_to_legacy_remote_payload()` adapter only maps 16 usages: `A`, `B`, `Enter`, `Escape`, `Tab`, `Space`, `F11`, arrows, and a few modifiers ([src/apps/nvda_remote/legacy_key_payload.py](/workspace/nvda-remote-client/src/apps/nvda_remote/legacy_key_payload.py:3)). Anything else raises `ValueError` ([src/apps/nvda_remote/legacy_key_payload.py](/workspace/nvda-remote-client/src/apps/nvda_remote/legacy_key_payload.py:24)). I confirmed that `DIGIT_1`, `DIGIT_0`, `C`, and `LEFT_META` all fail immediately with `Unsupported HID usage for remote payload`. Because `NvdaRemoteInputForwardingUseCase.handle()` calls this adapter directly without guarding the failure path ([src/apps/nvda_remote/use_cases/input_forwarding.py](/workspace/nvda-remote-client/src/apps/nvda_remote/use_cases/input_forwarding.py:24)), the implementation does not satisfy the plan’s “standard keyboard keys run end-to-end” requirement and would either drop or blow up on unsupported usages. This gap was introduced in `20eb32c`.

## Reviewed Inputs

- Completion note: [docs/superpowers/finish_task0.md](/workspace/nvda-remote-client/docs/superpowers/finish_task0.md)
- Spec: [docs/superpowers/specs/2026-06-12-hid-keyboard-design.md](/workspace/nvda-remote-client/docs/superpowers/specs/2026-06-12-hid-keyboard-design.md)
- Plan: [docs/superpowers/plans/2026-06-12-hid-keyboard-implementation.md](/workspace/nvda-remote-client/docs/superpowers/plans/2026-06-12-hid-keyboard-implementation.md)

## Commit Review Order

Reviewed in commit-time order as requested:

1. `95bef54` `feat: add HID keyboard event model`
2. `236ebf3` `feat: normalize platform key capture to HID`
3. `1b28104` `refactor: use HID in shared input policies`
4. `20eb32c` `test: complete HID keyboard regression coverage`

## Notes

- I did not find issues in `95bef54` or `1b28104` by themselves; the problems appear when the later platform mappings and app/protocol integrations are examined against the approved spec and plan.
- The existing green test result is not strong evidence here because the suite does not cover the real Windows `F10` hotkey path or broad standard-key coverage for the new HID maps and legacy relay adapter.
