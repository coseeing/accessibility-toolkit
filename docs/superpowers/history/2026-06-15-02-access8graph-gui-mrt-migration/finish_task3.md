# Access8Graph GUI MRT Migration - Task 3 Finish

## Review Suggestion Checked

Reviewed `docs/superpowers/review_task2.md` against the current code and verified the reported concern before changing production code.

- The Low finding was correct: hotkey startup error suppression depended on the exact `Failed to start navigation` error string.
- This was not a current user-facing regression in the reviewed malformed-GraphML path, but it was a real maintainability risk because behavior depended on presentation text instead of explicit startup state.

## Changes Made

- Replaced the hotkey-path generic-error suppression string check with explicit startup-state tracking:
  - `Access8GraphAppService` now tracks whether a hotkey-triggered startup attempt is in progress.
  - It also tracks whether that startup attempt already reported an error status.
  - The hotkey wrapper only suppresses the later generic exception when the same startup attempt already emitted a more specific error.
- Added a regression test for the generic-failure path without a preceding specific error:
  - `test_idle_hotkey_reports_generic_start_failure_when_no_specific_error_preceded`

## TDD Evidence

Red check before implementation:

```bash
pytest tests/unit/test_access8graph_app_service.py::test_idle_hotkey_reports_generic_start_failure_when_no_specific_error_preceded -v
# failed because delivered statuses were []
```

Green checks after implementation:

```bash
pytest tests/unit/test_access8graph_app_service.py::test_idle_hotkey_reports_generic_start_failure_when_no_specific_error_preceded -v
# 1 passed

pytest tests/unit/test_access8graph_app_service.py::test_idle_hotkey_with_malformed_graphml_keeps_specific_error_message -v
# 1 passed

pytest tests/unit/test_access8graph_app_service.py tests/unit/test_access8graph_flow.py -v
# 20 passed

pytest tests/unit/test_access8graph_graphml.py tests/unit/test_access8graph_input.py tests/unit/test_access8graph_output.py tests/unit/test_access8graph_flow.py tests/unit/test_access8graph_app_service.py tests/unit/test_access8graph_ui.py tests/integration/test_access8graph_mrt_flow.py -v
# 57 passed
```

## Result

The `review_task2.md` finding was valid and is now addressed. Hotkey startup error suppression no longer depends on an exact error string; instead it suppresses only the generic follow-up failure from the same startup attempt after a specific error was already reported.

## Commit List

New commits from this task:

```text
00e262b refactor: remove string-coupled access8graph hotkey errors
0aa59de docs: record access8graph task3 finish
```
