# Access8Graph Review Fixes - Task 4

## Review Source

`docs/superpowers/review_task3.md` - identified 1 Low issue: regression test bypasses production handler.

## Finding: Regression test does not exercise `_on_choose_graphml()`

**Confirmed:** Yes. `test_main_frame_clears_error_on_new_file_selection` manually set `frame._last_error = None` instead of calling `_on_choose_graphml()`. The test would pass even if the production fix (`self._last_error = None` at `main_frame.py:48`) were removed.

### Fix (commit `4c9631a`)

Rewrote the test to call `frame._on_choose_graphml(None)` directly:
- Installs fake wx with `FileDialog.GetPath` overridden to return a `tmp_path` file
- Emits error status → verifies label shows "parse failed"
- Calls `_on_choose_graphml(None)` → verifies the handler clears `_last_error` and label shows the new filename
- No manual `_last_error` assignment

This ensures the test actually fails if the `self._last_error = None` line is removed from the production code.

## Resolved Items From Task 3

| Finding | Status |
|---------|--------|
| Stale error after new file selection | Resolved in task3 (commit `f6f4d15`) |
| Test doesn't exercise production handler | **Fixed** (commit `4c9631a`) |

## Verification

```
pytest tests/unit tests/integration -v
427 passed in 0.67s
```

## Commit List (this review cycle)

```
4c9631a test: drive _on_choose_graphml in stale-error regression test
```
