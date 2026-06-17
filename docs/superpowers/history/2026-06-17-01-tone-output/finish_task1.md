# Tone Output - Task1 Completion (Review Fixes)

Date: 2026-06-17

## Review

`docs/superpowers/review_task0.md` identified one important issue: remote tone `hz` and `length` had no upper bounds, allowing a malicious peer to block the transport reader thread by sending a massive tone that would allocate/unboundedly loop during synchronous WAV generation.

## Verification of Review Finding

The finding was correct. Confirmed at:
- `src/interop/protocol/routing/message_router.py:92-93` — only `max(0.0, ...)` / `max(0, ...)`, no upper bound
- `src/adapters/outputs/tone.py:53` — `sample_count = int(SAMPLE_RATE * params.length / 1000)` with unbounded loop
- `src/adapters/outputs/tone.py:138` — `generate_beep_wav()` called synchronously from `beep()`, which runs inline on the transport reader thread

## Changes Made

### 1. Added safe maximum constants

- `src/adapters/outputs/tone.py`: `MAX_TONE_HZ = 20000`, `MAX_TONE_LENGTH_MS = 5000`
- `src/interop/protocol/routing/message_router.py`: `_MAX_TONE_HZ = 20000`, `_MAX_TONE_LENGTH_MS = 5000`

### 2. Router: reject non-finite values, clamp to upper bounds

- `_handle_tone_message` now checks `math.isfinite(hz)` and rejects `inf`/`nan` as `invalid_message`
- `hz` clamped to `[0, _MAX_TONE_HZ]`, `length` clamped to `[0, _MAX_TONE_LENGTH_MS]`

### 3. Backend: defense-in-depth clamping

- `normalize_beep_parameters` zeros non-finite `hz` and clamps `hz` to `MAX_TONE_HZ`, `length` to `MAX_TONE_LENGTH_MS`

### 4. Tests added (+7)

| Test | Location |
|------|----------|
| `test_router_clamps_tone_hz_and_length_to_maximum_bounds` | `test_message_router.py` |
| `test_router_reports_infinity_tone_hz_as_invalid_message` | `test_message_router.py` |
| `test_router_reports_nan_tone_hz_as_invalid_message` | `test_message_router.py` |
| `test_normalize_beep_parameters_clamps_to_maximum_bounds` | `test_tone_output.py` |
| `test_normalize_beep_parameters_zeros_inf_hz` | `test_tone_output.py` |
| `test_normalize_beep_parameters_zeros_nan_hz` | `test_tone_output.py` |
| `test_default_tone_output_skips_zero_hz_tone` | `test_tone_output.py` |

## Verification

- `452 passed in 0.77s` — full unit + integration test suite
- No NVDA runtime imports in tone backend (unchanged)
- Speech serialization unchanged (unchanged)

## Complete Commit List

| Commit | Message |
|--------|---------|
| `a203fe8` | test: add remote tone router coverage |
| `b70345d` | feat: route remote tone messages |
| `b75a04a` | feat: handle remote tones in output layer |
| `8a94b74` | feat: add default tone output backend |
| `b79cb2a` | feat: compose default tone output |
| `613c671` | fix: bound remote tone hz and length to prevent transport blockage |
