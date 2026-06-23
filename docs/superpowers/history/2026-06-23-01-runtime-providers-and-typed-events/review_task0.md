# Runtime Providers And Typed Events Review Task 0

Date: 2026-06-23

## Review Scope

Reviewed the implementation described by:

- `docs/superpowers/finish_task0.md`
- `docs/superpowers/specs/2026-06-23-runtime-providers-and-typed-events-design.md`
- `docs/superpowers/plans/2026-06-23-runtime-providers-and-typed-events-implementation.md`

The current checkout did not contain `docs/superpowers/finish_task0.md`; the completed work is on the local branch/worktree `runtime-providers-typed-events`. I reviewed the finish report from:

- `runtime-providers-typed-events:docs/superpowers/finish_task0.md`

Per the finish report, only these implementation commits were reviewed, in old-to-new order:

1. `ee554d6` test: cover bootstrap platform provider
2. `b4865cb` refactor: add runtime output builder
3. `435e7f7` refactor: centralize app runtime wiring
4. `f041e00` refactor: use shared runtime builder in key echo
5. `948a996` refactor: use shared runtime builder in access8graph
6. `0495a17` refactor: use shared runtime builder in nvda remote
7. `23a6de8` refactor: tighten runtime builder resource ownership
8. `60af804` feat: add typed application events
9. `af8aea3` feat: add app typed events
10. `bde2331` refactor: emit typed mode events
11. `8ed87d9` refactor: migrate key echo typed events
12. `573e1c2` refactor: migrate access8graph typed events
13. `53a0798` refactor: migrate nvda remote typed events
14. `c335050` refactor: migrate UI status consumers to typed events
15. `a108ee1` refactor: remove dict-first app status flow
16. `291073f` refactor: keep nvda remote status boundary typed
17. `8cb9126` refactor: tighten typed status event boundaries

## Findings

No blocking or correctness findings found.

## Commit-Order Review Notes

- `ee554d6`: `PlatformProvider`/`PlatformServices` wraps existing platform factories without changing the old public factory functions. This matches M1's "lightweight provider, not container" direction.
- `b4865cb`: `build_output_services()` centralizes scheduler/speech/speaker/capability assembly. The later `23a6de8` resource-ownership fix addresses the main failure-mode concern.
- `435e7f7`: `build_app_runtime_parts()` introduces a focused common runtime seam. The final shape avoids constructing clipboard unless requested and keeps tone optional.
- `f041e00`, `948a996`, `0495a17`: all three app entrypoints became thinner and still retain app-specific decisions: app service class, UI app class, hotkey usage, config/transport.
- `23a6de8`: output builder now shuts down the scheduler on construction/fallback failures. Tests cover options factory failure and fallback callback failure.
- `60af804`, `af8aea3`: shared vs app-domain event split follows the spec: shared events in `application/events.py`; app events in `apps/*/events.py`.
- `bde2331`: `ModeManager` emits `ModeChanged`, and `AppEvent` includes `ModeChanged`, so services can consume it through the shared event union.
- `8ed87d9`, `573e1c2`, `53a0798`: Key Echo, Access8Graph, and NVDA Remote services now emit typed events to UI-facing listeners.
- `c335050`: UI frames consume typed events rather than raw dict key checks.
- `a108ee1`, `291073f`, `8cb9126`: NVDA Remote protocol/router dicts remain isolated behind `StatusEvent.from_payload()` and are converted at the app boundary. Unknown protocol status kinds are ignored instead of leaking generic status objects to UI listeners.

## Verification

Commands run in `.worktrees/runtime-providers-typed-events`:

```bash
pytest tests/unit/test_bootstrap_output.py tests/unit/test_bootstrap_app_runtime.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_access8graph_app_service.py tests/unit/test_key_echo_app_service.py -v
```

Result: `70 passed`.

```bash
pytest tests/unit tests/integration -v
```

Result: `500 passed`.

```bash
git diff --check
```

Result: no output.

Additional scan:

```bash
rg -n '\{"kind"|status\.get\("kind"|status\["kind"\]|_status\.get\("kind"|StatusEvent|set_status_listener|_notify_status_listener' src/apps src/application src/ui tests/unit
```

Result: remaining app/UI matches are listener method names, typed notification methods, and NVDA Remote's explicit `StatusEvent.from_payload()` protocol-to-event conversion path. Remaining dict assertions are protocol/message-router tests, not the app/UI listener contract.

## Residual Risks

- The review ran on Linux. Windows/macOS adapter behavior remains primarily covered by injected/fake adapter tests, not live platform smoke tests.
- `StatusEvent.from_payload()` remains intentionally transitional for NVDA Remote protocol/router conversion. This is acceptable per spec, but it should not grow into a generic app/UI event API again.
- `build_output_services()` cleans up scheduler ownership on construction failures. If future speech backends acquire external resources during construction before a fallback persistence callback fails, add explicit backend-output cleanup coverage.
