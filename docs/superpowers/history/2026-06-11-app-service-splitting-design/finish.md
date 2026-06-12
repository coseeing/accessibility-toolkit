# App Service Splitting — Completion Report

**Date:** 2026-06-11  
**Branch:** (current)  
**Based on:**
- Spec: `docs/superpowers/specs/2026-06-11-app-service-splitting-design.md`
- Plan: `docs/superpowers/plans/2026-06-11-app-service-splitting-implementation.md`

## Summary

Split `NvdaRemoteAppService` and `KeyEchoAppService` into thin facades plus focused use cases, while unifying state-transition hotkeys behind one mapping-based mechanism. All 240 tests pass, UI behavior preserved.

## Deliverables

### New Files (src)

```
src/apps/nvda_remote/use_cases/__init__.py
src/apps/nvda_remote/use_cases/state_transition_hotkeys.py
src/apps/nvda_remote/use_cases/speech_settings.py
src/apps/nvda_remote/use_cases/control_mode.py
src/apps/nvda_remote/use_cases/input_forwarding.py
src/apps/key_echo/use_cases/__init__.py
src/apps/key_echo/use_cases/state_transition_hotkeys.py
src/apps/key_echo/use_cases/speech_settings.py
src/apps/key_echo/use_cases/echo_control.py
src/apps/key_echo/use_cases/echo_input.py
src/apps/nvda_remote/facade.py
src/apps/key_echo/facade.py
```

### New Files (tests)

```
tests/unit/test_nvda_remote_use_cases.py
tests/unit/test_key_echo_use_cases.py
```

### Modified Files

```
src/apps/nvda_remote/service.py          → compatibility re-export
src/apps/key_echo/service.py             → compatibility re-export
src/apps/nvda_remote/main.py             → imports NvdaRemoteAppFacade
src/apps/key_echo/main.py                → imports KeyEchoAppFacade
tests/unit/test_nvda_remote_app_service.py → +1 test (F11 toggle)
tests/unit/test_key_echo_app_service.py    → +2 tests (Enter echo start)
tests/unit/test_app_wx.py                  → monkeypatch targets updated
```

## Architecture

```
UI → AppFacade → UseCases → lower-level services/protocols
```

### nvda_remote
- **NvdaRemoteAppFacade** — thin UI-facing controller
- **ConnectionUseCase** — (session/router stays in facade for phase 1)
- **NvdaRemoteControlModeUseCase** — start/stop control lifecycle
- **NvdaRemoteInputForwardingUseCase** — key forwarding + suppression
- **NvdaRemoteSpeechSettingsUseCase** — backend/voice/rate/pitch/volume
- **NvdaRemoteStateTransitionHotkeyUseCase** — F11 → toggle_control

### key_echo
- **KeyEchoAppFacade** — thin UI-facing controller
- **KeyEchoControlUseCase** — start/stop echo lifecycle
- **KeyEchoInputUseCase** — keydown-to-speech behavior
- **KeyEchoSpeechSettingsUseCase** — backend/voice/rate/pitch/volume
- **KeyEchoStateTransitionHotkeyUseCase** — Enter → start_echo, Escape → stop_echo

## State-Transition Hotkeys

| App | Hotkey | Action |
|-----|--------|--------|
| nvda_remote | F11 (0x7A) | Toggle control mode |
| key_echo | Enter (0x0D) | Start echo mode |
| key_echo | Escape (0x1B) | Stop echo mode |

## Test Results

```
240 passed (unit + integration)
```

- Use-case tests: 10 passed
- App service tests: 22 passed
- wx composition tests: 30 passed
- All other unit/integration tests: 178 passed

## Success Criteria Met

1. `NvdaRemoteAppService` reduced to thin facade role via compatibility re-export
2. `KeyEchoAppService` follows same facade/use-case structural pattern
3. Core app business rules moved into focused use-case classes
4. Existing UI-facing behavior compatible (all wx tests pass)
5. Existing regression tests continue to pass (240/240)
6. New use-case unit tests exist (10 tests across 2 files)
7. State-transition hotkeys use same mapping-based mechanism
8. No adjacent refactors pulled into this change set

## Commits

```
0dfa933 test: cover app facade hotkey transitions
a5a7f08 feat: add state transition hotkey use cases
4ebf326 feat: add app speech settings use cases
160b886 feat: add app control lifecycle use cases
d001897 feat: add app input behavior use cases
b3c9353 refactor: introduce app facades and use cases
baae676 refactor: rewire runtimes to app facades
```
