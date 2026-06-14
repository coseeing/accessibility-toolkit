# Keyboard Pipeline Decision Model — Implementation Complete

## Summary

Replaced the lossy `KeyEventDecision` enum (`SUPPRESS` / `PASS_THROUGH`) with a structured two-dimensional model that separates **system pass-through** from **app handling state**. The new model enables the previously impossible combination: send to system **and** app also handles the event.

The first concrete use case — Windows `Num Lock` in `key_echo` — now works correctly: the system receives `Num Lock` so state stays synchronized, while `key_echo` still speaks the key.

## Architecture

Two new core types:

| Type | Description |
|------|-------------|
| `AppKeyEventResult` | App-internal handling state: `UNHANDLED`, `HANDLED_CONTINUE`, `HANDLED_STOP` |
| `KeyboardPipelineResult` | Final boundary result: `send_to_system: bool` + `app_result: AppKeyEventResult` |

Three-stage pipeline in `key_echo`:
1. `SystemPassThroughPolicyStage` — decides `send_to_system` (Windows Num Lock → True)
2. `ModeHandlingStage` — runs app logic, returns `AppKeyEventResult`
3. `DecisionAssembly` — combines into `KeyboardPipelineResult`

## Test Results

```
378 passed (373 unit + 5 integration) in 0.71s
```

All tests pass — no regressions.

## Commit List

```
5cd88c4 test: verify keyboard pipeline decision model refactor
4b4fa85 refactor: adapt nvda remote service to pipeline result
62b0a56 feat: add key echo keyboard pipeline
2fe4a84 refactor: switch keyboard captures to pipeline result
354d6c5 refactor: return app results from key echo input use case
584a192 refactor: return app key event results from policies
5515522 feat: add keyboard pipeline assembly helper
8cda556 feat: add keyboard pipeline result types
```

## Files Changed

### New Files
- `src/application/input/results.py` — `AppKeyEventResult`, `KeyboardPipelineResult`
- `src/application/input/keyboard_pipeline.py` — `assemble_pipeline_result()`
- `tests/unit/test_keyboard_pipeline_results.py`
- `tests/unit/test_keyboard_pipeline.py`

### Modified Files
- `src/application/input/__init__.py` — exports new types
- `src/application/input/active_key_policy.py` — returns `AppKeyEventResult`
- `src/application/input/system_toggle_policy.py` — returns `bool`
- `src/application/keyboard.py` — `KeyEventHandler` returns `KeyboardPipelineResult`
- `src/apps/shared/mode_manager.py` — returns `AppKeyEventResult`
- `src/apps/shared/mode_types.py` — protocol updated
- `src/apps/key_echo/use_cases/echo_input.py` — returns `AppKeyEventResult`
- `src/apps/key_echo/service.py` — three-stage pipeline, returns `KeyboardPipelineResult`
- `src/apps/nvda_remote/service.py` — interface compatibility, returns `KeyboardPipelineResult`
- `src/adapters/inputs/base.py` — listener contract uses `KeyboardPipelineResult`
- `src/adapters/windows/keyboard_hook.py` — reads `send_to_system`
- `src/adapters/macos/keyboard_hook.py` — reads `send_to_system`
- `src/adapters/macos/event_tap.py` — reads `send_to_system`
- `src/adapters/windows/hotkey.py` — returns `KeyboardPipelineResult`

### Updated Test Files
- `tests/unit/test_input_policies.py`
- `tests/unit/test_mode_manager.py`
- `tests/unit/test_key_echo_use_cases.py`
- `tests/unit/test_key_echo_app_service.py`
- `tests/unit/test_nvda_remote_app_service.py`
- `tests/unit/test_windows_adapters.py`
- `tests/unit/test_macos_adapters.py`
