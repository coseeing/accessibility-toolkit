# Final Whole-Branch Review Fix Report

## Status

Implemented all three final whole-branch review findings.

## Fixes

### 1. RelayTransport stale-reader race

Root cause: reader shutdown used a shared reusable `Event`. If a reader did not
finish within the one-second join timeout, `stop_reader()` detached it. A later
`start_reader()` cleared the same event, allowing the detached reader to publish
`transport_disconnected` into the replacement connection's service state.

`RelayTransport` now assigns each reader its own cancellation event and
monotonically increasing generation. Reader payloads and disconnect events are
published only while that reader is still current. The current-reader check and
callback are serialized under a reentrant lock, preventing replacement from
occurring between validation and publication. `close()` and `stop_reader()`
invalidate the generation before joining, while retaining the existing bounded
join behavior.

Added `test_replacement_reader_cannot_publish_delayed_old_disconnect`, which
holds the old reader beyond the join timeout, starts a replacement reader, and
asserts that only the replacement reader's message is delivered.

### 2. Main-frame Disconnect state

The dedicated Disconnect action is now enabled for every non-IDLE state,
including CONNECTING. Manage Connections remains disabled only while CONNECTING,
and Quick Connect remains limited to IDLE with a valid saved default.

Updated the wx state-transition test to assert Disconnect is enabled while
CONNECTING.

### 3. Strict catalog format version

`ConnectionCatalog.from_dict` now requires `type(format_version) is int` and an
exact value of `1`, rejecting booleans, `1.0`, strings, and other versions.
Model and store tests cover all of these non-exact forms.

## Exact verification output

Command:

```text
pytest tests/unit/test_nvda_remote_connection_models.py tests/unit/test_nvda_remote_connection_store.py tests/unit/test_app_wx.py -v
```

Output:

```text
============================== 47 passed in 0.31s ==============================
```

Command:

```text
pytest tests/integration/test_relay_session.py -v
```

Output:

```text
============================== 6 passed in 0.10s ===============================
```

Command:

```text
pytest tests/unit tests/integration -v
```

Output:

```text
======================== 942 passed, 1 skipped in 4.18s ========================
```

Additional focused regression verification:

```text
pytest tests/unit/test_relay_transport.py -v
============================== 1 passed in 2.04s ===============================
```

`git diff --check` completed without whitespace errors.

## Concerns

The full suite reports one pre-existing/expected skipped test. The worktree
also contains unrelated pre-existing changes in `.superpowers/sdd/task-1-report.md`
and untracked plan/spec documentation; these were not staged or modified.
