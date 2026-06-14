# CapturedKeyEvent Implementation — Completion Summary

**Spec:** docs/superpowers/specs/2026-06-14-captured-key-event-design.md  
**Plan:** docs/superpowers/plans/2026-06-14-captured-key-event-implementation.md  
**Date:** 2026-06-14  
**Status:** Complete — all 5 tasks implemented, 355 tests passing

## Summary

Introduced `CapturedKeyEvent` as a cross-platform capture wrapper at the input adapter boundary, added `WindowsNativeKeyContext` for Windows raw VK/scan/extended preservation, updated all capture protocols/services to pass `CapturedKeyEvent` end-to-end, routed NVDA Remote forwarding through a legacy payload bridge that prefers native Windows context, and tightened Windows HID semantics for Num Lock-sensitive keypad/navigation keys.

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | `4c8c039` | refactor: add captured key event contract |
| 2 | `9c6c2d7` | feat: emit captured key events from adapters |
| 3 | `db9bd93` | feat: forward native windows payloads for nvda remote |
| 4 | `834c336` | fix: stabilize windows keypad hid mapping |

## What Was Built

### New Files
- `src/adapters/inputs/captured_event.py` — `CapturedKeyEvent` frozen dataclass (wraps `KeyEvent` + optional `native_context`)
- `src/adapters/windows/native_key_context.py` — `WindowsNativeKeyContext` frozen dataclass (`vk_code`, `scan_code`, `extended`)
- `src/apps/nvda_remote/legacy_key_payload_bridge.py` — `legacy_payload_from_captured_event()` bridge (native-context-first, HID fallback)
- `tests/unit/test_nvda_remote_legacy_key_payload_bridge.py` — covers native-context-first and HID fallback paths

### Modified Production Files
- `src/adapters/inputs/base.py` — `InputCapture.set_listener()` now accepts `Callable[[CapturedKeyEvent], ...]`
- `src/application/keyboard.py` — `KeyEventHandler.handle_key_event()` now accepts `CapturedKeyEvent`
- `src/apps/key_echo/service.py` — unwraps `CapturedKeyEvent` → `ModeManager` receives plain `KeyEvent`
- `src/apps/nvda_remote/service.py` — accepts `CapturedKeyEvent`, suppression checks on `key_event`, native context preserved for forwarding via direct `input_forwarding.handle(event)` call when controlling
- `src/apps/nvda_remote/use_cases/input_forwarding.py` — `handle()` accepts `CapturedKeyEvent`, uses `legacy_payload_from_captured_event()` for forwarding
- `src/adapters/windows/keyboard_hook.py` — emits `CapturedKeyEvent(key_event=..., native_context=WindowsNativeKeyContext(...))`
- `src/adapters/macos/keyboard_hook.py` — emits `CapturedKeyEvent(key_event=..., native_context=None)`
- `src/adapters/windows/hid_map.py` — renamed `_VK_TO_USAGE` → `_VK_TO_USAGE_KEYPAD_NAV`, separated `0xF2` special case
- `src/adapters/windows/hotkey.py` — `_handle_key_event` unwraps via `event.key_event`

### Modified Test Files
- `tests/unit/test_keyboard_input_service.py` — added `CapturedKeyEvent` test, updated existing tests
- `tests/unit/test_key_echo_app_service.py` — all `handle_key_event` calls wrapped in `CapturedKeyEvent`
- `tests/unit/test_windows_adapters.py` — 14+ tests updated, 2 hotkey tests updated, 20 new parametrized VK mapping tests
- `tests/unit/test_macos_adapters.py` — 2 tests updated to expect `CapturedKeyEvent`
- `tests/unit/test_nvda_remote_use_cases.py` — 4 tests updated for `CapturedKeyEvent` contract
- `tests/unit/test_nvda_remote_app_service.py` — all tests updated
- `tests/unit/test_app_wx.py` — no changes needed (already aligned)

## Architecture Decisions

- **`KeyEvent` unchanged** — remains pure HID (usage_page, usage, pressed)  
- **`CapturedKeyEvent` at capture boundary** — carries platform native context without polluting shared model  
- **NVDA Remote forwards directly** — `NvdaRemoteAppService.handle_key_event` calls `input_forwarding.handle(event)` directly when controlling, preserving native context through the full path  
- **ModeManager unchanged** — continues receiving plain `KeyEvent` for mode transition logic  
- **Windows bridge `isinstance` dispatch** — isolates Windows-specific knowledge to bridge function, not in shared model  

## Test Results

```
355 passed in 0.59s
```

All focused regression suites pass:
- `tests/unit/test_keyboard_input_service.py` — 3/3
- `tests/unit/test_key_echo_app_service.py` — 19/19
- `tests/unit/test_windows_adapters.py` — 52/52 (including 20 new parametrized VK tests)
- `tests/unit/test_macos_adapters.py` — 36/36
- `tests/unit/test_nvda_remote_*.py` — 21/21
- `tests/unit/test_app_wx.py` — 31/31
- Remaining unit tests — 193/193
