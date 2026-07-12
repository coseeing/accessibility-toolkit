# Task 4 final-fix report

## Finding

Pending long-press timers could survive a new pressed state containing an extra
general or modifier key, because cancellation only ran for states with an exact
long-press or key-down binding. A delayed callback also did not verify that the
current pressed state still exactly matched the scheduled chord.

## Fix

- Cancel all pending long presses when the new state is neither an exact
  candidate chord nor a valid prefix.
- Require the callback's pending entry and the current pressed state to match
  the scheduled chord before invoking the handler.
- Added regressions for A+B followed by C and callback state mismatch.

## Verification

Command:

```text
pytest tests/unit/test_key_router.py tests/unit/test_mode_manager.py -q
```

Result: `42 passed`.

## Concerns

No known concerns. Existing unrelated untracked review artifacts were preserved
and not included in the commit.
