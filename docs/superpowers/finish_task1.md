# Task 1 Completion Report: Transition Table Integrity

**Date:** 2026-06-27
**Branch:** `feat/access8graph-facade-speech-settings-refactor`
**Review:** `docs/superpowers/review_task0.md`
**Validation:** `pytest tests/unit tests/integration -q` — `793 passed`

## Review Verification

Both review findings were reproduced before implementation:

- Invalid rule source values leaked `AttributeError`, while invalid command and
  target values passed validation.
- An invalid initial-state type leaked `AttributeError`.
- Two identical guarded rules passed validation, leaving `rules` and `index`
  with inconsistent rule counts and causing runtime ambiguity when the guard
  matched.

These behaviors conflict with the design requirement that malformed extension
tables fail during assembly before commands are accepted.

## Result

- Validation now checks the initial state type before reachability analysis.
- Every rule source and target must be a `NavigationStateId`.
- Every rule command must be a `NavigationCommand`.
- Exact duplicate rules are rejected before the lookup index is built,
  including guarded duplicates.
- All malformed values consistently raise
  `TransitionTableValidationError`.
- Added focused negative tests for invalid source, target, command, initial
  state, and duplicate guarded rules.

## Added Implementation Commits

```text
fee60b9 fix: validate access8graph transition rule integrity
```

The separate commit containing this completion report is intentionally not
self-listed because a commit cannot contain its own final hash.

## Verification

```text
$ pytest tests/unit/test_access8graph_transition_table.py -q
23 passed in 0.06s

$ pytest tests/unit/test_access8graph_transition_engine.py \
    tests/unit/test_access8graph_navigation_model.py -q
16 passed in 0.07s

$ git diff --check
(no output)

$ python3 -m compileall -q src tests
(no output)

$ pytest tests/unit tests/integration -q
793 passed in 1.80s
```

The suite has one unrelated, hash-order-dependent integration failure in
`test_undirected_station_navigation_speaks_station_after_moving_right`. The
recorded full-suite run passed, but a later run failed; fixed
`PYTHONHASHSEED` probes passed for seeds 1 and 2 and failed for seeds 3 and 4.
The validator changes do not touch graph or navigator ordering.

Windows/macOS speech backends, wx UI, and keyboard hooks were not exercised on
physical platform environments.
