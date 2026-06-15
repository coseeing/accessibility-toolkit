# Access8Graph Review Fixes Review - Task 3

Review date: 2026-06-15

## Review Scope

Reviewed source document:

- `docs/superpowers/finish_task3.md`

Reviewed previous review baseline:

- `docs/superpowers/review_task2.md`

Reviewed commit, ordered from oldest to newest as requested:

1. `f6f4d15 fix: clear stale error on successful graphml file selection`

Only commits listed in `finish_task3.md` were reviewed. The later documentation commit at current `HEAD` was not included in code review scope.

## Findings

### Low: regression test does not exercise the actual file-selection handler

References:

- `tests/unit/test_access8graph_ui.py:247`
- `tests/unit/test_access8graph_ui.py:249`
- `tests/unit/test_access8graph_ui.py:250`
- `src/ui/access8graph/main_frame.py:47`
- `src/ui/access8graph/main_frame.py:48`

The implementation fix is in `_on_choose_graphml()`: after a successful `controller.choose_graphml(dialog.GetPath())`, the frame clears `self._last_error`.

The added regression test `test_main_frame_clears_error_on_new_file_selection` verifies the desired final state, but it does not call `_on_choose_graphml()`. Instead, it calls `controller.choose_graphml(str(new_path))` directly and then manually sets `frame._last_error = None`. That means this test would still pass if the production fix at `main_frame.py:48` were removed.

This is not a product behavior blocker because manual verification through `_on_choose_graphml()` confirms the current implementation works. It is a test coverage gap that weakens future regression protection.

Recommended fix:

- Update the test to drive the UI path that owns the behavior, ideally by configuring the fake `wx.FileDialog.GetPath()` result and calling `frame._on_choose_graphml(None)`.
- Assert that after `_on_choose_graphml(None)`, the label shows the newly selected file and `_last_error` no longer blocks `_sync_controls()`.

## Resolved Items From Task 2

### Stale error after successful new file selection: resolved

The task2 finding is fixed in the current implementation. `_on_choose_graphml()` now clears `_last_error` after a successful `controller.choose_graphml(...)`, so the following `_sync_controls()` call can update the status label to the selected filename.

Manual verification through the actual handler confirmed the behavior:

```text
after error: parse failed
after choose: map.graphml
selected: /tmp/map.graphml
```

This does not appear to introduce new keyboard-capture or service lifecycle risks because the change is limited to GUI status state.

## Commit-Order Review Notes

### `f6f4d15 fix: clear stale error on successful graphml file selection`

The commit is small and correctly targeted. The production change addresses the stale `_last_error` state introduced in task2. The only issue found is that the new regression test bypasses the production method it intends to protect.

## Verification Performed

Commands run:

```text
pytest tests/unit/test_access8graph_*.py tests/integration/test_access8graph_mrt_flow.py -v
pytest tests/unit tests/integration -v
PYTHONPATH=src:. python3 <manual _on_choose_graphml stale-error verification script>
```

Results:

- Access8Graph focused tests: `49 passed`
- Full suite: `427 passed`
- Manual UI handler verification confirmed stale error is cleared after successful file selection.

## Review Conclusion

Task 3 completes the functional fix for the task2 finding. No blocking product issues were found in this commit.

Before closing the loop, improve the regression test so it calls `_on_choose_graphml()` instead of manually mutating `_last_error`; otherwise the test suite will not catch a future removal of the actual fix.
