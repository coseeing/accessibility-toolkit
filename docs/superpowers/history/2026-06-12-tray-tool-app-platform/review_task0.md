# Review Task 0

Reviewed in commit order from oldest to newest, using:

- `docs/superpowers/finish_task0.md`
- `docs/superpowers/plans/2026-06-12-tray-tool-app-platform-implementation.md`
- `docs/superpowers/specs/2026-06-12-tray-tool-app-platform-design.md`

## Findings

1. **High:** The tray/menu-bar `Exit` action does not actually terminate the wx application. In `ToolAppShell`, the exit callback only destroys the tray icon and calls `controller.shutdown()`; it never closes the hidden frames, destroys the app shell windows, or exits the main loop. That means the primary shutdown path introduced by the tray-shell work can leave a background process alive with hidden frames still owning the wx app. This directly contradicts the spec requirement that full exit must happen through the icon menu. Affected commit: `b73917a` (introduced), still present after `9e8dbcb`.  
   Refs: [src/apps/shared/tool_app_shell.py](/workspace/nvda-remote-client/src/apps/shared/tool_app_shell.py:20), [src/apps/shared/tool_app_shell.py](/workspace/nvda-remote-client/src/apps/shared/tool_app_shell.py:26), [tests/unit/test_tool_app_shell.py](/workspace/nvda-remote-client/tests/unit/test_tool_app_shell.py:141)

2. **Medium:** If the app does exit through some other route, shutdown is wired twice: once from `ToolAppShell.shutdown()` and again from each wx app’s `OnExit()`. For both apps, `OnExit()` still calls `controller.shutdown()` directly after the shell has already used the same callback for the tray `Exit` action. Double-disconnecting transports and double-shutting down speech backends is risky, especially for native resources and external TTS integrations. Affected commit: `b73917a` (introduced), still present after `9e8dbcb`.  
   Refs: [src/apps/shared/tool_app_shell.py](/workspace/nvda-remote-client/src/apps/shared/tool_app_shell.py:26), [src/ui/echo/app.py](/workspace/nvda-remote-client/src/ui/echo/app.py:24), [src/ui/nvda_remote/app.py](/workspace/nvda-remote-client/src/ui/nvda_remote/app.py:24)

3. **Medium:** `ModeManager.exit_active_mode()` ignores whether `InputActivationUseCase.exit_active()` actually succeeded, but still runs `mode.exit()`, clears `active_mode_id`, and emits an `"idle"` status. If restarting `HotkeyCapture` fails during active-to-idle transition, the manager will report the mode as fully exited even though capture ownership may still be broken. That creates a silent state mismatch between UI state and actual input lifecycle. Affected commit: `579ed76` (introduced), consumed by `1607d6e` and `4c02c8d`.  
   Refs: [src/apps/shared/mode_manager.py](/workspace/nvda-remote-client/src/apps/shared/mode_manager.py:42), [src/application/input/activation.py](/workspace/nvda-remote-client/src/application/input/activation.py:37)

4. **Low:** The shared tray icon is hard-coded to the tooltip `"NVDA Remote"` for every app. After `key_echo` was migrated onto the shared shell, its resident icon still identifies itself as the NVDA Remote app. This is a user-visible regression and also shows that the promised app-metadata registration boundary has not actually been implemented in the shell. Affected commit: `b73917a` (introduced), still present after `9e8dbcb`.  
   Refs: [src/apps/shared/tray_icon.py](/workspace/nvda-remote-client/src/apps/shared/tray_icon.py:11)

## Commit-by-Commit Notes

- `6511122` `refactor: extract shared speech settings controller`
  - No findings. The extraction is straightforward and remains aligned with the spec.

- `72ff04f` `feat: add shared panel hide-on-close controller`
  - No findings. The close-to-hide behavior matches the documented direction.

- `aca588a` `feat: move speech settings into standalone frame`
  - No findings. The standalone frame aligns with the plan and keeps behavior localized.

- `b73917a` `feat: add shared tray app shell`
  - Findings 1, 2, and 4 originate here.

- `579ed76` `feat: add shared mode manager`
  - Finding 3 originates here.

- `1607d6e` `feat: migrate key echo to shared mode platform`
  - No new findings beyond the inherited `ModeManager` issue above.

- `4c02c8d` `feat: connect nvda remote to shared mode lifecycle`
  - No new findings beyond the inherited `ModeManager` and tray-shell issues above.

- `9e8dbcb` `refactor: complete tray tool app platform migration`
  - No additional runtime findings from the cleanup commit; the earlier issues remain unresolved.

## Residual Risk

- The current test suite covers tray construction and controller-callback wiring, but it does not assert that the tray `Exit` action actually ends the app process or leaves `wx` in a terminated state.
- There is also no negative-path coverage for `ModeManager` when `exit_active()` fails during capture restoration.
