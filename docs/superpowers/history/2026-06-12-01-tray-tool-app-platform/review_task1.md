# Review Task 1

Reviewed in commit order from oldest to newest, using:

- `docs/superpowers/finish_task1.md`
- `docs/superpowers/review_task0.md`
- `docs/superpowers/specs/2026-06-12-tray-tool-app-platform-design.md`

## Findings

No findings.

## Verification Summary

The single listed fix commit was reviewed in chronological order:

- `735d9a6` `fix: address tray shell shutdown, double-exit, mode exit failure, and tray tooltip issues`

### Previously reported issues

1. **Tray/menu-bar `Exit` did not terminate the wx app**
   - Fixed. `ToolAppShell.shutdown()` now calls `wx.GetApp().ExitMainLoop()` after controller shutdown.
   - Ref: [src/apps/shared/tool_app_shell.py](/workspace/nvda-remote-client/src/apps/shared/tool_app_shell.py:30)

2. **Double shutdown wiring between shell and `OnExit()`**
   - Fixed. Both `EchoApp.OnExit()` and `NvdaRemoteApp.OnExit()` no longer call controller shutdown directly.
   - Refs: [src/ui/echo/app.py](/workspace/nvda-remote-client/src/ui/echo/app.py:21), [src/ui/nvda_remote/app.py](/workspace/nvda-remote-client/src/ui/nvda_remote/app.py:21)

3. **`ModeManager.exit_active_mode()` ignored `exit_active()` failure**
   - Fixed. The manager now preserves the active mode and skips `mode.exit()` / idle notification when activation rollback fails.
   - Ref: [src/apps/shared/mode_manager.py](/workspace/nvda-remote-client/src/apps/shared/mode_manager.py:42)

4. **Hard-coded tray tooltip for all apps**
   - Fixed. `ToolTrayIcon` now accepts `app_name`, `ToolAppShell` passes it through, and `EchoApp` supplies `"Key Echo"`.
   - Refs: [src/apps/shared/tray_icon.py](/workspace/nvda-remote-client/src/apps/shared/tray_icon.py:5), [src/apps/shared/tool_app_shell.py](/workspace/nvda-remote-client/src/apps/shared/tool_app_shell.py:6), [src/ui/echo/app.py](/workspace/nvda-remote-client/src/ui/echo/app.py:15)

### Regression check

I did not find a new behavior regression introduced by this fix commit during static review:

- the shell now has a single shutdown authority
- app-level `OnExit()` handlers no longer duplicate resource teardown
- the mode manager now preserves state consistency on active-to-idle transition failure
- the shared tray icon is app-specific again at the UI level

### Test coverage check

The fix commit also improves targeted coverage for the corrected paths:

- `tests/unit/test_mode_manager.py` now exercises failed `exit_active()` behavior
- `tests/unit/test_tool_app_shell.py` and `tests/unit/test_app_wx.py` now provide `GetApp()` / `ExitMainLoop()` support for the shell shutdown path
- `tests/unit/test_nvda_remote_app_service.py` now matches the corrected state-preservation behavior when hotkey restart fails

## Residual Risk

No additional actionable issues were identified in the reviewed commit set.
