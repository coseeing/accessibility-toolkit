# Task 0 Code Review

## Review Result

**Changes requested.** The implementation is structurally close to the approved
design and all tests pass, but Milestone 1 introduces one user-visible behavior
regression and leaves one private boundary dependency that violates the spec's
definition of done.

## Findings

### High: Access8Graph start failures lose their specific error contract

**Introduced by:** `220a8d0` (`refactor: move access8graph flow lifecycle out of app service`)

**Locations:**

- `src/apps/access8graph/service.py:37-45`
- `src/apps/access8graph/service.py:126-128`
- `src/apps/access8graph/use_cases/navigation.py:65-70`
- `tests/unit/test_access8graph_app_service.py` changes in `220a8d0`

Before this commit, `Access8GraphAppService.start_navigation()` validated the
selection before activating the mode:

- no selected file raised `RuntimeError("No GraphML file selected")`
- a selected file deleted afterward raised `FileNotFoundError` with its path

The refactor changed both paths to `RuntimeError("Failed to start navigation")`.
For a missing selection, `can_enter()` now returns `False`, so the specific
reason is never raised. For a deleted file, mode activation starts first,
`enter()` catches and reports the `FileNotFoundError`, returns `False`, and the
public method then replaces it with the generic `RuntimeError`.

This conflicts with M1's explicit requirements to preserve error speech,
exception types, and when validation occurs. It also changes activation timing:
input activation can briefly start and roll back before a deleted file is
reported.

The tests did not catch the regression because the commit changed their expected
messages and exception types to the new generic behavior. Restore validation
through a public navigation use-case method before mode activation, or propagate
the original start exception without replacing it. Restore assertions for the
specific no-selection and deleted-file cases, including that capture activation
has not begun when validation fails.

### Medium: Navigation mode still depends on a private session callback

**Introduced by:** `220a8d0` (`refactor: move access8graph flow lifecycle out of app service`)

**Locations:**

- `src/apps/access8graph/service.py:40-45`
- `src/apps/access8graph/use_cases/navigation.py:39-51`

`Access8GraphNavigationMode.enter()` directly calls
`self._navigation._notify_status(...)`. This replaces one private coupling with
another and does not satisfy the M1 rule that the mode depend only on stable
public interfaces. It also bypasses the declared callback contract:
`Access8GraphNavigationSession` types the callback as accepting only
`GraphNavigationChanged`, while the mode sends `ErrorRaised`.

Move failure reporting behind a public operation or return/raise a typed start
result for the app service to report. The mode should not access session fields
whose names begin with `_`.

## Commit-by-Commit Review

1. `7ba9f85` adds focused graph-selection, flow-factory, and navigation-session
   objects with useful unit coverage. No standalone defect found.
2. `220a8d0` rewires the app service successfully, but introduces both findings
   above. Its tests encode the changed error behavior instead of preserving the
   approved contract.
3. `e267ff7` extracts translation/dispatch without changing the existing
   handled, unhandled, and no-active-flow semantics. No additional finding.
4. `41f67cf` introduces the shared facade and retains the compatibility
   controller aliases. Callback behavior remains equivalent. No finding.
5. `fa01c4b` injects a separate speech controller through all app shells while
   retaining the intended fallback. No finding.
6. `2c9837d` removes app-service pass-through APIs and preserves engine-change
   persistence plus typed status notification in runtime wiring. No finding.
7. `1d571a7` moves `ClipboardService` without changing its public export. No
   finding.
8. `f4d6838` removes the unused output manager and rewrites tests around the
   surviving direct collaborations. No active production behavior was lost.

## Verification

- Reviewed only the eight commits listed in
  `docs/superpowers/finish_task0.md`, ordered by commit time from `7ba9f85` to
  `f4d6838`.
- Compared the changes against the approved design spec and implementation
  plan.
- Focused suites: `181 passed in 1.22s`.
- Full suite: `603 passed in 2.74s`.
- `git diff 7ba9f85^..f4d6838 --check`: no whitespace errors.

The passing suite confirms broad regression coverage, but the two M1 issues
above require correction before this task should be accepted as complete.
