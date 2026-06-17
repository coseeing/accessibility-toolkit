# Access8Graph GUI MRT Migration Review - Task 1

Review date: 2026-06-17

## Review Scope

Reviewed source document:

- `docs/superpowers/finish_task1.md`

Reviewed previous review baseline:

- `docs/superpowers/review_task0.md`

Reviewed implementation state:

- `src/apps/access8graph/service.py`
- `src/apps/access8graph/flow.py`
- `tests/unit/test_access8graph_app_service.py`
- `tests/unit/test_access8graph_flow.py`

`docs/superpowers/finish_task1.md` does not list commit hashes, and the reviewed changes are currently present as uncommitted working-tree changes. Because no commits are listed in the finish document, there was no commit-by-commit sequence to review. The review below follows the change order described by the finish document and verifies the current diff.

## Findings

### Medium: hotkey startup on malformed GraphML can overwrite the specific parser error with a generic failure

References:

- `src/apps/access8graph/service.py:238`
- `src/apps/access8graph/service.py:240`
- `src/apps/access8graph/service.py:242`

The new `_start_navigation_from_hotkey()` wrapper correctly prevents exceptions from escaping the wx-dispatched hotkey callback. However, when a selected GraphML file is malformed, startup now emits two error statuses:

1. `Access8GraphNavigationMode.enter()` reports the specific parser error, such as `Failed to parse GraphML file: syntax error: line 1, column 0`.
2. `start_navigation()` then raises `RuntimeError("Failed to start navigation")`, and `_start_navigation_from_hotkey()` reports that generic message as a second status.

In the UI, the second generic status can become the final visible label, losing the actionable parse failure that the button path preserves through `_last_error`.

Manual check performed during review:

```text
[{'kind': 'error', 'message': 'Failed to parse GraphML file: syntax error: line 1, column 0'}, {'kind': 'error', 'message': 'Failed to start navigation'}]
running False input False hotkey True
```

This does not reintroduce the keyboard-capture safety problem: navigation remains stopped, input capture remains inactive, and hotkey capture remains active. The issue is user-facing error quality and consistency between button start and hotkey start.

Recommended fix:

- Have `_start_navigation_from_hotkey()` suppress the generic `Failed to start navigation` status if startup already emitted a specific error during the same attempt.
- Or make `start_navigation()` preserve and re-raise the original startup exception instead of converting all `activate_mode(False)` cases to `Failed to start navigation`.
- Add a regression test for hotkey startup with malformed GraphML that asserts the final delivered error remains the parse-specific message.

## Resolved Items From Task 0

### High: idle hotkey without selected GraphML leaks `RuntimeError`: resolved

The fix routes idle hotkey activation through `_start_navigation_from_hotkey()`, which catches startup exceptions and reports them through `_notify_status_listener()`. The regression test `test_idle_hotkey_without_selected_graphml_reports_error_without_starting_capture` covers the no-selection path and verifies that input capture remains inactive.

### Low: duplicate function-menu announcement on return from direction run: resolved

The extra conditional `self.open_message` append was removed from `ModeState.enter()`. The remaining unconditional append preserves startup mode-menu speech and the new regression test `test_flow_returning_from_direction_run_announces_mode_menu_once` verifies that returning from a direction run announces `功能選單開啟` once.

## Change-Order Review Notes

### Guarded hotkey start path in `Access8GraphAppService`

The direction is correct: deferred hotkey startup no longer lets `RuntimeError("No GraphML file selected")` escape outside the UI button error path. This materially improves robustness over the state reviewed in task0.

The new wrapper catches broad exceptions, which is appropriate for a UI-dispatched callback, but it should avoid overwriting a more specific startup error with `Failed to start navigation` when the lower layer already reported the real cause.

### `ModeState.enter()` duplicate announcement removal

The change is small and matches the stated intent: remove the duplicate branch append while keeping one mode-menu open announcement. The regression test exercises the return-from-direction-run path that triggered the review finding.

### Regression tests

The two new tests directly cover the two task0 findings. The hotkey no-selection test also checks dispatch ordering by manually draining the pending callbacks, which is important because both hotkey start and status delivery use `main_thread_dispatch`.

Missing coverage: malformed selected GraphML through the hotkey path, where the new wrapper emits a second generic error status after the specific parse error.

## Verification Performed

Commands run:

```bash
pytest tests/unit/test_access8graph_app_service.py::test_idle_hotkey_without_selected_graphml_reports_error_without_starting_capture tests/unit/test_access8graph_flow.py::test_flow_returning_from_direction_run_announces_mode_menu_once -v
```

Result:

```text
2 passed
```

Command run:

```bash
pytest tests/unit/test_access8graph_app_service.py tests/unit/test_access8graph_flow.py -v
```

Result:

```text
18 passed
```

Command run:

```bash
pytest tests/unit/test_access8graph_graphml.py tests/unit/test_access8graph_input.py tests/unit/test_access8graph_output.py tests/unit/test_access8graph_flow.py tests/unit/test_access8graph_app_service.py tests/unit/test_access8graph_ui.py tests/integration/test_access8graph_mrt_flow.py -v
```

Result:

```text
55 passed
```

Additional manual check:

- Simulated hotkey startup with a selected malformed `.graphml` file.
- Confirmed navigation stayed stopped and input capture stayed inactive.
- Confirmed two error statuses were delivered, with the generic `Failed to start navigation` after the specific parse error.

## Review Conclusion

The task1 fixes complete both findings from `review_task0.md` in the important safety sense: idle hotkey exceptions are contained, capture state stays safe, and the duplicate mode-menu announcement is removed.

One medium-severity user-facing issue remains from the hotkey wrapper: malformed GraphML startup can report a specific parse error and then overwrite it with a generic failure. Fix that error-reporting regression before closing the review loop.
