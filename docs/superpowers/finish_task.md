# Mode-Key Router — Completion Report

## Objective

Extend the mode-owned `KeyEventRouter` with deterministic multi-key chord
matching, unified prefix buffering, binding ownership, lifecycle-aware key-up
handling, and a default long-press scheduler, while preserving raw captured
events for fallback and NVDA Remote forwarding.

## Implemented capabilities

- Added an optional injected delayed scheduler with a daemon-based
  `threading.Timer` default and reentrant, synchronized router state.
- Replaced singular key matching with immutable, exact `KeyChord` values that
  support order-independent sets of general HID usages and normalized
  modifiers.
- Added unified buffering and resolution for general-key and modifier prefixes,
  including longer-chord precedence and ordered fallback replay of original
  events and native context.
- Implemented key-down, key-up, and long-press binding ownership across
  multi-key chord lifecycles, including cancellation, repeat suppression, reset,
  and stale-timer protection.
- Migrated ModeManager, Access8Graph, Key Echo, and NVDA Remote integration to
  the shared router while preserving app fallbacks, exit bindings, and raw
  NVDA Remote payload behavior.
- Added focused router, mode lifecycle, app-service, and raw native-context
  regression coverage.

## Tests and validation

- Targeted validation: **42 passed**.
- Latest full validation: **841 passed, 14 failed, 1 skipped**.
- The 14 failures are the known baseline limitation caused by the missing
  ignored fixture `Access8Graph/tests/test.graphml`; they are out of scope and
  do not represent mode-key-router regressions.
- Review validation also completed cleanly for the spec/plan placeholder and
  planned-type scans, and `git diff --check` reported no whitespace errors.

## Review status

Implementation and review findings were addressed through the final review
pass. The work is complete with the documented missing-fixture baseline
limitation; no source or plan/spec changes are included in this completion
commit.

## Commits after base `6bb37eb`

Chronological order:

1. `255c482d189838d5e2c2c42bc9eeba8b4c424606` — `feat: add mode key event router`
2. `73d8aecfee3e472ff3a3e9ca9070c142bd1114d1` — `feat: add default long press scheduler`
3. `e4960e9c29f2a3386a76b6e9182badc2ec816393` — `fix: preserve falsey injected scheduler`
4. `0987a674fa3f4219b4c65e015fba1acff353a6c1` — `feat: support multi-key chord values`
5. `d6fb193113aa87a4b98926b571df06bc71f2f2c6` — `feat: buffer multi-key chord prefixes`
6. `7c358bc9b95764edd54d452b0c4ac1015cdaedd9` — `fix: address mode key router review findings`
7. `5667c9ec53199d0027cc336af145678e3640ed54` — `feat: own multi-key chord lifecycles`
8. `9b76b86671b1bfa813ba9cd8e4f151eda9e69d49` — `fix: address long-press ownership review findings`
9. `bb5c42f64f3986af2ce7526b32057c6ef2d3852f` — `docs: finalize multi-key router design`
10. `d795648f48367aeee00147d58db95b0e0a5e3595` — `test: address task 5 review findings`
11. `e1e3ab0657c47b435350cafff9bbc56542650c38` — `docs: make task 5 placeholder scan self-clean`
12. `f116deabb20cf4a3af179b2c8780ad465ad651ea` — `fix: cancel stale long-press timers`
