# Speech Runtime Settings And NVDA Remote Protocol Boundary Design

## Goal

Reduce startup duplication and finish the remaining typed boundary work in
NVDA Remote by doing three things in order:

1. extract the shared speech runtime settings persistence from app entrypoints
2. replace NVDA Remote's dict-based session/router status flow with typed events
3. split NVDA Remote orchestration around those typed events so the app service
   becomes a thin facade

This is a single design with three ordered milestones. Each milestone should be
reviewable and mergeable on its own, but the later milestones depend on the
earlier ones.

## Current State

The codebase has already moved past the earlier bootstrap-extraction stage:

- `bootstrap/platform.py`, `bootstrap/output.py`, and `bootstrap/app_runtime.py`
  now centralize the shared runtime wiring
- `application/events.py` already contains shared typed application events
- each app package already has its own app-domain event module
- NVDA Remote has some focused use cases already extracted, especially control
  and input-forwarding behavior

The remaining friction is concentrated in two places:

- all three app entrypoints still duplicate the same speech settings startup and
  persistence flow
- NVDA Remote still uses dict-shaped transport/session/router status payloads as
  a transitional event boundary

## Non-Goals

This design does not include the following work:

- changing the config file format or renaming persisted speech settings keys
- redesigning the output architecture into a full channel bus
- changing Access8Graph startup, navigation, or event handling
- introducing a general dependency injection container
- rewriting UI layouts or adding new UI features unrelated to these milestones

Access8Graph is intentionally out of scope even though it appears in
`refactor3.md` as a later follow-up. This design only covers the first three
priority items from that review.

## Milestone Order

The milestone order matters:

1. shared speech runtime settings persistence
2. typed NVDA Remote protocol events
3. NVDA Remote orchestration split around typed events

M2 depends on M1 only indirectly, but M3 depends on M2 in practice because the
orchestration split becomes simpler once the protocol/event boundary is typed.

---

## Milestone 1: Shared Speech Runtime Settings Persistence

### Intent

Remove the repeated speech settings startup/persistence code from
`nvda_remote`, `key_echo`, and `access8graph` entrypoints without changing the
actual config schema or per-app speech behavior.

### Problem Statement

Each app entrypoint currently repeats the same pattern:

- load the configured speech engine id
- apply saved voice/rate/pitch/volume values to the current speech engine
- persist speech engine changes
- persist voice and numeric setting changes through `SpeechSettingsController`

The logic is small, but it is repeated three times and makes the startup flow
look more different than it really is.

### Design

Create one small shared speech runtime helper in `src/apps/shared/` that owns
the duplicated policy for loading and applying saved speech settings.

Use a small coordinator object named `SpeechRuntimeSettingsCoordinator` rather
than spreading the logic across several free functions.

The helper should cover these responsibilities:

- use the app-provided startup engine selection policy
- apply saved speech settings to a given speech service for a specific engine id
- produce the engine-change persistence behavior used by the app entrypoints

The helper should not:

- know about UI classes
- know about app-specific controllers beyond the shared `SpeechSettingsController`
- change the config schema
- alter how `SpeechSettingsController` persists voice/rate/pitch/volume values

### Proposed File Structure

- Create: `src/apps/shared/speech_runtime_settings.py`
- Modify: `src/apps/nvda_remote/main.py`
- Modify: `src/apps/key_echo/main.py`
- Modify: `src/apps/access8graph/main.py`
- Modify: `tests/unit/test_bootstrap_app_runtime.py` or existing runtime tests that
  already verify app startup composition
- Create: `tests/unit/test_speech_runtime_settings.py`

### Shared Helper Behavior

The shared helper should encapsulate the startup policy currently duplicated in
the three entrypoints:

- `SpeechEngineConfigStore.load_engine_id(default_engine_id=...)`
- loading saved voice/rate/pitch/volume for the selected engine
- validating that the saved voice exists in the current engine's `list_voices()`
- only applying numeric settings supported by the engine
- building the engine-change callback that persists the selected engine and
  reapplies saved settings
- preserving the current startup engine selection behavior per app, including
  app-specific fixed-engine cases such as `key_echo`

The helper should be called from app startup code rather than from the UI layer.

### App Entrypoint Responsibilities After M1

Each `main.py` file should still:

- choose the app-specific default engine behavior
- construct the app service
- pass the shared speech settings callbacks into app-service construction
- build the UI app and keyboard input service

Each `main.py` file should no longer:

- define a private `_apply_saved_speech_settings()` copy
- duplicate the save-and-reapply logic for engine changes
- manually replicate the same load/apply/persist flow across all three apps

### Validation Criteria

M1 is complete when all of the following are true:

- the duplicated speech settings startup logic exists in one shared helper only
- each app entrypoint is visibly thinner
- the selected engine and its settings still restore on startup
- engine changes still persist and reapply saved settings
- existing startup/runtime tests continue to pass

---

## Milestone 2: Typed NVDA Remote Protocol Events

### Intent

Replace the dict-based status flow used by `RemoteSession` and `MessageRouter`
with typed protocol events so NVDA Remote no longer depends on a transitional
JSON-shaped status contract.

### Problem Statement

NVDA Remote currently has a half-typed event boundary:

- `RemoteSession` emits dict payloads for connection state
- `MessageRouter` emits dict payloads for protocol messages and invalid input
- `NvdaRemoteAppService` converts those dicts through `StatusEvent.from_payload()`

That makes the protocol contract implicit and forces the app service to remain
responsible for event parsing.

### Design

Introduce a typed protocol event module under `src/interop/protocol/` that both
`RemoteSession` and `MessageRouter` can use. The protocol layer should emit
typed dataclasses directly instead of dict-shaped status payloads.

The event model should cover the current session/router cases. Use dataclass
names that mirror the existing responsibilities, such as:

- `RemoteSessionConnected`
- `RemoteSessionDisconnected`
- `RemoteSessionVersionMismatch`
- `RemotePeerMessageReceived`
- `RemoteProtocolMessageIgnored`
- `RemoteProtocolMessageInvalid`

### Proposed File Structure

- Create: `src/interop/protocol/events.py`
- Modify: `src/interop/protocol/session/remote_session.py`
- Modify: `src/interop/protocol/routing/message_router.py`
- Modify: `src/apps/nvda_remote/service.py`
- Modify: `tests/unit/test_message_router.py`
- Create: `tests/unit/test_remote_session.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`
- Modify: `tests/unit/test_application_events.py` only if it still exercises the
  transitional `StatusEvent` helper

RemoteSession coverage that currently lives in `tests/unit/test_message_router.py`
should move into the new `tests/unit/test_remote_session.py` so the router and
session contracts can evolve independently.

### Boundary Rules

The protocol layer should be responsible for:

- deciding whether a payload is a session event, a remote peer message, or an
  invalid protocol message
- emitting typed protocol events

The app layer should be responsible for:

- mapping protocol events to existing app-domain events where needed
- updating app state
- deciding which events should be surfaced to the UI

The protocol layer should not:

- know about wx
- know about app-specific UI state
- know about `SpeechSettingsController`
- convert protocol events back into dicts

### Transitional Compatibility

`StatusEvent` may remain temporarily as a compatibility helper during the
migration, but it should no longer be part of the production path once this
milestone is complete.

### Validation Criteria

M2 is complete when all of the following are true:

- `RemoteSession` and `MessageRouter` emit typed events instead of dict payloads
- `NvdaRemoteAppService` no longer depends on `StatusEvent.from_payload()` for
  normal protocol flow
- the remaining app-level event mapping is explicit and typed
- message-router and session tests assert typed event behavior instead of raw
  dict shape

---

## Milestone 3: NVDA Remote Orchestration Split

### Intent

Use the typed protocol events from M2 to separate NVDA Remote's orchestration
concerns into smaller units, leaving `NvdaRemoteAppService` as a thin facade
for the UI and runtime wiring.

### Problem Statement

`NvdaRemoteAppService` still owns too many responsibilities:

- transport binding
- session lifecycle
- router lifecycle
- connection state transitions
- control start/stop orchestration
- remote status translation
- capture and hotkey policy
- clipboard push
- tone handling

Even after the existing use cases, the service is still the center of gravity.

### Design

Split the remaining orchestration into focused units that communicate through
typed events and small callback interfaces.

The service should keep only the UI-facing orchestration surface and delegate
the rest.

The most important extracted responsibilities are:

- connection/disconnection orchestration
- protocol event handling and translation into app events
- status presentation / dispatch to the UI boundary

Key forwarding and control mode can stay in their current use cases unless they
need further splitting after the protocol boundary is typed.

### Proposed File Structure

- Modify: `src/apps/nvda_remote/service.py`
- Create: `src/apps/nvda_remote/use_cases/connection.py`
- Create: `src/apps/nvda_remote/use_cases/protocol_events.py`
- Create: `src/apps/nvda_remote/use_cases/status_presentation.py`
- Reuse: `src/apps/nvda_remote/use_cases/control_mode.py`
- Reuse: `src/apps/nvda_remote/use_cases/input_forwarding.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`
- Modify: `tests/unit/test_nvda_remote_use_cases.py`
- Create or update: additional focused tests for the new use-case modules

### Service Boundary After M3

`NvdaRemoteAppService` should still expose the controller methods the UI uses,
but it should stop being the place where protocol payload parsing and
connection-state orchestration live.

It should primarily:

- wire together the smaller use cases
- expose the app controller API to the UI
- forward typed events to the UI listener
- keep main-thread dispatch glue in one place

### Validation Criteria

M3 is complete when all of the following are true:

- `NvdaRemoteAppService` is visibly thinner than before
- connection and protocol event handling have dedicated units
- the service no longer owns dict parsing or dict-shaped status translation
- UI behavior remains unchanged from the user's perspective
- existing NVDA Remote tests still pass with the new event boundary

---

## Cross-Cutting Testing Strategy

The implementation should use small, focused tests for each milestone.

### M1 Tests

- verify the shared helper applies saved speech settings to the current engine
- verify engine changes persist and reapply saved settings
- verify each app entrypoint still builds a runtime successfully

### M2 Tests

- verify `RemoteSession` emits typed session events
- verify `MessageRouter` emits typed protocol events for valid and invalid input
- verify `NvdaRemoteAppService` consumes the typed events without relying on
  dict payload shape

### M3 Tests

- verify the new connection/protocol/status units handle the same scenarios the
  service handled before
- verify the UI-facing app service API remains stable
- verify the split does not change existing control or forwarding behavior

## Definition Of Done

This design is complete when:

- speech runtime settings persistence is no longer duplicated in the three app
  entrypoints
- NVDA Remote protocol/session/router flow is typed end-to-end
- NVDA Remote orchestration is split into smaller units around the typed
  boundary
- the existing app-facing behavior remains stable
- the resulting code still follows the repo's current source layout and test
  style
