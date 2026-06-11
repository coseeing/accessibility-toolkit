# App Service Splitting Design

## Purpose

Reduce the complexity of `NvdaRemoteAppService` and `KeyEchoAppService` by splitting app-layer responsibilities into focused use-case objects while preserving current behavior and keeping the wx UI integration stable.

This is the next refactor phase after bootstrap extraction. The goal is not to redesign the full architecture. The goal is to make app-layer responsibilities smaller, clearer, and easier to test without changing the existing UI contract more than necessary.

## Scope

| In scope | Out of scope |
|----------|-------------|
| Split app-layer responsibilities into focused use cases | Redesign output architecture |
| Introduce thin app facades for `nvda_remote` and `key_echo` | Replace dict/status flow with typed events |
| Preserve existing UI-facing controller surface where practical | Replace wx UI dependencies with narrower presenter interfaces |
| Add direct unit tests for new use-case classes | Introduce shared base controller or inheritance hierarchy |
| Align both apps to the same app-layer pattern | Refactor transport/session/protocol architecture |

## Design Goals

1. Reduce the amount of business logic inside the current app service classes.
2. Apply the same app-layer pattern to both `nvda_remote` and `key_echo`.
3. Preserve current runtime behavior and UI behavior.
4. Keep the dependency flow simple and explicit.
5. Improve unit-testability by moving rules into smaller objects.

## Current Problem

`src/apps/nvda_remote/service.py` currently mixes multiple responsibilities:

- connection orchestration
- control mode lifecycle
- input forwarding rules
- transport event handling
- clipboard-related behavior
- speech backend settings behavior
- UI-oriented status dispatch

`src/apps/key_echo/service.py` is much smaller, but it still combines app orchestration and input/output behavior in one app-specific service class.

The result is an uneven app-layer shape:

- one large service with too many reasons to change
- one small service that does not validate a reusable pattern

The next phase should make both apps follow the same structural pattern without forcing an early shared base class.

## Recommended Approach

Use a **facade plus focused use cases** pattern.

Each app gets:

- one thin app facade that remains the UI-facing controller surface
- several focused use-case objects that hold business logic

Shared structure is achieved through pattern alignment, not inheritance.

### Why this approach

- Safer than immediately changing UI dependencies
- More meaningful than a minimal extraction that leaves most complexity in place
- Avoids premature abstraction into a shared base controller
- Creates a clean foundation for later output/event/UI refactors

## Target Structure

### `nvda_remote`

Recommended app-layer split:

- `NvdaRemoteAppFacade`
- `ConnectionUseCase`
- `ControlModeUseCase`
- `InputForwardingUseCase`
- `SpeechSettingsUseCase`

Possible file organization:

```text
src/apps/nvda_remote/
  facade.py
  service.py          # compatibility re-export or transitional wrapper if needed
  use_cases/
    __init__.py
    connection.py
    control_mode.py
    input_forwarding.py
    speech_settings.py
```

### `key_echo`

Recommended app-layer split:

- `KeyEchoAppFacade`
- `EchoControlUseCase`
- `EchoInputUseCase`
- `SpeechSettingsUseCase`

Possible file organization:

```text
src/apps/key_echo/
  facade.py
  service.py          # compatibility re-export or transitional wrapper if needed
  use_cases/
    __init__.py
    echo_control.py
    echo_input.py
    speech_settings.py
```

## Responsibility Split

### `NvdaRemoteAppFacade`

Responsibilities:

- expose the UI-facing controller surface
- coordinate use cases when one UI action crosses multiple responsibilities
- preserve compatibility for existing UI wiring

Non-responsibilities:

- direct business-rule ownership
- low-level transport logic
- key forwarding logic details
- speech settings rule implementation

### `ConnectionUseCase`

Responsibilities:

- connect
- disconnect
- update connection-related state
- coordinate transport lifecycle for connection actions

Non-responsibilities:

- key forwarding rules
- control-mode toggle rules
- speech backend configuration

### `ControlModeUseCase`

Responsibilities:

- start control
- stop control
- enforce state preconditions for entering/leaving control mode
- coordinate hotkey activation/deactivation rules where they belong to control mode

Non-responsibilities:

- transport connect/disconnect
- raw key-event forwarding decisions

### `InputForwardingUseCase`

Responsibilities:

- handle input events
- decide pass-through vs suppress
- apply local stop-hotkey business rules
- forward remote key messages through the appropriate collaborator

Non-responsibilities:

- connection establishment
- speech backend settings
- UI status formatting

### `SpeechSettingsUseCase`

Responsibilities:

- switch backend
- expose selected backend
- set and query voice/rate/pitch/volume
- handle backend-setting rules in one place

Non-responsibilities:

- speech playback implementation
- queue/scheduler lifecycle

### `KeyEchoAppFacade`

Responsibilities:

- expose the current UI-facing controller surface
- coordinate echo control and speech settings use cases

### `EchoControlUseCase`

Responsibilities:

- start echo
- stop echo
- coordinate input-service lifecycle actions needed for echo mode

### `EchoInputUseCase`

Responsibilities:

- convert input events into output actions
- apply echo-specific input rules such as stop-on-escape

### `SpeechSettingsUseCase` in `key_echo`

`key_echo` should use the same pattern shape as `nvda_remote`, even if the behavior is simpler. The two apps do not need to share one implementation immediately, but they should expose the same conceptual boundary.

## Dependency Direction

Required dependency flow:

```text
UI -> app facade -> use cases -> existing lower-level services/protocols
```

Rules:

1. UI talks to the facade, not directly to individual use cases.
2. The facade composes use cases, but should not absorb their logic.
3. Each use case depends only on the collaborators it actually needs.
4. Use cases should not casually depend on each other; cross-use-case coordination should happen through the facade unless a dependency is clearly one-way and stable.
5. No new platform branching belongs in facades or use cases.

## Collaboration Model

The design intentionally avoids introducing a shared base class such as `BaseAppService` or `BaseAppFacade`.

Reason:

- `nvda_remote` and `key_echo` are structurally similar, but their business rules are still meaningfully different.
- A shared parent at this stage would likely capture accidental similarities and force remote-specific behavior into common code.

The shared asset in this phase is the pattern:

- thin facade
- focused use cases
- explicit dependency direction
- direct unit tests per use case

## Backward Compatibility Strategy

This phase should preserve the current UI-facing behavior.

Preferred strategy:

- keep the object passed into wx UI code functionally compatible with the current controller surface
- migrate implementation behind that surface first
- defer any UI interface narrowing to a later phase

If necessary, `service.py` may temporarily remain as:

- the facade implementation itself, or
- a compatibility wrapper/re-export around `facade.py`

The important constraint is behavioral continuity, not file naming purity.

## Error Handling

Error handling should be clarified, not broadened.

Rules:

1. Use cases should own business-level failure decisions.
2. Facades should translate or relay failures into the same UI-observable behavior that exists today.
3. Infrastructure exceptions should not be caught ad hoc across the facade; they should be handled at the appropriate use-case boundary where possible.
4. This phase should not introduce a new global error/event framework.

Examples:

- attempting to start control while disconnected remains a control-mode rule
- attempting to send forwarded input while not in the correct state remains an input-forwarding rule
- switching to an invalid backend remains a speech-settings rule

## Testing Strategy

This phase must strengthen tests at the app-layer boundary.

### Keep existing regression coverage

Existing tests that validate current app behavior should remain and keep passing.

Examples:

- `tests/unit/test_nvda_remote_app_service.py`
- `tests/unit/test_key_echo_app_service.py`
- relevant wx composition tests

### Add direct use-case tests

Each new use-case class should have focused unit tests for its own rules.

Examples:

- connection state transitions
- start/stop control preconditions
- key forwarding suppression rules
- stop-on-escape behavior
- speech backend selection and configuration behavior

### Add facade composition tests

Add tests that verify:

- the facade wires use cases together correctly
- facade methods delegate to the correct use case
- facade does not re-implement business logic already covered by use-case tests

## Migration Constraints

This phase must not expand into adjacent refactors.

Specifically, do not do these as part of this design:

- redesign output channels around tone/wave/braille
- replace dict-based status payloads with typed events
- redesign the UI to depend on narrower interfaces
- rewrite transport/session/message-router responsibilities
- introduce a shared base app service/facade hierarchy

## Success Criteria

This phase is complete when all of the following are true:

1. `NvdaRemoteAppService` is replaced or reduced to a thin facade role.
2. `KeyEchoAppService` follows the same facade/use-case structural pattern.
3. Core app business rules are moved into focused use-case classes.
4. Existing UI-facing behavior remains compatible.
5. Existing regression tests continue to pass.
6. New use-case unit tests exist for the extracted responsibilities.
7. No new architecture phase is pulled into this change set.

## Future Path

This phase prepares later work without taking it on now.

After this design is implemented, the next likely refactor options become clearer:

- narrow UI-facing interfaces
- introduce typed domain events/state models
- redesign multimodal output architecture

Those later phases should build on smaller app-layer boundaries rather than trying to reshape the app layer and output/event architecture at the same time.
