# Access8Graph GUI MRT Migration - Task 2 Finish

## Review Suggestion Checked

Reviewed `docs/superpowers/review_task1.md` against the current code and reproduced the reported issue before changing production code.

- The Medium finding was confirmed: hotkey startup with a selected malformed `.graphml` file delivered the specific parse error and then a second generic `Failed to start navigation` error.
- Safety behavior was already correct before this task: navigation stayed stopped, input capture stayed inactive, and hotkey capture stayed active.

## Changes Made

- Added a regression test for malformed-GraphML hotkey startup:
  - `test_idle_hotkey_with_malformed_graphml_keeps_specific_error_message`
- Updated `Access8GraphAppService._start_navigation_from_hotkey()` so the hotkey path does not overwrite a more specific startup error with the generic `Failed to start navigation` status.

## TDD Evidence

Red check before implementation:

```bash
pytest tests/unit/test_access8graph_app_service.py::test_idle_hotkey_with_malformed_graphml_keeps_specific_error_message -v
# failed because delivered statuses included:
# - Failed to parse GraphML file: syntax error: line 1, column 0
# - Failed to start navigation
```

Green checks after implementation:

```bash
pytest tests/unit/test_access8graph_app_service.py::test_idle_hotkey_with_malformed_graphml_keeps_specific_error_message -v
# 1 passed

pytest tests/unit/test_access8graph_app_service.py tests/unit/test_access8graph_flow.py -v
# 19 passed

pytest tests/unit/test_access8graph_graphml.py tests/unit/test_access8graph_input.py tests/unit/test_access8graph_output.py tests/unit/test_access8graph_flow.py tests/unit/test_access8graph_app_service.py tests/unit/test_access8graph_ui.py tests/integration/test_access8graph_mrt_flow.py -v
# 56 passed
```

## Result

The `review_task1.md` finding was valid and is now addressed. Hotkey startup with malformed GraphML keeps the parse-specific error message instead of replacing it with a generic failure, while preserving the safe inactive-capture behavior introduced in the previous task.

## Commit List

New commits from this task:

```text
d4a0384 fix: harden access8graph hotkey startup handling
<pending> docs: record access8graph task2 finish
```
