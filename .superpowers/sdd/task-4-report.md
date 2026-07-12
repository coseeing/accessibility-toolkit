# Task 4 Report

## Files changed

- `src/accessibility_toolkit/input/router.py`
  - Added owned chord records covering all physical members and one-shot key-up dispatch.
  - Generalized pending long-press state from a single usage to a complete chord.
  - Added cancellation for member release, modifier loss, extra keys, reset, and mode exit reset.
  - Long-press completion now uses the key that completes the chord and establishes ownership.
- `tests/unit/test_key_router.py`
  - Added ownership, key-up-only, unhandled-down, multi-key long-press, and cancellation coverage.
- `tests/unit/test_mode_manager.py`
  - Added mode-exit pending long-press cancellation coverage.

## Full test output

```text
.......................................                                  [100%]
39 passed in 0.12s
```

Command:

```text
pytest tests/unit/test_key_router.py tests/unit/test_mode_manager.py -q
```

Additional verification: `git diff --check` passed.
