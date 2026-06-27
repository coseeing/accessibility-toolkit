# Review Fixes — Completion Report

## Review Source

`docs/superpowers/review_task0.md` — reviewed the 8 commits from Task 0 (`7ba9f85`..`f4d6838`).

## Findings Confirmed

### Finding 1 (High): Lost specific error contract in `start_navigation()`

**Confirmed.** The M1 refactor (`220a8d0`) removed pre-activation validation, collapsing two specific error types (`RuntimeError("No GraphML file selected")` and `FileNotFoundError`) into a single generic `RuntimeError("Failed to start navigation")`. This conflicts with M1's requirement to preserve error speech, exception types, and when validation occurs.

**Fix:** Restored `self._graph_selection.require_existing_graphml_path()` call in `start_navigation()` before `ModeManager.activate_mode()`. This ensures:
- No file selected → `RuntimeError("No GraphML file selected")`
- File deleted after selection → `FileNotFoundError(...)` with path
- Activation fails → `RuntimeError("Failed to start navigation")`

### Finding 2 (Medium): Private `_notify_status` access from mode

**Confirmed.** `Access8GraphNavigationMode.enter()` accessed `self._navigation._notify_status(...)` — a private session field typed `Callable[[GraphNavigationChanged], None]` but called with `ErrorRaised`. This violated M1's rule that the mode depend only on stable public interfaces.

**Fix:**
- Added `report_error(message: str) -> None` public method to `Access8GraphNavigationSession`
- Broadened `notify_status` callback type to `Callable[[object], None]` (matches actual runtime usage)
- Changed mode's `enter()` to call `self._navigation.report_error(str(error))` instead of private access

### Test Updates

Three tests updated to assert restored error contracts:
- `test_service_cannot_start_without_selected_graphml`: `match="No GraphML file selected"`
- `test_service_deleted_file_fails_before_activation`: `pytest.raises(FileNotFoundError, match="will_be_deleted")`
- `test_idle_hotkey_without_selected_graphml_reports_error_without_starting_capture`: expected error message restored to `"No GraphML file selected"`

## New Commit

| SHA | Subject |
|-----|---------|
| `f16979f` | fix: restore specific start error contract and remove private callback access |

## Verification

- **Targeted tests:** 50/50 passing (Access8Graph app service + use cases + input)
- **Full suite:** 603/603 passing, zero regressions
