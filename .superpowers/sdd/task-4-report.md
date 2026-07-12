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
# Task 4 Report: Long-Press Callback Ownership and Fired-State Cleanup

## Status

Implemented in the shared `mode-key-router` worktree.

## Changes

- Removed a fired pending long-press entry after its handler completes.
- Checked that the same pending entry still belongs to the router before creating chord ownership.
- Prevented a long-press handler that calls `router.reset()` from recreating ownership after reset.
- Added regressions for fired-state cleanup and reset-from-handler key-up behavior.

## Test-first evidence

The new regressions initially failed:

```text
2 failed, 27 deselected
```

The failures showed the fired pending entry remained in the router and reset was followed by recreated ownership that swallowed the key-up.

## Final verification

Command:

```bash
pytest tests/unit/test_key_router.py tests/unit/test_mode_manager.py -q
```

Output:

```text
40 passed in 0.07s
```

## Concerns

- The focused suite does not exercise platform-specific timer implementations.
