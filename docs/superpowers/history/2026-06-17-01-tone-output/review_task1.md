# Tone Output Task1 Review

Date: 2026-06-17

## Review Scope

Reviewed `docs/superpowers/finish_task1.md` and the commits listed there, in chronological order:

| Order | Commit | Message |
|---:|---|---|
| 1 | `a203fe8` | `test: add remote tone router coverage` |
| 2 | `b70345d` | `feat: route remote tone messages` |
| 3 | `b75a04a` | `feat: handle remote tones in output layer` |
| 4 | `8a94b74` | `feat: add default tone output backend` |
| 5 | `b79cb2a` | `feat: compose default tone output` |
| 6 | `613c671` | `fix: bound remote tone hz and length to prevent transport blockage` |

The first five commits were reviewed in `docs/superpowers/review_task0.md`; this review focuses on whether `613c671` resolves the prior Important finding and whether it introduces or leaves new issues.

## Findings

### Important: `Infinity` in integer tone fields still escapes validation as `OverflowError`

Files:

- `src/interop/protocol/routing/message_router.py:23`
- `src/interop/protocol/routing/message_router.py:100`
- `src/adapters/outputs/tone.py:53`
- `src/adapters/outputs/tone.py:136`

`613c671` correctly rejects non-finite `hz`, but `length`, `left`, and `right` still use `int(value)` before any `math.isfinite()` check. For `float("inf")`, Python raises `OverflowError`, while both router and backend only catch `TypeError` and `ValueError`.

This is reachable from remote input because Python `json.loads()` accepts `Infinity` by default:

```python
json.loads('{"type":"tone","hz":440,"length":Infinity,"left":50,"right":50}')
```

Observed behavior during review:

```text
router exception {'type': 'tone', 'hz': 440, 'length': inf, 'left': 50, 'right': 50} OverflowError cannot convert float infinity to integer
router exception {'type': 'tone', 'hz': 440, 'length': 80, 'left': inf, 'right': 50} OverflowError cannot convert float infinity to integer
router exception {'type': 'tone', 'hz': 440, 'length': 80, 'left': 50, 'right': inf} OverflowError cannot convert float infinity to integer
backend exception (440, inf, 50, 50) OverflowError cannot convert float infinity to integer
backend exception (440, 80, inf, 50) OverflowError cannot convert float infinity to integer
backend exception (440, 80, 50, inf) OverflowError cannot convert float infinity to integer
```

Impact:

- The original unbounded loop/allocation problem is mostly fixed for large finite values.
- A malformed remote tone payload can still raise an unhandled exception in router handling.
- Because `RelayTransport._read_loop()` calls the message handler inline, this can kill the reader thread or bypass the intended `invalid_message` status path.
- The backend defense-in-depth layer also does not fully satisfy the "playback failures are logged and do not tear down the app" requirement for non-finite integer-like fields.

Recommended fix:

- Update `_coerce_int()` to reject non-finite floats before `int(value)`, or catch `OverflowError` alongside `TypeError` and `ValueError`.
- Prefer explicit finite numeric coercion helpers for all tone fields, not only `hz`.
- Update `DefaultToneOutput.beep()` to catch `OverflowError` or make `normalize_beep_parameters()` fully normalize/reject non-finite `length`, `left`, and `right`.
- Add tests for `Infinity` in `length`, `left`, and `right` at both router and backend layers.

### Minor: duplicate router test name hides one copy during collection

File:

- `tests/unit/test_message_router.py:272`
- `tests/unit/test_message_router.py:439`

`test_router_clamps_tone_hz_and_length_to_maximum_bounds` appears twice in the same module. Pytest collected only one test with that name in the focused run, so the earlier definition is overwritten by the later definition at import time.

Impact:

- No product behavior impact.
- Test output overstates the intentionality of the coverage and can confuse future maintenance.

Recommended fix:

- Remove the duplicate test or rename one if it is meant to cover a distinct location/scenario.

## Commit-By-Commit Review

### 1. `a203fe8` - `test: add remote tone router coverage`

Status: previously reviewed in `review_task0`.

Notes:

- Provides baseline router coverage for the tone feature.
- Did not include upper-bound or non-finite integer-field tests, which explains the remaining `Infinity` gap.

### 2. `b70345d` - `feat: route remote tone messages`

Status: previously reviewed in `review_task0`.

Notes:

- Adds the tone router path.
- Original lack of upper bounds is addressed by `613c671` for large finite values.

### 3. `b75a04a` - `feat: handle remote tones in output layer`

Status: previously reviewed in `review_task0`; no new issue found in this commit during Task1 review.

### 4. `8a94b74` - `feat: add default tone output backend`

Status: previously reviewed in `review_task0`; still relevant because Task1 changed backend normalization.

Notes:

- `613c671` adds maximum bounds to `normalize_beep_parameters()`.
- Backend still raises `OverflowError` for non-finite `length`, `left`, or `right`, so defense-in-depth remains incomplete.

### 5. `b79cb2a` - `feat: compose default tone output`

Status: previously reviewed in `review_task0`; no new issue found in this commit during Task1 review.

### 6. `613c671` - `fix: bound remote tone hz and length to prevent transport blockage`

Status: partially complete.

What is fixed:

- Adds finite upper bounds for large finite `hz` and `length` values.
- Rejects `inf`/`nan` for `hz` in the router.
- Adds backend max-bound constants and clamps large finite backend inputs.
- Adds tests for large finite max bounds and non-finite `hz`.

What remains:

- `Infinity` in `length`, `left`, or `right` bypasses current exception handling as `OverflowError`.
- The test file contains a duplicate test name.

## Requirements Check

| Requirement | Status | Notes |
|---|---|---|
| Previous unbounded large finite tone values are bounded | Pass | `hz=50000`, `length=30000` are clamped to `20000.0`, `5000`. |
| Remote invalid tone payloads report `invalid_message` instead of crashing | Partial | `hz=inf/nan` works; `length/left/right=inf` raises `OverflowError`. |
| Backend normalization prevents unbounded WAV generation | Partial | Large finite values are bounded; `length=inf` raises before logging/returning. |
| No NVDA runtime dependencies in tone backend | Pass | Verified no forbidden NVDA runtime imports. |
| Existing test suite passes | Pass | Full unit + integration suite passes. |

## Verification Performed

Commands run:

```bash
python3 -m pytest tests/unit/test_message_router.py tests/unit/test_tone_output.py -v
```

Result: `31 passed in 0.13s`

```bash
python3 -m pytest tests/unit tests/integration -v
```

Result: `452 passed in 0.81s`

```bash
rg -n "^\s*(from|import)\s+(config|extensionPoints|nvwave|logHandler)\b|NVDAHelper" src/adapters/outputs/tone.py src
```

Result: no matches.

Manual edge-case verification:

```bash
PYTHONPATH=src python3 - <<'PY'
import json
from interop.protocol.routing.message_router import MessageRouter
from adapters.outputs.tone import DefaultToneOutput

payloads = [
    {"type": "tone", "hz": 440, "length": float("inf"), "left": 50, "right": 50},
    {"type": "tone", "hz": 440, "length": 80, "left": float("inf"), "right": 50},
    {"type": "tone", "hz": 440, "length": 80, "left": 50, "right": float("inf")},
]

for payload in payloads:
    seen = []
    router = MessageRouter(
        on_speech=lambda s: None,
        on_cancel=lambda: None,
        on_pause=lambda p: None,
        on_clipboard=lambda t: None,
        on_tone=lambda *args: seen.append(args),
        on_status=lambda e: seen.append(("status", e)),
    )
    try:
        router.handle_message(payload)
        print("router ok", payload, seen)
    except Exception as e:
        print("router exception", payload, type(e).__name__, e)

for args in [
    (440, float("inf"), 50, 50),
    (440, 80, float("inf"), 50),
    (440, 80, 50, float("inf")),
]:
    try:
        DefaultToneOutput(playback=type("P", (), {"play": lambda self, b: None})()).beep(*args)
        print("backend ok", args)
    except Exception as e:
        print("backend exception", args, type(e).__name__, e)

print(json.loads('{"type":"tone","hz":440,"length":Infinity,"left":50,"right":50}'))
PY
```

Result: `OverflowError` for `Infinity` in `length`, `left`, and `right`.

## Overall Assessment

Task1 substantially fixes the original transport-blockage issue for large finite values, but it is not complete. I would not consider the review finding fully resolved until all tone numeric fields handle non-finite values consistently and return `invalid_message` or safely noop instead of raising `OverflowError`.
