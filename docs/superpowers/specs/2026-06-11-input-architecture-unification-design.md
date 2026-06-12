# Input Architecture Unification Design

## Summary

This spec defines the next refactor phase after app-service splitting: unify the keyboard and hotkey input architecture used by `nvda_remote` and `key_echo`.

The goal is to standardize both apps on the same lifecycle model:

- `idle`: run `HotkeyCapture` only
- `active`: stop `HotkeyCapture` and run the full keyboard `InputCapture` pipeline

This phase does **not** redesign output architecture, add typed domain events, or generalize to new input device classes beyond keyboard and hotkey handling.

## Goals

1. Unify `nvda_remote` and `key_echo` around one input lifecycle model.
2. Extract shared input lifecycle and transition policy logic out of app facades.
3. Keep app-specific business handling separate from shared input state-machine logic.
4. Ensure active and idle capture modes do not overlap.
5. Preserve current UI-facing controller behavior.

## Non-Goals

- Redesign output architecture
- Introduce typed event/state flow across the app
- Generalize to gamepads, braille keyboards, media keys, or other future devices
- Remove platform-specific `HotkeyCapture` implementations from `nvda_remote`
- Collapse all platform capture mechanisms into one physical implementation

## Problem Statement

The current apps use similar concepts but different input lifecycle policies:

- `nvda_remote`
  - idle/connected: uses `HotkeyCapture`
  - active/controlling: stops `HotkeyCapture`, uses keyboard `InputCapture`
- `key_echo`
  - currently mixes state-transition hotkeys and active key handling through a keyboard-driven path
  - recent fixes proved that hotkey reachability and capture lifecycle can easily become tangled

As a result:

- capture lifecycle rules are not expressed as one reusable model
- state-transition hotkeys are handled differently across apps
- facades still carry too much input orchestration knowledge
- tests cover app behavior, but the shared lifecycle contract is not yet explicit

## Desired Model

Both apps should adopt the same input lifecycle:

### Idle

- `HotkeyCapture` is running
- keyboard `InputCapture` is stopped
- only state-transition hotkeys needed to enter active mode are listened for

### Active

- `HotkeyCapture` is stopped
- keyboard `InputCapture` is running
- general keyboard events are handled through the app's active keyboard pipeline
- active-state exit keys are handled inside the active keyboard pipeline, not by a parallel hotkey capture

## App-Level Behavior

### `nvda_remote`

- idle:
  - `F11` enters control mode
- active:
  - `F11` exits control mode
  - other keys follow remote input forwarding rules

### `key_echo`

- idle:
  - `Enter` enters echo mode
- active:
  - `Escape` exits echo mode
  - other keys follow echo playback rules

## Architectural Direction

Shared code should express the input state machine. App-specific code should supply:

- idle-enter hotkey mapping
- active-exit key rule
- active-state key handling behavior

The shared layer should not know what "control mode" or "echo mode" means beyond generic active/inactive transitions.

## Proposed Components

### `InputActivationUseCase`

Shared use case responsible for capture lifecycle transitions.

Responsibilities:

- enter active mode
- exit active mode
- keep `HotkeyCapture` and keyboard `InputCapture` mutually exclusive
- recover cleanly from partial start/stop failures
- expose the current activation state

Rules:

- `enter_active()`
  - stop `HotkeyCapture` if running
  - start keyboard `InputCapture` if not running
  - only mark active after keyboard capture is running
- `exit_active()`
  - stop keyboard `InputCapture` if running
  - start `HotkeyCapture` if needed
  - only mark idle after the transition is restored safely

Failure behavior:

- if keyboard capture fails to start while entering active:
  - restore idle hotkey capture when possible
  - do not leave state marked active
  - report an error through the caller-provided error callback
- if hotkey capture fails to restart while exiting active:
  - report an error
  - avoid claiming idle success unless the capture state matches the model

### `StateTransitionHotkeyPolicy`

Shared policy for idle-state hotkeys that activate the app.

Responsibilities:

- accept app-provided hotkey mapping
- match idle hotkey events to transition actions
- remain ignorant of app business behavior

Examples:

- `nvda_remote`: `F11 -> enter_active`
- `key_echo`: `Enter -> enter_active`

This policy only applies while idle and only through `HotkeyCapture`.

### `ActiveKeyEventPolicy`

Shared active-state routing policy with app-provided handlers.

Responsibilities:

- process keyboard events only while active
- identify the app's active-state exit key
- route non-exit keys to app-specific active handlers

Examples:

- `nvda_remote`
  - exit key: `F11`
  - non-exit behavior: remote key forwarding
- `key_echo`
  - exit key: `Escape`
  - non-exit behavior: speak/echo key events

This policy should return `KeyEventDecision` values and own the exit-key routing decision for the active keyboard path.

### App-Specific Active Handlers

App-specific logic stays outside the shared lifecycle state machine.

Examples:

- `nvda_remote`
  - remote forwarding logic
  - local suppression rules specific to remote control
- `key_echo`
  - speech echo behavior
  - echo-specific suppression behavior

## Data Flow

### Idle Path

1. app binds `HotkeyCapture` handler
2. idle hotkey event is received
3. `StateTransitionHotkeyPolicy` checks whether it matches the app's activate hotkey
4. `InputActivationUseCase.enter_active()` switches capture ownership
5. app-specific start action runs
   - `start_control()` or `start_echo()`

### Active Path

1. app binds keyboard `InputCapture` listener
2. keyboard event is received
3. `ActiveKeyEventPolicy` checks whether it is the app's exit key
4. if exit key:
   - app-specific stop action runs
   - `InputActivationUseCase.exit_active()` restores idle capture mode
5. otherwise:
   - app-specific active key handler runs

## Facade Responsibilities

After this refactor, app facades should:

- compose the shared input lifecycle/policy components
- connect app-specific handlers and callbacks
- expose existing UI-facing methods

App facades should not:

- directly own the main capture transition state machine
- duplicate idle/active capture switching logic
- duplicate state-transition hotkey routing logic

## Platform/Capture Strategy

This phase standardizes the policy model, not the underlying platform mechanism.

That means:

- `nvda_remote` may keep its existing `HotkeyCapture` implementation
- `key_echo` should gain the same lifecycle shape: idle hotkey capture, active keyboard capture
- platform-specific capture objects remain valid as long as they satisfy the shared control contract

We are standardizing:

- when each capture runs
- how transitions occur
- where hotkey rules live

We are not standardizing:

- one universal physical capture backend for every platform and mode

## Error Handling

Shared input lifecycle code must avoid half-switched states.

Requirements:

- no simultaneous active hotkey capture and active keyboard capture in normal operation
- no state flag claiming active when only hotkey capture is running
- no state flag claiming idle when keyboard capture still owns the pipeline
- capture start/stop failures must be surfaced to existing status/error reporting

`nvda_remote` and `key_echo` may use different user-facing error messages, but the rollback expectations should be shared.

## Testing Strategy

### Shared Unit Tests

Add direct tests for the extracted shared input lifecycle/policy components:

- idle -> active transition
- active -> idle transition
- keyboard capture start failure rollback
- hotkey capture restart failure reporting
- mutual exclusion between captures

### App-Level Tests

#### `nvda_remote`

- idle `F11` enters control
- active `F11` exits control
- forwarding behavior remains unchanged for non-exit keys

#### `key_echo`

- idle `Enter` enters echo
- active `Escape` exits echo
- active normal keys still echo speech
- idle non-hotkeys pass through

### Runtime / Integration Expectations

- runtime starts in idle mode
- idle mode owns only `HotkeyCapture`
- active mode owns only keyboard `InputCapture`
- shutdown stops all active captures cleanly

## Completion Criteria

This phase is complete when:

1. `nvda_remote` and `key_echo` both use the `idle hotkey / active keyboard` lifecycle.
2. `key_echo` has a proper `HotkeyCapture` path for idle activation.
3. active-state exit keys are handled inside the active keyboard pipeline.
4. shared input lifecycle and transition policy components are extracted.
5. app facades no longer contain the primary capture-switching state machine.
6. shutdown/teardown stops all captures correctly.
7. existing UI controller surface remains compatible.
8. tests directly cover shared lifecycle rollback and app-level hotkey behavior.

## Suggested File Direction

The exact filenames can change, but the structure should move toward:

```text
src/application/input/
  activation.py
  state_transition_hotkeys.py
  active_key_policy.py

src/apps/nvda_remote/
  facade.py
  use_cases/
    remote_active_input.py

src/apps/key_echo/
  facade.py
  use_cases/
    echo_active_input.py
```

The shared input lifecycle belongs in `application/`, while app-specific active behavior remains in app-local modules.
