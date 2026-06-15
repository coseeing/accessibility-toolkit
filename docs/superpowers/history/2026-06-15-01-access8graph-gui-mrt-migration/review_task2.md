# Access8Graph Review Fixes Review - Task 2

Review date: 2026-06-15

## Review Scope

Reviewed source document:

- `docs/superpowers/finish_task2.md`

Reviewed previous review baseline:

- `docs/superpowers/review_task1.md`

Reviewed commit, ordered from oldest to newest as requested:

1. `e939d95 fix: preserve error label through _sync_controls in button failure path`

Only commits listed in `finish_task2.md` were reviewed. The later documentation commit at current `HEAD` was not included in code review scope.

## Findings

### Medium: error state is not cleared when the user selects a different GraphML file

References:

- `src/ui/access8graph/main_frame.py:35`
- `src/ui/access8graph/main_frame.py:47`
- `src/ui/access8graph/main_frame.py:50`
- `src/ui/access8graph/main_frame.py:81`
- `src/ui/access8graph/main_frame.py:95`

Task 2 introduced `_last_error` so `_sync_controls()` can preserve status-listener errors after a failed Start Navigation action. That fixes the task1 finding, but `_last_error` is only cleared in `_on_controller_status()` for non-error statuses. Choosing a new file through `_on_choose_graphml()` does not clear `_last_error`, and `choose_graphml()` does not emit a non-error status.

As a result, after a failed start, the user can select a new valid `.graphml` file and `_sync_controls()` will still return early because `_last_error` remains set. The label continues to show the old error instead of the newly selected file name, conflicting with the expected main panel state.

Manual reproduction performed during review:

```text
after error: parse failed
after new selection sync: parse failed
```

Expected behavior after selecting `/tmp/new.graphml` is that the label updates to `new.graphml` and the stale error is cleared.

Recommended fix:

- Clear `_last_error` after a successful `controller.choose_graphml(dialog.GetPath())` before calling `_sync_controls()`.
- Consider also clearing `_last_error` before successful start/stop control sync, or centralize this as explicit UI state transitions rather than only relying on controller status events.
- Add a regression test: emit an error status, choose a different valid file, call the same UI path or `_sync_controls()`, then assert the label shows the new file name.

## Resolved Items From Task 1

### Button failure path preserving status-listener error: resolved

The direct task1 finding is fixed. `_last_error` is set in `_on_controller_status()` for error statuses, and `_sync_controls()` now updates button state while preserving the error label. The new regression test `test_main_frame_preserves_error_after_failed_start` covers the path where `start_navigation()` emits an error status and then raises.

Manual re-check from task1 no longer reproduces the old overwrite-to-filename issue for the failed start path covered by the test.

## Commit-Order Review Notes

### `e939d95 fix: preserve error label through _sync_controls in button failure path`

The implementation is appropriately scoped and fixes the reviewed failure path without touching keyboard capture or graph parsing logic. The change is localized to UI state preservation and adds a targeted regression test.

The new issue is that `_last_error` has no clear transition for successful file selection. This is a state-machine completeness problem in the GUI only; it does not appear to reintroduce the service lifecycle or keyboard-capture risks fixed in task1.

## Verification Performed

Commands run:

```text
pytest tests/unit/test_access8graph_*.py tests/integration/test_access8graph_mrt_flow.py -v
pytest tests/unit tests/integration -v
PYTHONPATH=src:. python3 <manual stale-error-after-new-selection reproduction script>
```

Results:

- Access8Graph focused tests: `48 passed`
- Full suite: `426 passed`
- Manual stale-error reproduction confirmed that after an error, selecting a new file and syncing controls leaves the old error label visible.

## Review Conclusion

Task 2 fixes the task1 reported bug for the failed Start Navigation path. However, the `_last_error` mechanism introduces a new medium-severity UI state bug: stale errors survive successful file selection.

Fix the error clearing transition on successful file choice and add a regression test for that path before considering this review cycle complete.
