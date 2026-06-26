# Review Task 0: Speech Runtime Settings & NVDA Remote Protocol Boundary

## Review Scope

Reviewed against:

- `docs/superpowers/finish_task0.md`
- `docs/superpowers/specs/2026-06-26-speech-runtime-settings-and-nvda-remote-protocol-boundary-design.md`
- `docs/superpowers/plans/2026-06-26-speech-runtime-settings-and-nvda-remote-protocol-boundary-implementation.md`

Commits reviewed in chronological order, using only the commits listed in the finish document:

1. `9ac5556` - `feat: add speech runtime settings coordinator`
2. `2f5c90c` - `refactor: share speech runtime settings wiring`
3. `52c5a7d` - `feat: add typed remote session events`
4. `129ae28` - `fix: update integration test for typed remote session events`
5. `88be7b7` - `feat: add typed message router events`
6. `b6a475f` - `refactor: consume typed protocol events in nvda remote`
7. `f2e23c3` - `refactor: split nvda remote orchestration`

## Findings

### Important: `version_mismatch` protocol events are emitted but dropped before reaching the app/UI boundary

`RemoteSession` now correctly emits `RemoteSessionVersionMismatch()` when it receives a `version_mismatch` message:

- `src/interop/protocol/session/remote_session.py:52`

However, the final app-level handler only handles `RemoteSessionConnected`, `RemoteSessionDisconnected`, and `RemotePeerMessageReceived`:

- `src/apps/nvda_remote/use_cases/protocol_events.py:15`

That means `RemoteSessionVersionMismatch` is silently ignored after the typed event migration. Before this refactor, `NvdaRemoteAppService._on_status()` passed the state through `_handle_connection_status("version_mismatch")`, which then emitted `RemoteConnectionChanged("version_mismatch")` to the status listener even though it did not update connection state. The new path loses that observable app event entirely.

Impact:

- UI or controller-level listeners no longer receive any signal that the relay rejected the protocol version.
- The typed event contract added by Task 3 is incomplete at the app boundary.
- There is no app-service regression test for the version mismatch path, so the drop is currently unguarded.

Suggested fix:

- Add a `RemoteSessionVersionMismatch` case in `RemoteProtocolEventHandler`.
- Map it to the previous `RemoteConnectionChanged("version_mismatch")` behavior for compatibility.
- Add a unit test in `tests/unit/test_nvda_remote_app_service.py` or `tests/unit/test_nvda_remote_use_cases.py` that asserts the listener receives `RemoteConnectionChanged("version_mismatch")`.

## Decision

- Keep protocol mismatch represented as `RemoteConnectionChanged("version_mismatch")` in this fix.
- Rationale: the approved spec emphasizes stable UI/controller behavior, and the pre-refactor app service already surfaced `version_mismatch` as a connection event. Preserving that shape minimizes this review fix to restoring lost behavior.
- Future cleanup can introduce a clearer app-domain event such as `RemoteProtocolWarning` or `RemoteProtocolMismatch`, but that should be a separate event-model refactor rather than part of this compatibility fix.

## Residual Risks

- `src/apps/access8graph/main.py:46` still applies saved settings using `selected_engine_id` rather than `parts.output.speech.get_selected_engine()`. If the configured engine is invalid and `build_app_runtime_parts()` falls back, Access8Graph may skip applying settings saved for the fallback engine. This appears to preserve prior behavior from before the coordinator extraction, so I am not listing it as a regression in this review, but it is worth tightening if the shared coordinator is expected to fully satisfy the "selected engine and settings restore on startup" validation criteria.
- `RemoteProtocolMessageIgnored` is defined in `src/interop/protocol/events.py` but is not currently emitted. That is not a behavioral bug, but it is unused API surface and may confuse future protocol event handling unless a later task uses it.

## Verification Performed

Ran focused regression tests:

```bash
pytest tests/unit/test_speech_runtime_settings.py tests/unit/test_remote_session.py tests/unit/test_message_router.py tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_app_service.py -q
```

Result:

```text
61 passed in 0.63s
```

Also manually probed current app-service behavior for `RemoteSessionVersionMismatch`:

```bash
PYTHONPATH=src python3 - <<'PY'
from tests.unit.test_nvda_remote_app_service import build_service
from interop.protocol.events import RemoteSessionVersionMismatch

service, *_ = build_service()
seen = []
service.set_status_listener(seen.append)
service._on_protocol_event(RemoteSessionVersionMismatch())
print(seen)
PY
```

Result:

```text
[]
```

## Assessment

The implementation largely matches the approved spec and plan: speech settings startup duplication has been centralized, protocol/session/router status payloads are typed, and `NvdaRemoteAppService` is thinner after the orchestration split.

The version mismatch event drop should be fixed before considering the work complete, because it is a user-visible protocol failure path and the typed protocol boundary currently emits an event that the app layer ignores.
