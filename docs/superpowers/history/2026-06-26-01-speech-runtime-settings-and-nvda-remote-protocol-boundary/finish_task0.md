# Speech Runtime Settings & NVDA Remote Protocol Boundary - Implementation Complete

## Summary

Implemented all 3 milestones across 6 tasks using Subagent-Driven Development:

### Milestone 1: Shared Speech Runtime Settings Persistence

- **Task 1**: Created `SpeechRuntimeSettingsCoordinator` in `src/apps/shared/speech_runtime_settings.py` with `apply_saved_settings()`, `build_engine_change_callback()`, and `selected_engine_id()` methods that encapsulate the duplicated speech settings startup logic.
- **Task 2**: Rewired `nvda_remote`, `key_echo`, and `access8graph` entrypoints to use the coordinator, eliminating 6 duplicated code blocks (3 `_apply_saved_speech_settings` + 3 `_on_speech_engine_changed`).

### Milestone 2: Typed NVDA Remote Protocol Events

- **Task 3**: Created `src/interop/protocol/events.py` with typed dataclasses (`RemoteSessionConnected`, `RemoteSessionDisconnected`, `RemoteSessionVersionMismatch`, `RemotePeerMessageReceived`). Updated `RemoteSession` to emit typed events instead of dict payloads. Moved session tests to `test_remote_session.py`.
- **Task 4**: Added `RemoteProtocolMessageInvalid` and `RemoteProtocolMessageIgnored` to events. Updated `MessageRouter` to emit typed events instead of dict payloads. Updated all 12 router test assertions.
- **Task 5**: Updated `NvdaRemoteAppService` to consume typed protocol events via `_on_protocol_event()` with match/case dispatch. Removed `StatusEvent` transitional helper entirely. Removed `_on_status()`, `_event_from_status()`, `_handle_connection_status()`.

### Milestone 3: NVDA Remote Orchestration Split

- **Task 6**: Created 3 new use-case classes: `RemoteConnectionUseCase`, `RemoteProtocolEventHandler`, `RemoteStatusPresenter`. Thinned `NvdaRemoteAppService` (-45 lines) with `_on_protocol_event()` and `_notify_status_listener()` becoming one-line delegations. Public API unchanged.

## Commit List

```
f2e23c3 refactor: split nvda remote orchestration
b6a475f refactor: consume typed protocol events in nvda remote
88be7b7 feat: add typed message router events
129ae28 fix: update integration test for typed remote session events
52c5a7d feat: add typed remote session events
2f5c90c refactor: share speech runtime settings wiring
9ac5556 feat: add speech runtime settings coordinator
```

## Test Results

Full regression suite: **591/591 tests passed** (0 failures, 0 errors).

## Files Changed

### Created
- `src/apps/shared/speech_runtime_settings.py` - Speech runtime settings coordinator
- `src/interop/protocol/events.py` - Typed protocol event dataclasses
- `src/apps/nvda_remote/use_cases/connection.py` - Connection orchestration
- `src/apps/nvda_remote/use_cases/protocol_events.py` - Protocol event handler
- `src/apps/nvda_remote/use_cases/status_presentation.py` - Status presenter
- `tests/unit/test_speech_runtime_settings.py` - Coordinator tests
- `tests/unit/test_remote_session.py` - Session event tests

### Modified
- `src/apps/shared/__init__.py` - Export coordinator
- `src/apps/nvda_remote/main.py` - Use coordinator
- `src/apps/key_echo/main.py` - Use coordinator
- `src/apps/access8graph/main.py` - Use coordinator
- `src/interop/protocol/session/remote_session.py` - Typed events
- `src/interop/protocol/routing/message_router.py` - Typed events
- `src/apps/nvda_remote/service.py` - Consume typed events + orchestration split
- `src/apps/nvda_remote/use_cases/__init__.py` - Export new use cases
- `src/application/events.py` - Remove StatusEvent
- `tests/unit/test_bootstrap_app_runtime.py` - Coordinator integration tests
- `tests/unit/test_app_wx.py` - Regression assertion
- `tests/unit/test_message_router.py` - Typed event assertions, session test removal
- `tests/unit/test_nvda_remote_app_service.py` - Updated for typed events
- `tests/unit/test_application_events.py` - Remove StatusEvent tests
- `tests/unit/test_nvda_remote_use_cases.py` - New use case tests
- `tests/integration/test_relay_session.py` - on_event parameter fix
