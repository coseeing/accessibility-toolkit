# Review Task 0 - Fix Summary

## Review Source

`docs/superpowers/review_task0.md` — 4 findings verified against codebase and spec, all confirmed correct.

## Fixes Applied (commit `735d9a6`)

### 1. High: Exit action does not terminate wx application

**Problem:** `ToolAppShell.shutdown()` destroyed the tray icon and called `controller.shutdown()`, but never called `wx.ExitMainLoop()`. This left the app process running with hidden frames.

**Fix:** `tool_app_shell.py:29` — Added `wx.GetApp().ExitMainLoop()` at the end of `shutdown()`. This imports `wx` and triggers proper app termination.

**Ref:** `src/apps/shared/tool_app_shell.py:29`

### 2. Medium: Double shutdown wiring

**Problem:** Both `ToolAppShell.shutdown()` and each `wx.App.OnExit()` called `controller.shutdown()`. When Exit was triggered via tray menu, the controller was shut down twice.

**Fix:** Removed `controller.shutdown()` from both `EchoApp.OnExit()` and `NvdaRemoteApp.OnExit()`. The shell's `shutdown()` is the single shutdown path.

**Ref:** `src/ui/echo/app.py:21-22`, `src/ui/nvda_remote/app.py:21-22`

### 3. Medium: ModeManager ignores exit_active() failure

**Problem:** `exit_active_mode()` ignored the return value of `InputActivationUseCase.exit_active()`. When hotkey capture restart failed, the mode was still marked as exited, creating silent state mismatch between UI state and actual capture state.

**Fix:** `mode_manager.py:46-48` — `exit_active_mode()` now checks the return value. If `exit_active()` returns `False`, the mode is NOT exited, `active_mode_id` is NOT cleared, and `mode.exit()` is NOT called. The error was already reported by `InputActivationUseCase` (no redundant notification).

**Ref:** `src/apps/shared/mode_manager.py:46-48`

### 4. Low: Hard-coded tray tooltip

**Problem:** `ToolTrayIcon` had `"NVDA Remote"` hard-coded as the tooltip for all apps, including `key_echo`.

**Fix:** `tray_icon.py:6` — Added `app_name` parameter (default `"NVDA Remote"`). `ToolAppShell` passes `app_name` through. `EchoApp` passes `app_name="Key Echo"`, `NvdaRemoteApp` uses the default.

**Ref:** `src/apps/shared/tray_icon.py:6`, `src/ui/echo/app.py:20`

## Test Updates

| File | Change |
|------|--------|
| `test_tool_app_shell.py` | Added `FakeApp.ExitMainLoop()` and `fake_wx.GetApp()` |
| `test_app_wx.py` | Added `ExitMainLoop()` to fake `App`, added `GetApp()` returning fallback |
| `test_nvda_remote_app_service.py` | Updated `test_nvda_remote_service_stop_control_handles_hotkey_start_failure`: control_state now stays `CONTROLLING` (not `CONNECTED`) when exit fails; only one error event expected |
| `test_mode_manager.py` | Added `FakeActivation.fail_exit` flag; added `test_mode_manager_preserves_active_mode_when_exit_active_fails` |

## Result

```
262 passed (257 unit + 5 integration)
```
