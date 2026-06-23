# Runtime Providers And Typed Events Design

## Goal

Restructure runtime composition and app/UI event boundaries so the codebase can
support additional apps, platforms, and UI flows without duplicating bootstrap
logic or relying on ad hoc status dictionaries.

This design covers two sequential milestones:

1. `M1`: runtime provider extraction
2. `M2`: typed event migration across all three apps

The milestones are intended to be reviewed and merged separately, but `M2`
explicitly builds on the structure introduced in `M1`.

## Current State

The codebase is in a better state than before the output package reorganization:

- output concerns are now grouped under `application.output`
- speech backend selection is isolated under `application.output.speech`
- app runtimes use more consistent naming
- some app-specific behavior already lives under `apps/*/use_cases/`

The main architectural pressure is now in two places:

1. runtime composition is still duplicated across `apps/*/main.py`
2. app/UI status flow still depends on loosely structured dictionaries

`bootstrap/platform.py` also remains overloaded. It currently combines:

- platform detection
- lazy import resolution
- null fallback implementations
- clipboard and tone factory behavior
- speech backend selection

On the app side, `NvdaRemoteAppService`, `KeyEchoAppService`, and
`Access8GraphAppService` still expose UI-facing controller methods while also
owning lower-level orchestration concerns. That makes event and status flow hard
to evolve safely.

## Non-Goals

This design does not include the following work:

- splitting `NvdaRemoteAppService` into multiple focused use-case classes
- redesigning output into a full channel-based `OutputBus`
- replacing remote protocol payloads with typed wire models
- rewriting UI classes or wx structure beyond what is necessary for typed event
  consumption
- introducing a full dependency injection container or registry framework

These remain valid future refactors, but they are not part of `M1` or `M2`.

## Milestone 1: Runtime Provider Extraction

### Intent

Remove duplicated runtime assembly from app entrypoints and establish a shared
bootstrap seam for platform and output capability wiring.

### Design Principles

- keep app `main.py` files thin
- move shared wiring into `bootstrap/`
- use lightweight provider objects plus builder functions
- do not introduce a general-purpose container
- preserve current behavior and runtime shapes unless there is a strong reason
  to normalize them

### Target Structure

The expected direction inside `bootstrap/` is:

- `bootstrap/platform.py`
  - platform capability provider construction
  - provider-facing fallback logic
- `bootstrap/output.py`
  - scheduler, speech, speaker, tone, and capability assembly
- `bootstrap/app_runtime.py`
  - shared runtime wiring helpers for app entrypoints

The exact file names can vary slightly if the surrounding code suggests a
better local naming pattern, but responsibilities should remain separated along
those boundaries.

### Core Types

`M1` should introduce a small number of explicit bootstrap-side types.

Suggested types:

- `PlatformProvider`
  - answers which platform-backed services are available
  - owns creation of input capture, hotkey capture, clipboard, and tone output
- `OutputServices`
  - bundles runtime output pieces:
    - `scheduler`
    - `speech`
    - `speaker`
    - `capabilities`
- `AppRuntimeParts`
  - optional helper bundle for common runtime wiring before each app wraps it in
    its own runtime dataclass

These types should be small and concrete. They are not intended to become
general framework abstractions.

### Runtime Builder Shape

The composition flow should look like this:

1. app `main.py` asks bootstrap for platform-backed services
2. app `main.py` asks bootstrap to assemble output services
3. app `main.py` supplies app-specific dependencies
4. app `main.py` constructs the app service and UI shell

That means app `main.py` still decides:

- which app service class to instantiate
- which UI app class to instantiate
- which default hotkey usage to use
- which app-specific dependencies exist, such as transport or config store

But app `main.py` should stop directly assembling all shared runtime pieces.

### Expected Result In App Entrypoints

After `M1`, `apps/*/main.py` should mostly read as:

- get platform-backed services
- get output services
- create app-specific service
- create keyboard input service
- create UI app
- return runtime dataclass

The detailed platform and output assembly should no longer be spread across all
three app entrypoints.

### Validation Criteria For M1

`M1` is complete when all of the following are true:

- the three app entrypoints are visibly thinner
- shared runtime wiring lives under `bootstrap/`
- platform capability selection is no longer open-coded in each app main module
- existing runtime-focused tests still verify app startup composition
- no app service responsibility split is required to finish the milestone

## Milestone 2: Typed Event Boundary

### Intent

Replace dictionary-based UI-facing status output with typed events across all
three apps.

### Scope Decision

`M2` applies to all three apps together:

- `nvda_remote`
- `key_echo`
- `access8graph`

This is not a single-app pilot. The point of the milestone is to establish one
consistent application/UI event boundary across the repo.

### Shared Event Location

Shared events must be defined in:

- `src/application/events.py`

This file is the canonical location for application-level shared event models
that can be consumed by multiple apps and shared UI/controller code.

### App-Specific Event Location

App-domain events should live inside each app package when they are not shared.

Examples:

- `src/apps/nvda_remote/events.py`
- `src/apps/key_echo/events.py`
- `src/apps/access8graph/events.py`

This separation prevents `application/events.py` from becoming a dumping ground
for remote-specific or graph-specific semantics.

### Event Layering Rules

Shared events in `application/events.py` should describe runtime or capability
state that is meaningful across apps.

Examples:

- `ErrorRaised`
- `SpeechBackendChanged`
- `InputCaptureChanged`
- `HotkeyCaptureChanged`
- `ClipboardAvailabilityChanged`

App-specific events should describe app-domain meaning.

Examples:

- NVDA Remote:
  - `RemoteConnectionChanged`
  - `RemoteControlChanged`
  - `RemoteTransportDisconnected`
- Access8Graph:
  - graph selection or navigation lifecycle events if needed
- Key Echo:
  - mode-specific state events if needed

### Boundary Definition

The typed event migration should first target the boundary between:

- app services
- UI-facing controllers or listeners

This means:

- app services should emit typed events internally
- UI controllers should consume typed events
- dict-based status payloads should stop being the primary contract

If compatibility is temporarily needed, the repo may use a thin adapter that
converts typed events into the legacy dict shape. That adapter is transitional,
not a new long-term public API.

### Relationship To Existing `StatusEvent`

`application/events.py` currently contains `StatusEvent`, which is essentially a
typed wrapper around a generic dict shape.

`M2` should move away from that model.

The target is not:

- one generic `StatusEvent` plus free-form payloads

The target is:

- multiple explicit event dataclasses with stable fields and names

The old wrapper may remain briefly for migration support, but it should not be
the end state of the milestone.

### Migration Strategy For M2

The expected sequence is:

1. define shared event dataclasses in `application/events.py`
2. define app-domain events under each app package as needed
3. update app services to emit typed events
4. update shared UI/controller code to accept typed events
5. update app-specific UI consumers to accept typed events
6. remove dict-first status flow once all three apps are migrated

### Validation Criteria For M2

`M2` is complete when all of the following are true:

- all three app services use typed events as their primary UI-facing status
  contract
- shared event definitions live in `application/events.py`
- app-domain events live under each app package when needed
- UI/controller code no longer relies on raw dict key conventions as the
  primary contract
- any compatibility adapter is clearly transitional and thin

## Why The Order Matters

The milestone order should remain:

1. `M1`: runtime provider extraction
2. `M2`: typed event boundary

Reason:

- `M1` reduces repeated wiring and stabilizes runtime assembly seams
- `M2` then operates on cleaner app/service/UI boundaries
- reversing the order would cause event work to be spread across entrypoints
  that are still structurally noisy

`M2` does not need to be completely independent from `M1`, but it should not
require additional major bootstrap churn after `M1` lands.

## Testing Strategy

### M1

Focus on runtime assembly and startup composition tests:

- app runtime build tests
- bootstrap platform tests
- app main tests that assert the correct shared pieces are wired together

Behavior should remain unchanged. Most tests should be adapted rather than
rewritten from scratch.

### M2

Focus on event contract and UI boundary tests:

- app service event emission tests
- controller or listener tests that consume typed events
- compatibility adapter tests if an adapter exists during migration

The goal is to verify stable event contracts rather than only indirect UI state
effects.

## Risks

### M1 Risks

- over-abstracting too early and creating a framework instead of a helper layer
- changing runtime wiring shape too much and forcing unnecessary app churn
- mixing provider extraction with app-service decomposition

### M2 Risks

- inventing one giant event union that becomes another weak abstraction
- mixing shared and app-specific events in the same module
- leaving the repo in a long-lived hybrid state where dict status and typed
  events both act as primary APIs

## Recommended Next Step

The next concrete step after this design is to write an implementation plan for
`M1` only.

That keeps the first execution scope tight, creates the bootstrap seam needed by
`M2`, and avoids turning both milestones into one oversized implementation
batch.
