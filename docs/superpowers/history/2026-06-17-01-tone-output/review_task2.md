# Tone Output Task2 Review

Date: 2026-06-17

## Review Scope

Reviewed `docs/superpowers/finish_task2.md` and the commits listed there, in chronological order:

| Order | Commit | Message |
|---:|---|---|
| 1 | `a203fe8` | `test: add remote tone router coverage` |
| 2 | `b70345d` | `feat: route remote tone messages` |
| 3 | `b75a04a` | `feat: handle remote tones in output layer` |
| 4 | `8a94b74` | `feat: add default tone output backend` |
| 5 | `b79cb2a` | `feat: compose default tone output` |
| 6 | `613c671` | `fix: bound remote tone hz and length to prevent transport blockage` |
| 7 | `77ea5ed` | `fix: reject non-finite values in all tone numeric fields` |

The earlier commits were reviewed in `docs/superpowers/review_task0.md` and `docs/superpowers/review_task1.md`; this review focuses on whether `77ea5ed` resolves the remaining Task1 findings and introduces any new problems.

## Findings

No blocking findings found.

Task2 resolves both issues from `review_task1.md`:

- `Infinity` in `length`, `left`, and `right` no longer escapes as `OverflowError`.
- The duplicate `test_router_clamps_tone_hz_and_length_to_maximum_bounds` definition was removed; only one definition remains.

## Commit-By-Commit Review

### 1. `a203fe8` - `test: add remote tone router coverage`

Status: previously reviewed.

Notes:

- Provides the original router coverage foundation.
- No new concerns introduced by Task2.

### 2. `b70345d` - `feat: route remote tone messages`

Status: previously reviewed.

Notes:

- The router path remains intact.
- Task2 improves the shared numeric coercion helpers used by this path.

### 3. `b75a04a` - `feat: handle remote tones in output layer`

Status: previously reviewed.

Notes:

- No changes in Task2 affect the output-layer routing behavior.

### 4. `8a94b74` - `feat: add default tone output backend`

Status: previously reviewed.

Notes:

- Task2 strengthens `normalize_beep_parameters()` and `DefaultToneOutput.beep()` defense-in-depth.
- Backend no longer raises on non-finite `length`, `left`, or `right`.

### 5. `b79cb2a` - `feat: compose default tone output`

Status: previously reviewed.

Notes:

- Runtime composition remains unchanged.
- No new composition or dependency issue found.

### 6. `613c671` - `fix: bound remote tone hz and length to prevent transport blockage`

Status: previously reviewed as partial.

Notes:

- Large finite bounds from this commit still work.
- The remaining non-finite integer-field gap is resolved by `77ea5ed`.

### 7. `77ea5ed` - `fix: reject non-finite values in all tone numeric fields`

Status: acceptable.

What was fixed:

- `_coerce_float()` now rejects non-finite values directly.
- `_coerce_int()` now rejects non-finite float values before calling `int()`.
- `_handle_tone_message()` catches `OverflowError` as defense-in-depth.
- `normalize_beep_parameters()` converts non-finite `length`, `left`, and `right` floats to `0` before integer conversion.
- `DefaultToneOutput.beep()` catches `OverflowError` as defense-in-depth.
- Added tests for `Infinity` in router integer fields and backend normalization.
- Removed the duplicate router test definition.

Behavior check:

- Router now handles `Infinity` in `hz`, `length`, `left`, and `right` by emitting `invalid_message`.
- Backend now noops for `length=Infinity`.
- Backend normalizes non-finite `left` or `right` to `0`; if the other channel is valid, playback can still occur on the valid channel. This is safe and bounded, and does not reintroduce the transport-blockage or unhandled-exception risk.

## Requirements Check

| Requirement | Status | Notes |
|---|---|---|
| Large finite remote tone values are bounded | Pass | `hz` and `length` remain clamped to safe maximums. |
| Non-finite remote tone values do not crash router | Pass | `hz`, `length`, `left`, and `right` return `invalid_message`. |
| Backend defense-in-depth handles non-finite values safely | Pass | No unhandled exception or unbounded WAV generation observed. |
| Duplicate router test removed | Pass | Only one `test_router_clamps_tone_hz_and_length_to_maximum_bounds` remains. |
| No NVDA runtime dependencies in tone backend | Pass | Forbidden import scan returned no matches. |
| Existing tests pass | Pass | Full unit + integration suite passes. |

## Verification Performed

Commands run:

```bash
python3 -m pytest tests/unit/test_message_router.py tests/unit/test_tone_output.py -v
```

Result: `38 passed in 0.14s`

```bash
python3 -m pytest tests/unit tests/integration -v
```

Result: `459 passed in 0.79s`

```bash
rg -n "def test_router_clamps_tone_hz_and_length_to_maximum_bounds" tests/unit/test_message_router.py
```

Result: one match.

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
    {"type": "tone", "hz": float("inf"), "length": 80, "left": 50, "right": 50},
    {"type": "tone", "hz": float("nan"), "length": 80, "left": 50, "right": 50},
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
        on_tone=lambda *args: seen.append(("tone", args)),
        on_status=lambda e: seen.append(("status", e)),
    )
    router.handle_message(payload)
    print("router ok", seen)

class Playback:
    def __init__(self):
        self.calls = []
    def play(self, wav_data):
        self.calls.append(wav_data)

for args in [
    (440, float("inf"), 50, 50),
    (440, 80, float("inf"), 50),
    (440, 80, 50, float("inf")),
]:
    playback = Playback()
    DefaultToneOutput(playback=playback).beep(*args)
    print("backend ok", args, len(playback.calls))

print(json.loads('{"type":"tone","hz":440,"length":Infinity,"left":50,"right":50}'))
PY
```

Result:

- Router returned `invalid_message` for all non-finite tone fields.
- Backend did not raise for non-finite `length`, `left`, or `right`.
- `json.loads()` still accepts `Infinity`, confirming the regression case is covered by the router behavior.

## Overall Assessment

Task2 completes the requested correction. The prior Important and Minor findings are resolved, and I did not find a new regression introduced by `77ea5ed`.
