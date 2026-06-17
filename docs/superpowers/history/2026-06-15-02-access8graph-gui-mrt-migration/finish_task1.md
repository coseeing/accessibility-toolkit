# Access8Graph GUI MRT Migration - Task 1 Finish

## Review Suggestions Checked

Reviewed `docs/superpowers/review_task0.md` against the current code, design, and implementation plan.

- High finding confirmed: `_handle_idle_hotkey()` scheduled `start_navigation()` without a selected GraphML path, so the deferred callback could raise `RuntimeError("No GraphML file selected")` outside the UI button error path.
- Low finding confirmed: migrated `ModeState.enter()` appended `功能選單開啟` once inside the direction-run background branch and once unconditionally, while the original Access8Graph source only appended inside the branch. Keeping one unconditional append preserves startup mode-menu speech while removing the duplicate on return from direction run.

## Changes Made

- Added a guarded hotkey start path in `Access8GraphAppService`:
  - idle hotkey dispatches `_start_navigation_from_hotkey()`;
  - startup exceptions are caught and reported through `_notify_status_listener()`;
  - input capture remains inactive when no `.graphml` file is selected.
- Removed the duplicate branch append from `ModeState.enter()`, so returning from direction-run mode announces the function menu once.
- Added regression tests for both review findings.

## TDD Evidence

Red checks before implementation:

```bash
pytest tests/unit/test_access8graph_app_service.py::test_idle_hotkey_without_selected_graphml_reports_error_without_starting_capture -v
# failed with RuntimeError: No GraphML file selected

pytest tests/unit/test_access8graph_flow.py::test_flow_returning_from_direction_run_announces_mode_menu_once -v
# failed because 功能選單開啟 appeared twice
```

Green checks after implementation:

```bash
pytest tests/unit/test_access8graph_app_service.py::test_idle_hotkey_without_selected_graphml_reports_error_without_starting_capture -v
# 1 passed

pytest tests/unit/test_access8graph_flow.py::test_flow_returning_from_direction_run_announces_mode_menu_once -v
# 1 passed

pytest tests/unit/test_access8graph_app_service.py tests/unit/test_access8graph_flow.py -v
# 18 passed

pytest tests/unit/test_access8graph_graphml.py tests/unit/test_access8graph_input.py tests/unit/test_access8graph_output.py tests/unit/test_access8graph_flow.py tests/unit/test_access8graph_app_service.py tests/unit/test_access8graph_ui.py tests/integration/test_access8graph_mrt_flow.py -v
# 55 passed
```

## Result

Both review findings were valid and have been addressed. The focused Access8Graph test suite passes with the new regression coverage.
