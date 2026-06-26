# Review Task 1: Version Mismatch Follow-up

## Review Scope

Reviewed against:

- `docs/superpowers/finish_task1.md`
- `docs/superpowers/review_task0.md`

The finish document does not list a committed hash for this follow-up. The reviewed change is the current working-tree patch documented in `finish_task1.md`:

1. `src/apps/nvda_remote/use_cases/protocol_events.py`
2. `tests/unit/test_nvda_remote_app_service.py`

## Findings

No blocking, important, or minor issues found.

The fix correctly restores the pre-refactor app/UI signal for protocol version mismatch:

- `RemoteProtocolEventHandler` now handles `RemoteSessionVersionMismatch`.
- It maps the event to `RemoteConnectionChanged("version_mismatch")`, matching the compatibility decision recorded in `review_task0.md`.
- The new regression test verifies that `NvdaRemoteAppService` surfaces `RemoteConnectionChanged("version_mismatch")` to its status listener.

Relevant code:

- `src/apps/nvda_remote/use_cases/protocol_events.py:22`
- `tests/unit/test_nvda_remote_app_service.py:745`

## Regression Risk Assessment

This change is narrowly scoped and should not introduce new connection-state side effects:

- It does not call `on_connected`.
- It does not call `on_disconnected`.
- It does not mutate `RuntimeState`.
- It only emits the compatibility event through the existing app event notification path.

That matches the old behavior described in `review_task0.md`: `version_mismatch` was surfaced as a connection event without changing connection state.

## Verification Performed

Targeted tests:

```bash
pytest tests/unit/test_nvda_remote_app_service.py::test_nvda_remote_service_surfaces_version_mismatch_for_listener tests/unit/test_nvda_remote_app_service.py::test_nvda_remote_service_dispatches_status_updates_through_main_thread_callback tests/unit/test_remote_session.py::test_session_emits_version_mismatch_and_remote_messages -q
```

Result:

```text
3 passed in 0.05s
```

Related protocol and NVDA Remote regression tests:

```bash
pytest tests/unit/test_nvda_remote_use_cases.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_remote_session.py tests/unit/test_message_router.py -q
```

Result:

```text
60 passed in 0.13s
```

Full unit and integration suite:

```bash
pytest tests/unit tests/integration -q
```

Result:

```text
592 passed in 1.19s
```

## Residual Notes

- The follow-up is still uncommitted at review time. If this is committed later, record the commit hash in the next finish document so future reviews can follow the requested commit order precisely.
- The broader event-model cleanup mentioned in `review_task0.md` remains intentionally out of scope. A future refactor can introduce a more explicit protocol warning event, but this follow-up correctly preserves compatibility.

## Assessment

The review finding from `review_task0.md` is resolved. I do not see new issues introduced by this follow-up patch.
