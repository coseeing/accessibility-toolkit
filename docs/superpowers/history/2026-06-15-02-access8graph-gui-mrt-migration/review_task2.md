# Access8Graph GUI MRT Migration Review - Task 2

Review date: 2026-06-17

## Review Scope

Reviewed source document:

- `docs/superpowers/finish_task2.md`

Reviewed previous review baseline:

- `docs/superpowers/review_task1.md`

Reviewed design and plan references:

- `docs/superpowers/specs/2026-06-15-access8graph-gui-mrt-migration-design.md`
- `docs/superpowers/plans/2026-06-15-access8graph-gui-mrt-migration-implementation.md`

Reviewed commits listed in `finish_task2.md`, ordered oldest to newest:

1. `d4a0384 fix: harden access8graph hotkey startup handling`
2. `69d919c docs: record access8graph task2 finish`

Local history contains a later unlisted documentation commit (`8076257 docs: finalize access8graph task2 commit list`). Per review instruction, that commit was not reviewed as a commit-order unit.

## Findings

### Low: hotkey error suppression is coupled to the exact generic error string

References:

- `src/apps/access8graph/service.py:126`
- `src/apps/access8graph/service.py:133`
- `src/apps/access8graph/service.py:238`
- `src/apps/access8graph/service.py:242`

The task2 fix works for the reviewed malformed-GraphML case: `_start_navigation_from_hotkey()` now suppresses the second generic `Failed to start navigation` status and preserves the parse-specific message. However, the suppression rule is implemented as a string comparison on `str(error) == "Failed to start navigation"`.

That leaves the hotkey path behavior tied to presentation text instead of structured control flow. If the generic error text changes, is localized, or another `activate_mode(False)` path is introduced later, the hotkey path can regress in one of two directions:

1. duplicate generic error becomes visible again because the string no longer matches; or
2. the only visible error is dropped if a different path starts raising the same generic text without first emitting a specific status.

I did not reproduce a current user-facing failure from this in the existing code. The current code passes the malformed-GraphML regression and focused suite. This is a low-severity maintainability risk, not a confirmed runtime regression.

Recommended follow-up:

- Replace the string check with structured signaling.
- Examples:
  - make `start_navigation()` preserve and re-raise the underlying startup exception instead of always converting `activate_mode(False)` to `RuntimeError("Failed to start navigation")`; or
  - return richer startup status from the mode/activation path so the hotkey wrapper can distinguish “specific error already reported” from “generic failure with no prior status”.

## Resolved Item From Task 1

### Medium: malformed GraphML hotkey startup overwrote the specific parser error: resolved

The reviewed fix addresses the behavior reported in `review_task1.md`. Hotkey startup with a selected malformed `.graphml` file now keeps the parse-specific error and does not append the second generic `Failed to start navigation` status. Safety behavior also remains correct: navigation stays stopped, input capture stays inactive, and hotkey capture stays active.

## Commit-Order Review Notes

### `d4a0384 fix: harden access8graph hotkey startup handling`

This commit fixes the task1 review finding in behavior. The new regression test for malformed GraphML hotkey startup matches the reported scenario and passes in the current tree. I did not find a new functional regression from this change in the reviewed Access8Graph suite.

The remaining issue is the low-severity implementation brittleness described above: the suppression decision depends on the exact generic error string.

### `69d919c docs: record access8graph task2 finish`

Documentation-only. The finish document accurately describes the bug that was fixed, the TDD sequence, and the focused verification evidence for this task.

## Verification Performed

Command run:

```bash
pytest tests/unit/test_access8graph_app_service.py::test_idle_hotkey_with_malformed_graphml_keeps_specific_error_message -v
```

Result:

```text
1 passed
```

Command run:

```bash
pytest tests/unit/test_access8graph_app_service.py tests/unit/test_access8graph_flow.py -v
```

Result:

```text
19 passed
```

Command run:

```bash
pytest tests/unit/test_access8graph_graphml.py tests/unit/test_access8graph_input.py tests/unit/test_access8graph_output.py tests/unit/test_access8graph_flow.py tests/unit/test_access8graph_app_service.py tests/unit/test_access8graph_ui.py tests/integration/test_access8graph_mrt_flow.py -v
```

Result:

```text
56 passed
```

## Review Conclusion

The task2 fix is complete in the behavior that `review_task1.md` asked for. I did not find a new functional regression in the current Access8Graph runtime path or focused test suite.

One low-severity issue remains: the hotkey wrapper’s generic-error suppression is implemented via exact string matching, which is brittle against later refactors or message changes. The current behavior is correct, but the control flow should eventually be made explicit instead of text-driven.
