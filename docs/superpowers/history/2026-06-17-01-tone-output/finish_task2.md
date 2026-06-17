# Tone Output - Task2 Completion (Review Fixes v2)

Date: 2026-06-17

## Review

`docs/superpowers/review_task1.md` identified two issues remaining from Task1:

1. **Important:** `Infinity` in integer tone fields (`length`, `left`, `right`) escapes validation as `OverflowError` — `int(float("inf"))` raises `OverflowError`, but both router and backend only caught `TypeError`/`ValueError`, not `OverflowError`.

2. **Minor:** Duplicate test `test_router_clamps_tone_hz_and_length_to_maximum_bounds` at lines 272 and 439 — only one was collected by pytest.

## Verification of Review Findings

Both findings confirmed correct:

| Finding | Confirmed at |
|---------|-------------|
| `_coerce_int` raises `OverflowError` for `float("inf")` | `src/interop/protocol/routing/message_router.py:27` — `return int(value)` |
| `_handle_tone_message` only catches `TypeError, ValueError` | `message_router.py:103` — missing `OverflowError` |
| `normalize_beep_parameters` `int(length)`/`int(left)`/`int(right)` vulnerable | `src/adapters/outputs/tone.py:53-55` |
| `DefaultToneOutput.beep()` only catches `TypeError, ValueError` | `tone.py:135` — missing `OverflowError` |
| Duplicate test at line 272 | `tests/unit/test_message_router.py:272` |

## Changes Made

### 1. Router: non-finite rejection in coercion helpers

`src/interop/protocol/routing/message_router.py`:
- `_coerce_float`: added `math.isfinite()` check before returning — raises `ValueError` for `inf`/`nan`
- `_coerce_int`: added `isinstance(value, float) and not math.isfinite(value)` check before `int()` — raises `ValueError` for `inf`/`nan`
- `_handle_tone_message`: added `OverflowError` to the catch tuple as defense-in-depth; removed redundant separate `math.isfinite(hz)` check since `_coerce_float` now handles it

### 2. Backend: non-finite normalization for integer fields

`src/adapters/outputs/tone.py`:
- `normalize_beep_parameters`: zeros non-finite `length`, `left`, `right` before `int()` call, matching the existing `hz` non-finite handling
- `DefaultToneOutput.beep()`: added `OverflowError` to the catch tuple as defense-in-depth

### 3. Duplicate test removed

`tests/unit/test_message_router.py`: removed duplicate `test_router_clamps_tone_hz_and_length_to_maximum_bounds` from line 272 (the remaining copy at line 422 was kept)

### 4. Tests added (+7)

| Test | Location |
|------|----------|
| `test_router_reports_infinity_tone_length_as_invalid_message` | `test_message_router.py` |
| `test_router_reports_infinity_tone_left_as_invalid_message` | `test_message_router.py` |
| `test_router_reports_infinity_tone_right_as_invalid_message` | `test_message_router.py` |
| `test_normalize_beep_parameters_zeros_inf_length` | `test_tone_output.py` |
| `test_normalize_beep_parameters_zeros_inf_left` | `test_tone_output.py` |
| `test_normalize_beep_parameters_zeros_inf_right` | `test_tone_output.py` |
| `test_default_tone_output_noops_on_inf_length` | `test_tone_output.py` |

## Verification

- `459 passed in 0.78s` — full unit + integration test suite
- All tone fields (`hz`, `length`, `left`, `right`) now consistently handle non-finite values via `invalid_message` (router) or safe noop (backend)

## Complete Commit List

| Commit | Message |
|--------|---------|
| `a203fe8` | test: add remote tone router coverage |
| `b70345d` | feat: route remote tone messages |
| `b75a04a` | feat: handle remote tones in output layer |
| `8a94b74` | feat: add default tone output backend |
| `b79cb2a` | feat: compose default tone output |
| `613c671` | fix: bound remote tone hz and length to prevent transport blockage |
| `77ea5ed` | fix: reject non-finite values in all tone numeric fields |
