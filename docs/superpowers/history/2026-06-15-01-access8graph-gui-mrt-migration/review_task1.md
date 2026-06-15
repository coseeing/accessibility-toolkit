# Access8Graph Review Fixes Review - Task 1

Review date: 2026-06-15

## Review Scope

Reviewed source document:

- `docs/superpowers/finish_task1.md`

Reviewed previous review baseline:

- `docs/superpowers/review_task0.md`

Reviewed commit, ordered from oldest to newest as requested:

1. `1bcd13d fix: harden graph loading validation, activation rollback and UI error persistence`

Only commits listed in `finish_task1.md` were reviewed. The later documentation commit at current `HEAD` was not included in code review scope.

## Findings

### Medium: Start button failure path still overwrites controller error status with selected file name

References:

- `src/ui/access8graph/main_frame.py:57`
- `src/ui/access8graph/main_frame.py:60`
- `src/ui/access8graph/main_frame.py:61`
- `src/ui/access8graph/main_frame.py:87`

The task 1 fix made `_on_controller_status()` return early after setting an error label, which fixes the direct status-listener path. However, the actual button path still calls `_sync_controls()` unconditionally after catching `controller.start_navigation()` exceptions.

For malformed GraphML, `Access8GraphNavigationMode.enter()` now notifies the specific parse error through the status listener. The frame briefly sets that error text, but `_on_toggle_navigation()` then catches `RuntimeError("Failed to start navigation")`, shows a message box, and calls `_sync_controls()`. Since navigation is not running and a file is still selected, `_sync_controls()` changes the label back to the selected file name.

Manual reproduction performed during review:

```text
controller.start_navigation() sends {"kind": "error", "message": "parse failed"}
controller.start_navigation() raises RuntimeError("Failed to start navigation")
frame._on_toggle_navigation(None)

Final status label: bad.graphml
Message box: Failed to start navigation
```

This means the previous task0 Medium finding is only partially fixed. The status-listener unit test added in task1 covers direct callback behavior, but does not cover the real `_on_toggle_navigation()` failure path.

Recommended fix:

- In `_on_toggle_navigation()`, return immediately after showing the error, or preserve an explicit error state so `_sync_controls()` does not overwrite it.
- Prefer surfacing the specific controller error when available, not only the generic `Failed to start navigation`.
- Add a UI unit test where `start_navigation()` emits an error status and raises, then assert the final label remains the error message after `_on_toggle_navigation()` returns.

## Resolved Items From Task 0

### Critical GraphML activation lifecycle issue: resolved

The task1 changes correctly stop malformed GraphML from remaining in active navigation:

- `Graph.load()` now raises `ValueError` on XML parse errors instead of swallowing them.
- `Access8GraphNavigationMode.enter()` returns `False` on flow startup failure.
- `ModeManager.activate_mode()` therefore rolls back through `InputActivationUseCase.exit_active()`.
- `_start_flow()` no longer sets `_navigation_running = True` before graph/model construction.

The added regression test `test_service_malformed_graphml_does_not_leave_input_capture_running` verifies that malformed XML leaves navigation stopped, input capture stopped, and hotkey capture restored.

### Missing-file validation issue: resolved

`choose_graphml()` now checks `.suffix.lower()` and `Path.is_file()`. `start_navigation()` also revalidates existence before activation, covering deleted-after-selection behavior.

The added tests cover missing file, uppercase `.GRAPHML`, and deleted-after-selection behavior.

### Direct status-listener overwrite issue: partially resolved

Direct controller status callbacks are fixed by returning early in `_on_controller_status()`. The added unit test covers this path. The remaining problem is the button-start failure path described in the finding above.

## Commit-Order Review Notes

### `1bcd13d fix: harden graph loading validation, activation rollback and UI error persistence`

This commit addresses the main service lifecycle risks from task0. The GraphML parser no longer silently creates empty graphs on malformed XML, and navigation activation now rolls back when flow startup fails. File validation is also materially better and now happens both at selection time and before start.

The new issue is localized to UI status synchronization: the direct callback was fixed, but `_on_toggle_navigation()` still overwrites errors after failed starts. This does not reintroduce the keyboard-capture safety bug, but it does leave the user-facing error state inconsistent with the spec.

## Verification Performed

Commands run:

```text
pytest tests/unit/test_access8graph_*.py tests/integration/test_access8graph_mrt_flow.py -v
pytest tests/unit tests/integration -v
PYTHONPATH=src:. python3 <manual UI failure-path reproduction script>
```

Results:

- Access8Graph focused tests: `47 passed`
- Full suite: `425 passed`
- Manual UI reproduction confirmed final status label becomes `bad.graphml` after a failed start path that emitted `parse failed`.

## Review Conclusion

The critical and high-severity task0 service lifecycle findings are fixed. The code no longer appears to leave keyboard capture active on malformed or deleted graph files in the covered paths.

One medium-severity UI issue remains: failed Start Navigation actions can still overwrite the specific error label with the selected filename. Fix this before considering task1 fully complete, and add a regression test around `_on_toggle_navigation()` rather than only direct status listener invocation.
