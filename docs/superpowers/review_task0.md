# Access8Graph GUI MRT Migration Review - Task 0

Review date: 2026-06-17

## Review Scope

Reviewed source document:

- `docs/superpowers/finish_task0.md`

Reviewed design and plan:

- `docs/superpowers/specs/2026-06-15-access8graph-gui-mrt-migration-design.md`
- `docs/superpowers/plans/2026-06-15-access8graph-gui-mrt-migration-implementation.md`

Reviewed commits listed in `finish_task0.md`, ordered oldest to newest:

1. `4defbe9 docs: add access8graph gui mrt migration design`
2. `80bbab4 feat: migrate access8graph graphml core`
3. `6320c31 feat: add access8graph key translator`
4. `2822214 feat: add access8graph flow output adapter`
5. `960e8be feat: port access8graph mrt flow`
6. `4d6e6e9 test: cover access8graph mrt flow smoke path`
7. `608f78c feat: add access8graph app service`
8. `efad860 feat: add access8graph gui runtime`
9. `aedf89e docs: add access8graph migration completion summary`
10. `b452e13 docs: add access8graph review fix summary`
11. `4f62f1a docs: add access8graph review task2 fix summary`
12. `603c2e3 docs: add access8graph review task3 fix summary`
13. `733b227 docs: add access8graph review task4 fix summary`
14. `7ccb053 done: 2026-06-15-access8graph-gui-mrt-migration`
15. `874b53b feat: harden access8graph navigation error handling`

Only commits listed in `finish_task0.md` were reviewed as commit-order units. Local history contains additional unlisted fix commits between some of these documentation commits; those were not reviewed as separate commits, but the final working tree behavior was checked because it is what users will run.

## Findings

### High: idle hotkey can raise an unhandled start error before a GraphML file is selected

References:

- `src/apps/access8graph/main.py:54`
- `src/apps/access8graph/service.py:126`
- `src/apps/access8graph/service.py:233`
- `src/apps/access8graph/service.py:236`

`Access8GraphRuntime.build_runtime()` starts the app hotkey immediately. The hotkey handler `_handle_idle_hotkey()` only checks `is_navigation_running()` and then dispatches `self.start_navigation`. If the user presses the hotkey before selecting a `.graphml` file, `start_navigation()` raises `RuntimeError("No GraphML file selected")`.

In the wx runtime this is scheduled through `main_thread_dispatch` (`wx.CallAfter`), so the exception is not caught by the button handler and is not converted into a controlled UI error. This violates the design intent that the main panel disables Start until selection and that start failures report a concise error instead of leaking an exception through the UI event loop.

Recommended fix:

- Make `_handle_idle_hotkey()` check `get_selected_graphml_path()` before dispatching `start_navigation()`.
- Or dispatch a wrapper that catches `Exception`, calls `_notify_status_listener({"kind": "error", "message": str(error)})`, and leaves capture state unchanged.
- Add a regression test that calls `hotkey_capture.handler()` with no selected file and asserts no exception escapes, input capture remains inactive, and an error status is delivered or no-op behavior is intentional.

### Low: `ModeState.enter()` now announces the function menu twice when returning from a running direction state

References:

- `src/apps/access8graph/flow.py:204`
- `src/apps/access8graph/flow.py:206`
- `src/apps/access8graph/flow.py:209`
- `Access8Graph/addon/globalPlugins/Access8Graph/GraphML/mrtView.py:309`

The migrated `ModeState.enter()` appends `self.open_message` inside the `background_state`/`run` branch and then appends it again unconditionally. The original Access8Graph implementation only appended inside the branch. This creates a likely duplicate "功能選單開啟" announcement when returning to the mode menu while a direction run background state exists.

This is not a keyboard-capture safety issue, but it is a user-facing speech regression from the original flow and conflicts with the design goal of preserving existing MRT flow behavior.

Recommended fix:

- Decide whether initial mode entry should announce `功能選單開啟`. If yes, keep one unconditional append and remove the branch append.
- If preserving original behavior is more important, restore the original conditional-only behavior.
- Add a focused flow test for returning from a direction run to the mode menu and assert the announcement appears once.

## Commit-Order Review Notes

### `4defbe9 docs: add access8graph gui mrt migration design`

The design is coherent and gives enough behavioral constraints for review: NVDA-free GraphML/model code, explicit output adapters, keyboard-capture lifecycle, UI state, and error handling. No issue found in the design document itself.

### `80bbab4 feat: migrate access8graph graphml core`

The GraphML/MRT core is structurally isolated under `apps.access8graph.graphml` and current tests confirm it imports without NVDA modules. Previous review artifacts recorded parser/lifecycle issues; the final current tree no longer reproduces those focused failures in the covered tests.

Residual risk remains around deeper GraphML route-planning correctness because current tests are still fixture smoke tests rather than exhaustive behavioral parity checks.

### `6320c31 feat: add access8graph key translator`

The translator matches the planned first-stage key set and correctly ignores key-up events at the translator boundary. No issue found in this commit.

### `2822214 feat: add access8graph flow output adapter`

The output adapter maps speech items into `SpeechSequence` and inserts `BreakCommand(time=1)` between non-empty items, as specified. It also treats missing tone capability as no-op. No issue found in this commit.

### `960e8be feat: port access8graph mrt flow`

The flow port keeps the state-machine structure and removes NVDA runtime dependencies. The low-severity duplicate function-menu announcement appears in this area: current `ModeState.enter()` differs from the original `mrtView.py` behavior and can repeat the open message.

### `4d6e6e9 test: cover access8graph mrt flow smoke path`

The integration smoke test is useful for ensuring the fixture can start and accept basic menu navigation. It does not cover returning from active direction navigation to the mode menu, which is where the duplicate announcement risk would show.

### `608f78c feat: add access8graph app service`

The app service provides the expected selected-file state, lifecycle methods, keyboard pipeline entrypoint, and speech settings proxies. The final current tree includes later hardening for validation, dispatch exceptions, unsupported key suppression, and main-thread status dispatch.

The remaining high-severity issue is in the idle hotkey path: it bypasses the GUI's disabled Start button guard and can dispatch `start_navigation()` before a file is selected.

### `efad860 feat: add access8graph gui runtime`

The GUI runtime follows the shared tray shell pattern and starts the Access8Graph hotkey immediately. Starting the hotkey is consistent with a tray tool, but it makes the service hotkey guard mandatory. Since `_handle_idle_hotkey()` currently lacks that guard, this commit participates in the high-severity finding.

### `aedf89e docs: add access8graph migration completion summary`

Documentation-only. It captured an earlier completion state. No code issue introduced by this commit.

### `b452e13 docs: add access8graph review fix summary`

Documentation-only. The corresponding review/fix cycle is now archived under `docs/superpowers/history/2026-06-15-01-access8graph-gui-mrt-migration/`. No code issue introduced by this commit.

### `4f62f1a docs: add access8graph review task2 fix summary`

Documentation-only. No code issue introduced by this commit.

### `603c2e3 docs: add access8graph review task3 fix summary`

Documentation-only. No code issue introduced by this commit.

### `733b227 docs: add access8graph review task4 fix summary`

Documentation-only. The archived task4 review reports no remaining issue for the stale-error regression test. No code issue introduced by this commit.

### `7ccb053 done: 2026-06-15-access8graph-gui-mrt-migration`

This commit reorganizes the Access8Graph completion/review artifacts into history, adds the implementation plan and zh-TW design document, and updates `.gitignore`. No code issue introduced by this commit.

### `874b53b feat: harden access8graph navigation error handling`

This commit fixes important service behavior: unsupported active key events are suppressed, flow dispatch exceptions stop navigation and report status, and status callbacks are delivered through `main_thread_dispatch`. The new regression tests cover these paths.

The commit does not address idle-hotkey startup with no selected file, so the high-severity finding remains.

## Verification Performed

Command run:

```bash
pytest tests/unit/test_access8graph_app_service.py tests/unit/test_access8graph_graphml.py tests/unit/test_access8graph_input.py tests/unit/test_access8graph_output.py tests/unit/test_access8graph_flow.py tests/unit/test_access8graph_ui.py tests/integration/test_access8graph_mrt_flow.py -v
```

Result:

```text
53 passed
```

## Review Conclusion

The Access8Graph migration is structurally aligned with the approved spec and the focused test suite passes. The main remaining issue is the idle hotkey path: users can trigger navigation before selecting a file, causing an uncaught start error through the UI dispatcher. Fix that before treating the runtime as ready for real use.

The duplicate function-menu announcement should also be cleaned up or explicitly accepted with a test, because it diverges from the original Access8Graph flow behavior.
