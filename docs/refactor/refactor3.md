# Architecture refactor review v3

Context
-------
This review compares `docs/refactor/refactor2.md` with the current codebase.

`refactor2.md` correctly identified the main architecture tensions at the time,
but part of its recommended work has already landed:

- Shared runtime assembly now exists in:
  - `src/bootstrap/platform.py`
  - `src/bootstrap/output.py`
  - `src/bootstrap/app_runtime.py`
- Shared typed application events now exist in:
  - `src/application/events.py`
- App-specific typed events now exist in:
  - `src/apps/key_echo/events.py`
  - `src/apps/access8graph/events.py`
  - `src/apps/nvda_remote/events.py`
- Input/mode activation is more unified through:
  - `src/application/input/`
  - `src/apps/shared/mode_manager.py`
- Key echo and part of NVDA Remote logic already moved into focused use cases.

Because of that, the next refactor should not start by redoing bootstrap
extraction or re-arguing for typed events in the abstract. The remaining work is
now about finishing boundaries that were only partially established.

What Changed Since v2
---------------------

1. Runtime composition is no longer the highest-risk problem.

`refactor2.md` recommended extracting shared runtime builders. That is now
substantially done. The app entrypoints still contain some app-specific wiring,
but the large duplicated platform/output setup has already been centralized.

Current assessment:
- This area still has duplication, but it is not the main architectural
  blocker anymore.
- The remaining duplication is narrower and mostly around speech setting
  persistence and small app-specific startup policy.

2. Typed events exist, but the protocol layer is still dict-first.

The codebase now has typed events for app and shared runtime concerns, but
NVDA Remote still depends on a transitional dict-to-dataclass bridge:

- `RemoteSession` emits dict status payloads.
- `MessageRouter` emits dict status payloads.
- `NvdaRemoteAppService` converts them through `StatusEvent.from_payload()`.

Current assessment:
- The event model is only half migrated.
- The outer app layer is typed; the protocol/session/router layer is not.

3. App services are still unevenly decomposed.

There has been progress:
- `key_echo` is relatively close to the intended facade/use-case shape.
- NVDA Remote has extracted control/input-forwarding use cases, but the app
  service still owns too much orchestration.
- Access8Graph is still more service-centric than the other apps.

Current assessment:
- The next refactor should focus on service boundary completion, not on moving
  files around.

Updated Pressure Points
-----------------------

1. Finish typed events at the protocol boundary.

Files:
- `src/interop/protocol/session/remote_session.py`
- `src/interop/protocol/routing/message_router.py`
- `src/apps/nvda_remote/service.py`
- `src/application/events.py`
- `src/apps/nvda_remote/events.py`

Current state:
- `RemoteSession` emits dict payloads such as connection and remote message
  statuses.
- `MessageRouter` emits dict payloads for unknown messages and invalid payloads.
- `NvdaRemoteAppService` still contains translation logic from transport/router
  dict payloads into UI-facing typed events.
- `StatusEvent` exists only as a transitional adapter and is still part of the
  live architecture, not just compatibility support.

Why this is now the top priority:
- It blocks the next stage of NVDA Remote service splitting.
- It keeps protocol contracts implicit and stringly typed.
- It forces `NvdaRemoteAppService` to keep event-translation responsibilities
  that should live closer to the protocol layer.

Recommended direction:
- Introduce protocol-facing typed events instead of dict payloads.
- Make `RemoteSession` emit events such as:
  - `RemoteSessionConnected`
  - `RemoteSessionDisconnected`
  - `RemoteSessionVersionMismatch`
  - `RemotePeerMessageReceived`
- Make `MessageRouter` emit typed protocol/runtime errors such as:
  - `RemoteProtocolMessageIgnored`
  - `RemoteProtocolMessageInvalid`
- Restrict `StatusEvent` to test/backward-compatibility use only, then remove it
  from production flow.

Migration order:
- Add new protocol event dataclasses.
- Update `RemoteSession` and `MessageRouter` to emit typed events internally.
- Adapt `NvdaRemoteAppService` to consume those events directly.
- Migrate tests away from raw dict comparisons.
- Remove `StatusEvent` from production wiring once all callers are migrated.

2. Split NVDA Remote orchestration into connection/protocol/presentation units.

Files:
- `src/apps/nvda_remote/service.py`
- `src/apps/nvda_remote/use_cases/control_mode.py`
- `src/apps/nvda_remote/use_cases/input_forwarding.py`
- `src/interop/protocol/session/remote_session.py`
- `src/interop/protocol/routing/message_router.py`

Current state:
- `NvdaRemoteAppService` still owns:
  - transport binding
  - session lifecycle
  - router lifecycle
  - connection state transitions
  - control start/stop orchestration
  - clipboard push
  - tone handling
  - remote status translation
  - capture/hotkey start/stop policy
- Existing extracted use cases are helpful, but the main service is still the
  architectural center of gravity.

Why this is the second priority:
- This is now the most responsibility-dense class in the repo.
- Its remaining complexity is no longer mostly UI; it is orchestration and
  protocol glue.
- The protocol event migration above will make this split much easier and
  cleaner.

Recommended direction:
- Keep `NvdaRemoteAppService` as a UI-facing facade.
- Move orchestration into focused units such as:
  - `RemoteConnectionUseCase`
  - `RemoteProtocolEventHandler`
  - `RemoteClipboardUseCase`
  - `RemoteCapturePolicy`
- Leave key forwarding and control mode in their current use cases unless
  further splitting becomes necessary.

Migration order:
- First extract connection/disconnection and connection-state handling.
- Then extract protocol event handling from `_handle_transport_message()`,
  `_on_status()`, `_handle_connection_status()`, and `_event_from_status()`.
- Move clipboard push/tone routing only if they still do not fit after the
  larger split.
- Keep the external controller API stable for the UI.

3. Extract shared speech runtime settings policy from app entrypoints.

Files:
- `src/apps/nvda_remote/main.py`
- `src/apps/key_echo/main.py`
- `src/apps/access8graph/main.py`
- `src/application/config.py`
- `src/apps/shared/speech_settings_controller.py`

Current state:
- All three app entrypoints repeat nearly the same logic for:
  - loading selected engine
  - applying saved voice/rate/pitch/volume
  - persisting engine/voice/numeric setting changes
- This duplication now stands out because the lower-level runtime wiring has
  already been centralized.

Why this matters now:
- It is one of the few remaining cross-app duplications in startup flow.
- It mixes persistence policy into entrypoints that should mostly compose
  runtime parts.
- It makes app runtime assembly look more different than it really is.

Recommended direction:
- Introduce a shared helper or coordinator such as:
  - `SpeechRuntimeSettings`
  - `SpeechSettingsPersistence`
  - `bind_speech_settings_to_config_store(...)`
- Let app `main.py` files declare only:
  - which default engine policy they use
  - whether fallback should persist
  - which UI app/controller to instantiate

Migration order:
- Extract the duplicated `_apply_saved_speech_settings()` logic first.
- Then extract the callbacks used by `SpeechSettingsController`.
- Keep per-app default engine selection in app entrypoints unless that also
  converges naturally.

4. Bring Access8Graph up to the same service/use-case standard as the other apps.

Files:
- `src/apps/access8graph/service.py`
- `src/apps/access8graph/input.py`
- `src/apps/access8graph/flow.py`
- `src/apps/access8graph/output.py`
- `src/apps/access8graph/events.py`

Current state:
- `Access8GraphAppService` still directly owns:
  - graph file selection validation
  - flow construction/destruction
  - graph navigation lifecycle
  - error speech side effects
  - hotkey startup error-reporting policy
- `Access8GraphNavigationMode` reaches into private service methods such as
  `_start_flow()` and `_stop_flow()`.
- `Access8GraphKeyTranslator()` is created inline inside mode handling.

Why this should come after NVDA Remote, not before:
- It is less risky than NVDA Remote because it has no transport/session layer.
- Its problems are mostly local and can be fixed after the event/protocol model
  is clearer.

Recommended direction:
- Keep `Access8GraphAppService` as a thin facade.
- Extract focused units such as:
  - `GraphSelectionUseCase`
  - `GraphNavigationUseCase`
  - `GraphFlowFactory`
  - `Access8GraphCommandTranslator` protocol or stable translator boundary
- Remove direct mode-to-private-service coupling.

Migration order:
- Extract flow creation/destruction first.
- Then extract navigation lifecycle and hotkey start policy.
- Finally decide whether translator standardization should be shared with other
  apps or remain local.

5. Clarify whether `application.output.Manager` is still a real abstraction.

Files:
- `src/application/output/manager.py`
- `src/interop/protocol/routing/message_router.py`
- related tests under `tests/unit/test_output_manager.py` and
  `tests/unit/test_message_router.py`

Current state:
- `Manager` still exists and is tested, but the active runtime path mostly uses
  `Capabilities`, `QueuedService`, and direct router callbacks instead.
- The class name is generic, but its responsibilities are narrow and partly
  legacy.

Why this is lower priority:
- It is not currently blocking app/service refactors.
- The risk is conceptual confusion more than immediate architecture damage.

Recommended direction:
- Decide one of two paths:
  - keep it as a small compatibility utility and rename/document it clearly, or
  - retire it after protocol/output routing is fully settled
- Do not start with this item.

Deprioritized From v2
---------------------

1. Bootstrap extraction is no longer a next-step project.

The provider/output/app runtime layer already exists. Remaining cleanup here is
incremental, not foundational.

2. A full generic input command pipeline is not the best next move.

The codebase already has meaningful shared input pieces:
- captured event abstraction
- app pipeline result helpers
- activation policy
- mode management

There is still variation in translators and command execution, but this is not
the highest leverage refactor today. Finishing protocol events and app-service
boundaries will likely simplify any later input unification work.

3. A full multimodal output bus should still wait.

The current output organization is good enough for the present apps. The bigger
problems are service and protocol boundaries, not lack of a generalized output
bus.

Recommended Next Refactor Slice
-------------------------------

If only one refactor track should be chosen next, it should be:

1. Extract shared speech runtime settings persistence from app entrypoints.
2. Complete typed protocol events for NVDA Remote.
3. Split NVDA Remote app orchestration around those typed events.

Why this order:
- It removes one of the few remaining cross-app startup duplications first.
- It finishes work already started in `refactor2`.
- It removes the most important remaining dict-based boundary next.
- It shrinks the largest service in the repo after the protocol contract is clearer.
- It simplifies app entrypoints without reopening already-solved bootstrap work.

Concrete definition of done for the next phase:
- Shared speech settings startup/persistence logic is no longer copied across
  three `main.py` files.
- `RemoteSession` and `MessageRouter` no longer emit dict status payloads in
  normal production flow.
- `NvdaRemoteAppService` becomes a thin facade over smaller orchestration units.
- Existing UI controller APIs and behavior remain stable.

Summary
-------

Compared with `refactor2.md`, the architecture has already crossed the
"bootstrap extraction" stage and partially crossed the "typed events" stage.
The next refactor should therefore focus on completion, not reorganization for
its own sake.

The highest-value next move is to extract the duplicated speech settings
runtime policy from app entrypoints first, then finish the typed
protocol/event boundary for NVDA Remote, and then use that boundary to split
the remaining orchestration out of `NvdaRemoteAppService`. After that, bring
Access8Graph up to the same facade/use-case standard.
