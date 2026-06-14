# Keyboard Pipeline Decision Model Design

## Problem

The current keyboard handling model compresses two distinct concerns into a single final decision:

- whether the captured event should be passed through to the operating system
- whether the application handled the event and whether application-local processing should stop

Today the capture/app boundary uses a two-value decision:

- `SUPPRESS`
- `PASS_THROUGH`

This model only supports two effective combinations:

- do not send to system + app handled the event
- send to system + app did not handle the event

It cannot express the third valid combination:

- send to system + app also performs its own behavior

This gap is now concrete on Windows `Num Lock` in `key_echo`:

- the system must receive `Num Lock` so `Num Lock` state stays synchronized
- `key_echo` should still perform its own behavior for the key

## Goal

Introduce a theoretically correct keyboard pipeline model that separates:

- system-facing pass-through behavior
- app-internal handling state

The first concrete use cases are:

- `key_echo` on Windows should pass `Num Lock` through to the system
- `key_echo` should still handle the key within app logic
- `nvda_remote` on Windows should also pass `Num Lock` through to the local system
- in this phase, `nvda_remote` should not forward `Num Lock` to the remote side

## Non-Goals

- Do not introduce `AppPostProcessingStage` in this phase
- Do not extend this mechanism to `Caps Lock` or `Scroll Lock`
- Do not redesign legacy payload forwarding in this spec

## Design Summary

The design introduces two separate result types:

1. `AppKeyEventResult`
   Describes app-internal handling state.

2. `KeyboardPipelineResult`
   Describes the final pipeline output exposed to capture adapters.

This design intentionally does not preserve a final `KeyEventDecision` enum as the formal model.
The capture/app boundary should return `KeyboardPipelineResult` directly.

The pipeline is intentionally minimal in this phase:

1. `SystemPassThroughPolicyStage`
2. `ModeHandlingStage`
3. `DecisionAssembly`

No `AppPostProcessingStage` is included in this phase.

## Core Types

### `AppKeyEventResult`

This is the app-internal result model used by:

- `ModeManager`
- `ActiveKeyEventPolicy`
- app use cases such as `KeyEchoInputUseCase`

Values:

- `UNHANDLED`
  - the app layer did not handle the event
- `HANDLED_CONTINUE`
  - the app layer handled the event
  - app-internal processing should continue to the next handler/stage
- `HANDLED_STOP`
  - the app layer handled the event
  - app-internal processing should stop here

Important boundary:

- this type does not decide whether the event is sent to the operating system
- `HANDLED_CONTINUE` is purely an app-pipeline control signal
- it does not mean "send to system"
- it means "this stage handled the event, but the app pipeline should keep running"

### `KeyboardPipelineResult`

This is the final result type returned from app services to capture adapters.

Fields:

- `send_to_system: bool`
- `app_result: AppKeyEventResult`

Meaning:

- `send_to_system` is the only field that capture adapters must use to decide whether to suppress or pass the system event
- `app_result` preserves app-internal semantics for testing, logging, and future extension

## Pipeline Stages

### 1. `SystemPassThroughPolicyStage`

Responsibility:

- decide whether the captured event should be sent to the operating system

Output:

- `pass_through_to_system: bool`

This stage does not:

- return final adapter decisions
- perform app side effects

Initial policy in this phase:

- on Windows, a captured `Num Lock` event should set `pass_through_to_system=True`
- other events default to `False`

The stage may inspect `CapturedKeyEvent.native_context` to determine whether the event originated from Windows.

In this phase, this stage is a fixed pre-mode policy. It does not depend on `ModeHandlingStage` output or any `AppKeyEventResult`.
While this rule could technically be evaluated later in the pipeline, it is intentionally placed first because it represents a system-facing boundary policy rather than app-handling semantics.

### 2. `ModeHandlingStage`

Responsibility:

- run mode manager and mode/use case logic

Output:

- `AppKeyEventResult`

This stage owns app behavior such as:

- active mode exit handling
- `key_echo` speech behavior
- existing app-local key handling logic

It does not decide whether the system should receive the event.

### 3. `DecisionAssembly`

Responsibility:

- combine:
  - `pass_through_to_system`
  - final `AppKeyEventResult`
- produce `KeyboardPipelineResult`

Assembly rules:

- `send_to_system=False` + `UNHANDLED`
  - `KeyboardPipelineResult(send_to_system=False, app_result=UNHANDLED)`
- `send_to_system=False` + `HANDLED_CONTINUE`
  - `KeyboardPipelineResult(send_to_system=False, app_result=HANDLED_CONTINUE)`
- `send_to_system=False` + `HANDLED_STOP`
  - `KeyboardPipelineResult(send_to_system=False, app_result=HANDLED_STOP)`
- `send_to_system=True` + `UNHANDLED`
  - `KeyboardPipelineResult(send_to_system=True, app_result=UNHANDLED)`
- `send_to_system=True` + `HANDLED_CONTINUE`
  - `KeyboardPipelineResult(send_to_system=True, app_result=HANDLED_CONTINUE)`
- `send_to_system=True` + `HANDLED_STOP`
  - `KeyboardPipelineResult(send_to_system=True, app_result=HANDLED_STOP)`

The important point is that the pipeline no longer compresses these states into a lossy enum.

## Data Flow

The resulting keyboard flow becomes:

1. capture adapter emits `CapturedKeyEvent`
2. app service runs `SystemPassThroughPolicyStage`
3. app service runs `ModeHandlingStage`
4. app service assembles `KeyboardPipelineResult`
5. capture adapter uses only `send_to_system` to suppress or pass the system event

This makes the layering explicit:

- system pass-through is a boundary concern
- handling semantics are an app concern

## `key_echo` Application of the Model

### General keys in echo mode

- pass-through policy: `False`
- echo mode handles the key and speaks it
- mode handling returns `HANDLED_STOP`
- final result:
  - `send_to_system=False`
  - `app_result=HANDLED_STOP`

Effect:

- the system does not receive the key
- app behavior runs as before

### Windows `Num Lock` in echo mode

- pass-through policy: `True`
- echo mode still performs its key behavior
- `KeyEchoInputUseCase` returns `HANDLED_CONTINUE`
- final result:
  - `send_to_system=True`
  - `app_result=HANDLED_CONTINUE`

Effect:

- Windows receives `Num Lock`, so system `Num Lock` state stays synchronized
- `key_echo` still performs its own behavior for the key

This is the first explicit case of the previously missing combination:

- send to system
- app also handles the event

## `nvda_remote` Scope in This Phase

`nvda_remote` adopts the new pipeline result model and the shared Windows `Num Lock` pass-through policy in this phase.

This means:

- its service layer adapts to the new pipeline result types
- Windows `Num Lock` is passed through to the local system before remote forwarding logic
- `Num Lock` does not flow into the existing remote forwarding path in this phase
- all other existing controlling/forwarding behavior should remain unchanged

## Affected Components

- `src/adapters/inputs/base.py`
  - listener return contract changes from the current single final decision model
- `src/application/input/`
  - add `AppKeyEventResult`
  - add `KeyboardPipelineResult`
  - add keyboard pipeline assembly logic
- `src/apps/shared/mode_manager.py`
  - return `AppKeyEventResult`
- `src/application/input/active_key_policy.py`
  - return `AppKeyEventResult`
- `src/apps/key_echo/use_cases/echo_input.py`
  - general keys return `HANDLED_STOP`
  - Windows `Num Lock` in echo mode returns `HANDLED_CONTINUE`
- `src/apps/key_echo/service.py`
  - compose and run the keyboard pipeline
- `src/apps/nvda_remote/service.py`
  - adapt to the new result model
  - apply shared Windows `Num Lock` pass-through behavior
- `src/adapters/windows/keyboard_hook.py`
  - use `send_to_system`
- `src/adapters/macos/keyboard_hook.py`
  - adapt listener return type and use `send_to_system`

## Migration Plan

1. introduce new core result types:
   - `AppKeyEventResult`
   - `KeyboardPipelineResult`
2. update capture listener interfaces to return `KeyboardPipelineResult`
3. update Windows and macOS adapters to read only `send_to_system`
4. update `ModeManager` and `ActiveKeyEventPolicy` to return `AppKeyEventResult`
5. update `key_echo` use cases and service to use the pipeline
6. adapt `nvda_remote` to the new interfaces and apply shared Windows `Num Lock` pass-through before forwarding

## Testing Strategy

### Unit tests

- `SystemPassThroughPolicyStage`
  - Windows `Num Lock` -> `send_to_system=True`
  - non-Windows or non-`Num Lock` -> `False`
- `ModeManager`
  - no active mode -> `UNHANDLED`
  - exit key -> `HANDLED_STOP`
- `KeyEchoInputUseCase`
  - general key -> `HANDLED_STOP`
  - Windows `Num Lock` in echo mode -> `HANDLED_CONTINUE`
- decision assembly
  - preserves both `send_to_system` and `app_result` without lossy compression

### Adapter tests

- Windows and macOS keyboard hooks use only `send_to_system`
  - `True` -> pass through
  - `False` -> suppress

### App service tests

- `key_echo`
  - general key -> app handles, system does not receive
  - Windows `Num Lock` -> app handles, system receives
- `nvda_remote`
  - Windows `Num Lock` -> local system receives it, remote forwarding does not
  - current controlling behavior for other keys should not regress

## Rationale

The previous design failed because it attempted to represent:

- system pass-through behavior
- app handling semantics

with a single compressed decision.

This spec fixes that by:

- making system pass-through an explicit boundary concern
- making app handling state an explicit app concern
- preserving both dimensions in the final pipeline result

That produces a model that is more correct, easier to reason about, and easier to extend in later phases.
