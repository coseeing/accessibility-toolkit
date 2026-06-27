# Task 1 Code Review

## Review Result

**Approved with one non-blocking type-safety suggestion.** Commit `f16979f`
correctly resolves both findings from `review_task0.md`. The original
Access8Graph error behavior is restored, mode activation no longer begins for
pre-validation failures, and the mode no longer accesses the navigation
session's private callback.

No new runtime regression was found.

## Finding

### Low: Status callback type is broader than the actual event contract

**Introduced by:** `f16979f`

**Location:** `src/apps/access8graph/use_cases/navigation.py:47`

The callback type was changed from
`Callable[[GraphNavigationChanged], None]` to `Callable[[object], None]` so it
can also receive `ErrorRaised`. This removes the original type mismatch, but
also permits any object and prevents static analysis from detecting unrelated
event types.

Use an explicit event union instead:

```python
Callable[[ErrorRaised | GraphNavigationChanged], None]
```

Alternatively, define a named Access8Graph status-event alias shared with the
app service. This is a maintainability improvement and does not block acceptance
of the behavioral fix.

## Previous Findings

### High: Specific start error contract

**Resolved.**

`Access8GraphAppService.start_navigation()` now calls
`require_existing_graphml_path()` before `ModeManager.activate_mode()`.
Consequently:

- no selection raises `RuntimeError("No GraphML file selected")`
- a selected file deleted afterward raises `FileNotFoundError` with its path
- neither pre-validation failure starts input capture
- genuine mode activation failures still use
  `RuntimeError("Failed to start navigation")`

The three affected tests now assert the restored error messages and exception
types rather than accepting the task0 regression.

### Medium: Private navigation callback access

**Resolved.**

`Access8GraphNavigationMode.enter()` now calls the public
`Access8GraphNavigationSession.report_error()` method. There is no remaining
mode access to `_notify_status`, so the M1 stable-interface requirement is met.

## Commit-by-Commit Review

The completion report lists one commit:

1. `f16979f` (`fix: restore specific start error contract and remove private
   callback access`) directly follows task0's final commit `f4d6838`. Its
   production changes resolve both requested corrections, and its test changes
   restore the original behavioral contract. No blocking defect or new runtime
   regression was found.

## Verification

- Reviewed only commit `f16979f`, as listed in
  `docs/superpowers/finish_task1.md`.
- Compared the fix against `review_task0.md`, the approved design spec, and the
  implementation plan.
- Focused Access8Graph tests: `50 passed in 0.16s`.
- Full suite: `603 passed in 1.17s`.
- `git diff f16979f^..f16979f --check`: no whitespace errors.

Task 1 is acceptable as complete. The callback union above may be tightened in
a later cleanup without changing runtime behavior.
