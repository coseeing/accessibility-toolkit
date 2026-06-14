# Fix Task 1 — Review Response

## Review Finding Analysis

**Finding:** Hotkey paths report `UNHANDLED` even when they actively handle and suppress the event.

**Correctness check:** Confirmed correct. When a hotkey fires (e.g. F11 to enter/exit a mode), the adapter invokes the handler and suppresses the event (`send_to_system=False`). However, the `app_result` was `UNHANDLED`, which contradicts the semantic contract: `UNHANDLED` means "the app layer did not handle the event." These paths clearly did handle it.

**Root cause:** The hotkey paths were migrated from `KeyEventDecision.SUPPRESS` to `KeyboardPipelineResult(send_to_system=False)` but `app_result` was not properly set to reflect the handling state — it defaulted to `UNHANDLED`.

## Changes Made

### Production Code (3 sites)

| File | Line | Old | New |
|------|------|-----|-----|
| `src/adapters/windows/hotkey.py` | 177 | `UNHANDLED` | `HANDLED_STOP` |
| `src/adapters/macos/event_tap.py` | 134 | `UNHANDLED` | `HANDLED_STOP` |
| `src/adapters/macos/event_tap.py` | 138 | `UNHANDLED` | `HANDLED_STOP` |

- **hotkey.py:177** — Hotkey matched, handler invoked, event suppressed → `HANDLED_STOP`
- **event_tap.py:134** — Suppressed key-up (of previously handled hotkey) → `HANDLED_STOP`
- **event_tap.py:138** — Hotkey handler matched and fired, event suppressed → `HANDLED_STOP`

### Test Code (5 assertions)

| File | Line | Change |
|------|------|--------|
| `tests/unit/test_windows_adapters.py` | 551 | `UNHANDLED` → `HANDLED_STOP` |
| `tests/unit/test_macos_adapters.py` | 309 | `UNHANDLED` → `HANDLED_STOP` |
| `tests/unit/test_macos_adapters.py` | 442 | `UNHANDLED` → `HANDLED_STOP` |
| `tests/unit/test_macos_adapters.py` | 445 | `UNHANDLED` → `HANDLED_STOP` |
| `tests/unit/test_macos_adapters.py` | 448 | `UNHANDLED` → `HANDLED_STOP` |

## What Was NOT Changed (Correctly `UNHANDLED`)

- Non-matching keys passing through (`send_to_system=True`) — app genuinely didn't handle
- No listener / unmapped key fallbacks — no app handling occurred
- Keyboard listener-returned values — the listener's own `app_result` choice

## Spec Update

The spec files were also updated to reflect that `nvda_remote` now adopts the shared Windows `Num Lock` pass-through policy (the as-implemented behavior matched the updated spec).

## Test Results

```
378 passed (373 unit + 5 integration) in 0.59s
```

## Commit

```
f6077b0 fix: report HANDLED_STOP from hotkey paths that suppress events
```

Added to the existing commit chain:

```
f6077b0 fix: report HANDLED_STOP from hotkey paths that suppress events
5cd88c4 test: verify keyboard pipeline decision model refactor
4b4fa85 refactor: adapt nvda remote service to pipeline result
62b0a56 feat: add key echo keyboard pipeline
2fe4a84 refactor: switch keyboard captures to pipeline result
354d6c5 refactor: return app results from key echo input use case
584a192 refactor: return app key event results from policies
5515522 feat: add keyboard pipeline assembly helper
8cda556 feat: add keyboard pipeline result types
```
