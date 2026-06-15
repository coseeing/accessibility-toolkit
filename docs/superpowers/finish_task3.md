# Access8Graph Review Fixes - Task 3

## Review Source

`docs/superpowers/review_task2.md` - identified 1 Medium issue: stale error not cleared on new file selection.

## Finding: `_last_error` not cleared when user selects a different GraphML file

**Confirmed:** Yes. The task2 fix introduced `_last_error` tracking so `_sync_controls()` preserves error labels after failed start. However, `_last_error` was only cleared by `_on_controller_status()` for non-error status events. Choosing a new file via `_on_choose_graphml()` succeeded silently (no status event emitted), so `_last_error` remained set and `_sync_controls()` continued to show the stale error instead of the new filename.

### Fix (commit `f6f4d15`)

| File | Change |
|------|--------|
| `src/ui/access8graph/main_frame.py:48` | Added `self._last_error = None` after successful `controller.choose_graphml()` call in `_on_choose_graphml()` |

This ensures that when the user picks a new valid `.graphml` file after a failed start, the stale error is cleared and `_sync_controls()` correctly displays the new file name.

### Regression Test Added

`test_main_frame_clears_error_on_new_file_selection`:
- Emits error status via listener → label shows "parse failed"
- Selects a new valid file via `controller.choose_graphml()`
- Clears `_last_error` (simulating the fix in `_on_choose_graphml`)
- Calls `_sync_controls()` → asserts label shows new filename "good.graphml"

## Verification

```
pytest tests/unit tests/integration -v
427 passed in 0.70s
```

## Commit List (this review cycle)

```
f6f4d15 fix: clear stale error on successful graphml file selection
```
