# Access8Graph Review Fixes - Task 2

## Review Source

`docs/superpowers/review_task1.md` - identified 1 Medium issue, confirmed 2 prior findings resolved.

## Finding: Start button failure path overwrites error label

**Confirmed:** Yes. The task1 fix made `_on_controller_status()` return early after setting an error label, but `_on_toggle_navigation()` line 61 still calls `_sync_controls()` unconditionally after catching `start_navigation()` exceptions. For malformed GraphML, the status listener emits a specific parse error ("parse failed"), but `_sync_controls()` overwrites it with the selected filename.

**Root cause:** `_sync_controls()` had no awareness of pending error state from the status listener. When called from `_on_toggle_navigation()` after a failed start, it would rewrite the status label to the file name or "No file selected".

### Fix (commit `e939d95`)

| File | Change |
|------|--------|
| `src/ui/access8graph/main_frame.py:10` | Added `self._last_error: str | None = None` attribute |
| `src/ui/access8graph/main_frame.py:80-81` | `_sync_controls()` returns early if `_last_error` is set, preserving the error label while still updating button state |
| `src/ui/access8graph/main_frame.py:89-93` | `_on_controller_status()` sets `_last_error` on error status, clears it on non-error status (so choosing a new file or successful start clears the error) |

### Regression Test Added

`test_main_frame_preserves_error_after_failed_start` - simulates the `_on_toggle_navigation()` failure path:
- `FakeController.start_error` set to "parse failed"
- Controller emits `{"kind": "error", "message": "parse failed"}` via status listener, then raises `RuntimeError`
- After `_on_toggle_navigation()` returns, `status_label` still reads "parse failed"

## Resolved Items From Task 1

| Finding | Status |
|---------|--------|
| Critical: GraphML activation lifecycle | Resolved in task1 (commit `1bcd13d`) |
| High: Missing-file validation | Resolved in task1 (commit `1bcd13d`) |
| Medium: UI error overwritten by `_sync_controls()` | **Now fully resolved** (both direct status listener path and button failure path) |

## Verification

```
pytest tests/unit tests/integration -v
426 passed in 0.72s
```

## Commit List (this review cycle)

```
e939d95 fix: preserve error label through _sync_controls in button failure path
```
