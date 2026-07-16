# Task 1 Report: Default delayed scheduler

## Status

Completed and committed as `73d8aec` (`feat: add default long press scheduler`).

## Files changed

- `src/accessibility_toolkit/input/router.py`
  - Added the private `_ThreadingDelayedScheduler` adapter, which starts daemon
    `threading.Timer` instances.
  - Uses that adapter when no `DelayedScheduler` is injected.
  - Added one shared `threading.RLock` around `handle()`, `reset()`, and timer
    callback state handling, preserving same-thread `reset()` re-entry from a
    long-press handler.
- `tests/unit/test_key_router.py`
  - Added default-scheduler timer-factory coverage without sleeping.
  - Added injected-scheduler coverage that fails if `threading.Timer` is used.
  - Added coverage for a long-press handler calling `router.reset()` and
    clearing pending state.

## Test execution

### RED

`pytest tests/unit/test_key_router.py -q`

Result before implementation: `2 failed, 7 passed`. The new timer-factory
tests failed because the router did not yet import or expose `threading` for
the default scheduling seam.

### GREEN / final verification

`pytest tests/unit/test_key_router.py -q`

Result: `9 passed in 0.02s` (also rerun immediately before the commit with the
same result).

`git diff --check`

Result: no whitespace errors.

## Self-review

Verified that the default scheduler sets `daemon = True`, starts the timer, and
returns the scheduled call; an injected scheduler is preferred; and callback
state claim/mutation plus long-press handler invocation occur under the shared
reentrant lock. Callback exceptions remain uncaught.

## Concerns

None. The pre-existing untracked planning/specification files in the shared
worktree were left untouched and were not included in the commit.

## Fix: Preserve falsey injected schedulers

### Status

Fixed and committed.

### Files changed

- `src/accessibility_toolkit/input/router.py`
  - Uses an explicit `None` check so injected schedulers are preserved even
    when their truth value is false.
- `tests/unit/test_key_router.py`
  - Added focused coverage for a falsey injected scheduler.

### Test execution

`pytest tests/unit/test_key_router.py -q`

Result: `10 passed in 0.03s`

`git diff --check`

Result: no whitespace errors.

### Concerns

None.
