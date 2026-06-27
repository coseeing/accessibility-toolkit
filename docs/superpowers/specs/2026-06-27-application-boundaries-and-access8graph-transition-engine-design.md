# Application Boundaries and Access8Graph Transition Engine Design

## Goals

This design defines the next refactor phase after `docs/refactor/refactor5.md`.
It has two sequential goals:

1. Correct the remaining low-risk application, adapter, and UI package
   boundaries.
2. Replace the Access8Graph object-oriented State hierarchy with an extensible
   declarative transition table and injected action handlers.

The work is delivered through five milestones. Each milestone must be
independently reviewable and verified before the next begins.

## Decisions Already Made

This design does not reopen these decisions:

- The work remains one overall design with a separate section for each
  milestone.
- `NavigationCommand` is a `StrEnum`.
- `NavigationStateId` is a `StrEnum` containing every legal navigation state.
- Every transition rule has a fixed target state.
- Data-dependent branches are represented by multiple guarded rules, not by an
  action-selected target.
- Guards are pure reads over one immutable snapshot shared for a single rule
  evaluation.
- Rule priority is forbidden. At most one guard for a source and command may
  succeed.
- Action handlers may directly mutate the existing navigator after completing
  all validations that can fail.
- The engine commits the target state only after the action succeeds.
- Unexpected action exceptions stop the navigation session; no rollback
  mechanism is introduced.
- Automatic advancement is represented by the internal
  `NavigationCommand.AUTO`.
- State-entry handlers may build view and presentation data but may not change
  the state.
- The new and old flow implementations are compared in tests, followed by one
  atomic production cutover.
- No command-dictionary, old-flow, import, or speech-settings compatibility
  facade remains in the final state.

## Current State

The refactor described by `refactor4.md` is substantially complete:

- Access8Graph graph selection and flow lifecycle are separate use cases.
- Access8Graph key translation and command dispatch have explicit boundaries.
- speech settings are passed to UI as an independent facade.
- `application.output.Manager` has been retired.
- `application.keyboard` is being moved under `application.input`.

The remaining boundary problems are:

- `SpeechEngineConfigStore` is application code that directly performs JSON
  and filesystem I/O.
- `SpeechServiceProtocol` forces consumers to depend on a 17-method interface.
- NVDA Remote-only state types live at the shared application root.
- wx-specific shell, tray, and panel classes live under `apps/shared`.
- obsolete speech-settings aliases still present multiple names for one
  facade.

The main architectural problem is now `src/apps/access8graph/flow.py`:

- it contains the flow, base states, 20 concrete states, and view classes
- states directly mutate the complete flow and navigator
- transitions are implicit assignments distributed across state methods
- commands are arbitrary dictionary values dispatched through `getattr`
- state entry can trigger additional hidden transitions
- output policy is coupled to transition execution

## Non-Goals

This phase does not:

- change the speech-settings JSON schema
- change UI behavior or layout
- rewrite the GraphML parser, model, or navigators
- redesign bootstrap providers
- refactor scheduler concurrency
- create a repository-wide generic state-machine framework
- migrate Key Echo or NVDA Remote to the new transition engine
- intentionally fix existing Access8Graph behavior during parity work
- preserve legacy import paths after their milestone is complete

## Target Architecture

### Package Boundaries

The target package ownership is:

```text
application/
  input/
    service.py
  output/
    speech/
      settings_store.py       # SpeechSettingsStore port
    ports.py                  # narrow speech protocols

adapters/
  config/
    json_speech_settings.py   # JsonSpeechSettingsStore adapter

apps/
  nvda_remote/
    state.py
  shared/
    mode_manager.py
    speech_runtime_settings.py
    speech_settings_facade.py

ui/
  shared/
    panel_controller.py
    tool_app_shell.py
    tray_icon.py
```

`application/config.py`, `application/state.py`, the speech compatibility
modules, and the old `apps/shared` UI modules are removed after consumers move.

### Speech Ports

The broad speech interface is split by consumer role:

```python
class SpeechOutputPort(Protocol):
    def speak(self, sequence: SpeechSequence) -> None: ...
    def cancel(self) -> None: ...
    def pause(self, is_paused: bool) -> None: ...


class SpeechSettingsPort(Protocol):
    def get_engine_options(self) -> tuple[tuple[str, str], ...]: ...
    def get_selected_engine(self) -> str: ...
    def set_engine(self, engine_id: str) -> None: ...
    def list_voices(self) -> tuple[tuple[str, str], ...]: ...
    def get_voice(self) -> str | None: ...
    def set_voice(self, voice_id: str) -> None: ...
    def get_rate(self) -> int | None: ...
    def set_rate(self, value: int) -> None: ...
    def get_pitch(self) -> int | None: ...
    def set_pitch(self, value: int) -> None: ...
    def get_volume(self) -> int | None: ...
    def set_volume(self, value: int) -> None: ...
    def get_supported_numeric_settings(
        self,
    ) -> tuple[SpeechNumericSetting, ...]: ...


class SpeechLifecyclePort(Protocol):
    def shutdown(self) -> None: ...


class SpeechServicePort(
    SpeechOutputPort,
    SpeechSettingsPort,
    SpeechLifecyclePort,
    Protocol,
):
    pass
```

Concrete speech services continue to satisfy these contracts structurally.
Consumers declare the narrowest contract they use. `SpeechServicePort` exists
only for composition points that genuinely require every capability.

### Speech Settings Persistence

`SpeechSettingsStore` preserves the current store operations:

- load/save selected engine
- load/save voice by engine
- load/save numeric setting by engine and setting ID

`JsonSpeechSettingsStore` preserves:

- the current JSON keys and nested layout
- UTF-8 encoding
- parent-directory creation
- clamping numeric settings
- fallback to empty/default data for missing, malformed, or unreadable files

`SpeechRuntimeSettingsCoordinator` depends only on
`SpeechSettingsStore`. App entrypoints construct the JSON adapter.

## Access8Graph Transition Model

### Commands

`NavigationCommand` is a closed `StrEnum`. It includes all current external
domain commands and one internal command:

```text
UP
DOWN
LEFT
RIGHT
CONFIRM
HOME
END
SELECT_DIRECTION
SELECT_UNDIRECTED
SELECT_PLAN
QUIT
OPEN_HELP
OPEN_MODE
OPEN_BROWSER
SELECT_STATION
SELECT_LINE
SELECT_ENDPOINT
AUTO
```

- HID-specific names do not enter the domain enum
- only the keyboard translator converts HID events to commands
- `AUTO` can only be generated by the transition flow
- no payload fields are added without a demonstrated domain need

`ESCAPE` remains an outer navigation-mode command handled by `ModeManager`
before the event reaches the transition flow. It is not a
`NavigationCommand`.

### State IDs

`NavigationStateId` is a closed `StrEnum` covering the existing state set:

```text
MODE
STATIONS
LINES
DIRECTION_END_POINT
DIRECTION_RUN
UNDIRECTION_RUN
PLAN_RUN
DIRECTION_TRANSFER
UNDIRECTION_TRANSFER
EXPLORE_NEIGHBOR
EXPLORE_SUB_LINE
DIRECTION_STATIONS
DIRECTION_LINES
SOURCE_STATIONS
SOURCE_LINES
DESTINATION_STATIONS
DESTINATION_LINES
UNDIRECTION_STATIONS
UNDIRECTION_LINES
UNDIRECTION_SUB_LINES
HELP
```

`HELP` replaces the current dynamically constructed `HelpState` identity.
The return state remains data in `NavigationContext`.

No transition, context, test, or action handler uses arbitrary state strings.

### Immutable Snapshot

One `NavigationSnapshot` is created before evaluating the candidate rules for a
source and command. It is a frozen value object containing only facts needed
by guards, such as:

- current state and return state
- current view selection and option count
- selected navigation mode
- whether line, station, source, or destination values exist
- neighbor and transfer counts
- whether a navigator run is active

All guards for that evaluation receive the same snapshot. Guards:

- may only read the snapshot
- may not receive the mutable context or navigator
- may not perform I/O
- may not mutate caches or registries

After a successful transition, the engine creates a new snapshot before
evaluating `AUTO`.

### Transition Rules

A transition rule is immutable and contains:

```python
@dataclass(frozen=True, slots=True)
class TransitionRule:
    source: NavigationStateId
    command: NavigationCommand
    target: NavigationStateId
    action_id: ActionId
    guard_id: GuardId | None = None
```

Every rule has one fixed target. There is no `allowed_targets`, dynamic target,
or `ActionResult.target_state`.

For a source and command:

- one unguarded rule is allowed only when no guarded alternatives exist
- multiple rules require mutually exclusive guards
- zero successful guards produces a normal rejection
- more than one successful guard raises `AmbiguousTransitionError`
- list order never acts as rule priority

### Transition Engine

The engine executes one external command as a macrostep:

1. Build one immutable snapshot.
2. Find all rules matching the current state and command.
3. Evaluate every candidate guard against the same snapshot.
4. Return rejected if no rule succeeds.
5. Raise `AmbiguousTransitionError` if multiple rules succeed.
6. Invoke the selected action handler.
7. If the action rejects, keep the current state.
8. If the action succeeds, run source-state exit presentation processing.
9. Commit the rule's fixed target.
10. Run target-state entry processing to build its view and presentation
    effects.
11. Build a fresh snapshot and evaluate `AUTO`.
12. Repeat automatic transitions until stable.
13. Present the accumulated macrostep result once.

The engine does not:

- know HID values
- call wx
- speak, cancel, or beep
- dispatch handlers through `getattr`
- choose a target through an action result
- catch and hide unexpected action exceptions

### Automatic Transitions

An automatic transition is a normal fixed-target rule using
`NavigationCommand.AUTO`.

This replaces hidden transitions currently triggered from state `enter()`,
including single-option automatic selection. State-entry handlers may:

- build the current view
- append open messages and hints to presentation effects
- expose facts for the next snapshot

They may not change `NavigationContext.current_state`.

Source-state exit handlers may append close messages before the target is
committed. Entry and exit handlers may not select another target or perform
output I/O.

The engine protects automatic processing with:

- a maximum of 32 automatic transitions per macrostep
- visited rule/state tracking for the current macrostep
- an `AutomaticTransitionCycleError` on repetition or exhaustion

### Action Handlers

Handlers are injected through an action registry and addressed by typed action
IDs. A handler receives:

- the immutable snapshot used to select the rule
- narrow mutable navigation context
- only the navigator collaborator needed by that action

A handler:

- completes all queries and validations that can fail before mutation whenever
  practical
- may directly mutate the existing navigator
- returns accepted or rejected plus presentation/context effects
- never selects or commits the target state
- never speaks or beeps

There is no copy-on-write or rollback mechanism. An unexpected exception is a
fatal navigation-session error.

### Context

`NavigationContext` owns state-machine session data, not infrastructure:

- current state
- return/background state
- current view model
- selected navigation mode
- pending presentation effects
- state-machine selection data not already owned by a navigator

It does not own:

- output adapters
- HID events
- wx objects
- the transition table or registries

### State Lifecycle Handlers

State lifecycle handlers are injected separately from transition actions:

- an exit handler contributes source-state close effects
- an entry handler builds the target view and contributes open/hint effects
- neither handler may change the current state
- neither handler may invoke output
- entry processing completes before the next `AUTO` snapshot is built

This keeps lifecycle presentation explicit without allowing hidden
transitions.

### Presentation

`FlowPresenter` receives one completed macrostep result and a narrow
`FlowOutput` port. It preserves the existing observable order:

1. close messages
2. open messages
3. first-entry hint when applicable
4. current view display

It then performs the current cancel-and-speak policy once for the stable state.

For a recognized command rejected by the current state, it preserves the
current beep and current-view speech behavior. Unrecognized HID events retain
the existing navigation-mode consume behavior without entering the transition
engine.

No partial presentation is emitted when an action raises unexpectedly.

## Transition Table Validation

`TransitionTableValidator` runs in tests and during flow assembly. It rejects:

- unknown command, state, action, or guard IDs
- duplicate unguarded rules
- an unguarded rule combined with guarded alternatives for the same source and
  command
- unreachable non-terminal states
- an invalid initial state
- missing required return paths for help/menu states
- statically detectable `AUTO` cycles

Guard overlap is data-dependent and is therefore also checked at runtime.
Tests must provide representative snapshots for every guarded branch and prove
that exactly one rule succeeds for each expected branch.

Navigation-mode exit behavior is validated in ModeManager/service integration
tests rather than by the transition table.

## Error Semantics

Expected outcomes are represented without exceptions:

- `TRANSITIONED`: action succeeded and target differs from source
- `HANDLED`: action succeeded while remaining in the same state
- `REJECTED`: no guard matched or the action rejected
- `UNHANDLED`: reserved for commands outside the flow contract

Unexpected errors include:

- ambiguous transitions
- automatic-transition cycles
- missing registry entries that escaped assembly validation
- unexpected action or navigator exceptions

Unexpected errors propagate to the existing app-service boundary. That
boundary emits `ErrorRaised`, stops navigation, and preserves existing error
speech behavior.

## Milestone 1: Low-Risk Boundary and Compatibility Cleanup

### Intent

Correct package ownership, narrow speech dependencies, and remove obsolete
aliases before the transition rewrite begins.

### Scope

- complete the keyboard service move to `application.input`
- introduce narrow speech ports
- introduce the speech settings store port and JSON adapter
- migrate all runtime and test consumers
- move NVDA Remote state to its app package
- move wx shell classes to `ui/shared`
- remove speech-settings compatibility aliases

### Required End State

- `src/application/keyboard.py` is deleted
- `src/application/config.py` is deleted
- `src/application/state.py` is deleted
- `src/apps/shared/speech_settings_controller.py` is deleted
- app-specific speech-settings alias modules are deleted
- old wx modules under `apps/shared` are deleted
- no old path is re-exported

### Behavioral Constraints

- speech settings persistence remains byte-for-byte schema compatible
- malformed configuration fallback remains unchanged
- speech engine, voice, rate, pitch, and volume behavior remains unchanged
- UI startup, tray, panel, and shutdown behavior remains unchanged
- NVDA Remote connection/control state behavior remains unchanged

### Validation

- focused tests move with each public import
- JSON adapter contract tests cover existing read/write and corruption behavior
- protocol tests prove concrete speech services satisfy required ports
- repository search finds no old imports
- the full unit and integration suite passes

## Milestone 2: Existing Flow Behavior Baseline

### Intent

Make the current implicit behavior explicit before implementing its
replacement.

### Scope

Create a data-driven characterization matrix covering every current state:

- state entry and exit effects
- primary commands
- rejected recognized commands
- target state
- view data and selection
- navigator mutations
- message, hint, and display ordering
- beep behavior
- background/return behavior
- single-option automatic progression
- help, transfer, exploration, and route-planning paths

### Rules

- production code does not change in this milestone
- discovered bugs are recorded separately
- tests describe current behavior even when that behavior is not ideal
- each scenario must identify all externally observable effects

### Definition of Done

- every current concrete state is represented in the matrix
- all branches in current `if/elif/else` transition logic are represented
- automatic transitions are explicitly represented as expected chained steps
- the baseline suite passes against the existing flow

## Milestone 3: Parallel Transition Engine

### Intent

Build the complete replacement behind tests without mixing it into the
production path.

### Initial File Structure

```text
src/apps/access8graph/navigation/
  __init__.py
  model.py
  snapshot.py
  engine.py
  actions.py
  table.py
  presenter.py
  flow.py
```

The initial modules stay consolidated by responsibility. Mode-family splitting
waits until contracts stabilize in Milestone 5.

### Scope

- implement command and state enums
- implement snapshots and pure guards
- implement rules, validation, and engine macrosteps
- implement action and guard registries
- implement `AUTO` processing and cycle protection
- implement context, view models, results, and presenter
- implement the complete transition table
- implement a new flow adapter compatible with the dispatcher boundary

### Parity Method

The same scenarios from Milestone 2 run against:

- the old `MrtFlow`
- the new transition flow

Parity compares:

- final state
- intermediate automatic steps
- navigator mutation
- view model
- messages, hints, and speech item order
- cancel/speak/beep calls
- rejection and exception behavior

### Definition of Done

- every baseline scenario passes against both implementations
- transition table validation passes
- ambiguous guard tests fail as designed
- guard purity and shared-snapshot use are tested
- production still constructs only the old flow

## Milestone 4: Atomic Cutover and Old Architecture Removal

### Intent

Switch production to the verified transition engine and remove the old
architecture in the same milestone.

### Scope

- make `MrtFlowFactory` construct the new flow
- make the translator return `NavigationCommand`
- make the dispatcher depend on a typed `NavigationFlow` contract
- switch result mapping to `TransitionResult`
- remove old state and view classes
- remove command dictionaries and dynamic `getattr` dispatch
- remove temporary old/new parity fixtures that are no longer needed

### Constraints

- no feature flag
- no runtime fallback to the old flow
- no compatibility adapter
- no GraphML model or navigator rewrite

### Definition of Done

- no runtime reference to the old hierarchy remains
- no Access8Graph command dictionary remains
- key-event-to-output integration paths pass
- startup, hotkey, stop, and unexpected-error behavior remains unchanged
- all unit and integration tests pass

## Milestone 5: Module Consolidation and Integrity Protection

### Intent

Improve ownership after the engine contract is stable and make future table
extensions safe.

### Target Grouping

Split actions and transition tables by:

- common/list/help
- mode selection
- direction exploration
- undirected exploration
- route planning
- transfer/explore

All groups are assembled into one validated transition graph.

### Scope

- split stable action and table modules by navigation concern
- keep the engine and shared model independent of mode-family details
- add negative validation suites
- document how to add a command, guard, action, state, and transition
- update module ownership documentation

### Required Negative Tests

- duplicate rules
- unguarded and guarded rule conflicts
- multiple successful guards
- unknown action or guard
- unreachable states
- invalid initial state
- missing help/menu return
- missing required in-flow return behavior
- automatic-transition cycles and maximum-step exhaustion

### Definition of Done

- adding a rule or state does not require modifying the engine
- each family module has one navigation concern
- all tables form one valid graph
- extension documentation matches the implemented contracts
- the full test suite passes

## Test Strategy

Testing proceeds from the smallest contract outward:

1. Value-object tests for commands, states, snapshots, rules, and results.
2. Validator tests for graph and registry integrity.
3. Engine tests with fake guards and actions.
4. Action tests with fake contexts and navigators.
5. Presenter tests with exact ordered output.
6. Characterization and old/new parity scenarios.
7. Dispatcher and service integration tests.
8. Full unit and integration regression suite.

Tests must specifically prove:

- candidate guards share the same snapshot instance
- guards cannot access mutable context through their contract
- action rejection does not commit state
- action exception does not commit target state or emit partial presentation
- state entry cannot change state
- automatic transitions present once after stabilization
- the runtime never resolves ambiguity by rule order

## Risks and Controls

### Missing Implicit Behavior

Control: complete Milestone 2 before implementing the replacement and run each
scenario against both flows.

### Partial Navigator Mutation

Control: validate before mutation, keep actions focused, stop the entire
session on unexpected failure, and add before/after assertions for transfer
and route actions.

### Speech Ordering Regression

Control: compare exact ordered speech items and output calls, not only final
state.

### Over-Abstraction

Control: keep the engine under `apps/access8graph`; do not extract a shared
framework without a second concrete consumer.

### Excessive Concurrent Change

Control: complete and verify each milestone before starting the next. Do not
combine GraphML, scheduler, bootstrap, or UI behavior changes with this work.

## Overall Definition of Done

The phase is complete only when:

- package ownership matches this design
- obsolete compatibility paths are removed
- application policy depends on a speech store port rather than JSON I/O
- speech consumers use appropriately narrow protocols
- Access8Graph commands and states are closed typed enums
- all branches use fixed-target declarative rules
- guards are pure and evaluate one immutable snapshot
- ambiguity is rejected rather than prioritized
- automatic transitions use `NavigationCommand.AUTO`
- actions cannot choose or commit target states
- presentation occurs once per stable macrostep
- the old State hierarchy and dynamic dispatch are removed
- user-visible navigation, speech, beep, hotkey, and error behavior remains
  compatible
- all unit and integration tests pass
