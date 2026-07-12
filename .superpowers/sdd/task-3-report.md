# Task 3 Report: Unified Prefix Buffering and Fallback Replay

## Status

Implemented in the shared `mode-key-router` worktree.

## Changes

- Added `_BufferedInput` and `_DeferredChord` state records.
- Indexed unique binding chords for deterministic prefix detection.
- Unified general-key and modifier handling through prefix buffering.
- Deferred shorter exact key-down bindings while longer registered chords remain possible.
- Resolved deferred chords on release and suppressed obsolete shorter handlers.
- Replayed original `KeyEventInput` objects, including `CapturedKeyEvent` context, in arrival order when a prefix fails.
- Preserved long-press scheduling/cancellation and prevented repeat key-downs from extending or retriggering buffered chords.
- Added coverage for shorter/longer chord precedence, general-key replay, modifier replay, and no-fallback discard behavior.
- Updated the prior unformed-chord expectations to reflect buffered-prefix semantics.

## Test-first evidence

Initial required-suite run after adding the prefix tests was RED:

```text
4 failed, 16 passed in 0.12s
```

The failures showed immediate dispatch of shorter bindings, immediate modifier fallback, and missing general-key prefix buffering.

## Final verification

Command:

```bash
pytest tests/unit/test_key_router.py -q
```

Output:

```text
....................                                                     [100%]
20 passed in 0.07s
```

`git diff --check` also completed successfully.

## Commit

`feat: buffer multi-key chord prefixes`

## Blocking review fixes

- Suppressed repeated modifier key-down events using the same pressed-state guard as general keys.
- Replayed the breaking input through its original `KeyEventInput` wrapper, preserving `CapturedKeyEvent.native_context`.
- Cancelled shorter pending long-press candidates when a longer exact chord is recognized.
- Added focused regressions for all three findings.

## Review-fix verification

Command:

```bash
pytest tests/unit/test_key_router.py -q
```

Output:

```text
.......................                                                  [100%]
23 passed in 0.08s
```
