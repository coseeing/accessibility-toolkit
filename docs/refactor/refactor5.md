# Architecture Refactor Review v5

## 1. Review Scope

This document compares the current `src/` code against the following material
and recommends the direction for the next refactor phase:

- `docs/refactor/refactor4.md`
- `docs/superpowers/specs/`
- `docs/superpowers/plans/`
- `docs/superpowers/specs/2026-06-26-access8graph-facade-and-shared-speech-settings-design.md`
- `docs/superpowers/plans/2026-06-26-access8graph-facade-and-shared-speech-settings-implementation.md`

The review uses three complementary perspectives:

- Design Patterns: determine whether the existing patterns actually reduce
  coupling and which patterns fit the next phase
- SOLID: examine responsibilities, extension points, interface size, and
  dependency direction
- Incremental delivery: even though the core will be fully rewritten, control
  risk through independently verifiable milestones

This document contains refactor design and recommendations only. It does not
include implementation.

## 2. Completion Status of `refactor4.md`

Most major recommendations from `refactor4.md` have been completed:

1. The Access8Graph flow lifecycle has been extracted into:
   - `GraphSelectionUseCase`
   - `Access8GraphNavigationSession`
   - `MrtFlowFactory`
2. Access8Graph command dispatch has been extracted into:
   - `Access8GraphKeyTranslator`
   - `Access8GraphCommandDispatcher`
3. Speech settings now have independent components:
   - `SpeechSettingsFacade`
   - `SpeechRuntimeSettingsCoordinator`
4. `application.output.Manager` has been removed.
5. The contents of `application.keyboard` are being moved into
   `application.input`, which improves package cohesion.

The next phase should therefore no longer focus on thinning the Access8Graph
app service or removing the output manager. The highest-leverage problem has
moved inward to the Access8Graph navigation core and several remaining unclear
package boundaries.

## 3. Main Conclusion

The next phase should use a two-stage strategy:

1. Complete low-risk package-boundary and compatibility cleanup.
2. Fully rewrite the Access8Graph navigation flow, replacing the current State
   class hierarchy with an extensible declarative transition table.

Access8Graph should not begin with a mechanical file split. The problem with
`src/apps/access8graph/flow.py` is not merely its 955 lines. Its 20 states can
all directly manipulate the complete `MrtFlow`, navigator dictionary, message
queue, and view. Moving those classes into separate files would leave the God
Context, dynamic dispatch, and implicit transitions intact.

The approved target is:

> Declarative transition table + injected action handlers

Once the new architecture reaches behavioral parity, the production path
should switch atomically. The old and new flows must not remain in parallel,
and no compatibility adapter should be retained.

## 4. Design Patterns Review

### 4.1 Access8Graph State Pattern

`MrtFlow` currently uses the State Pattern, but it has these problems:

- transitions are scattered across state methods as
  `self.flow.state = ...`
- commands are dispatched dynamically through `getattr(self.state, key)()`
- each state can read and write the entire flow and navigator
- view construction, navigation mutation, messages, and speech policy share
  one execution path
- the transition graph cannot be validated without executing the program
- adding a command or state requires changes to the translator, state classes,
  and implicit transitions

Assessment:

- The problem is not a lack of the State Pattern. The current object-oriented
  State Pattern lacks a narrow context and an explicit transition model.
- The next step should be a Table-Driven State Machine, not splitting the
  current state classes into separate files.

Recommended patterns:

- **Table-Driven State Machine**: centrally describe source, command, guard,
  action, and target
- **Command**: replace command dictionaries with a typed `NavigationCommand`
- **Strategy / Ports**: inject guard and action handlers
- **Presenter**: separate speech, cancellation, and beep policy from transition
  execution
- **Factory**: let `MrtFlowFactory` assemble the transition engine, context,
  and handlers

### 4.2 Access8Graph Command Boundary

The translator and dispatcher now form a useful boundary, but the translator
returns:

```python
{"key": "down", "repeat": 0, "pressing": 0}
```

`repeat` and `pressing` do not currently form a stable domain contract, while
`key` remains an arbitrary string used to drive `getattr`.

Recommendations:

- the translator returns `NavigationCommand | None`
- commands use an enum or frozen dataclass
- the dispatcher depends only on a `NavigationFlow` protocol
- the flow accepts typed commands and returns `TransitionResult`
- no dictionary compatibility path is retained

### 4.3 Facade

The three app services reasonably act as UI-facing Facades, although they
still assemble some use cases and concrete collaborators directly. This is not
the highest priority for the next phase because bootstrap already centralizes
most runtime wiring.

Recommendations:

- keep each app service as a facade; do not continue splitting it solely based
  on class size
- move assembly responsibility only when a collaborator is independently
  replaceable or has a clear reuse case
- app-service consumers should depend on narrow protocols rather than receive
  capabilities they do not need through `Capabilities`

### 4.4 Adapter / Port

`SpeechEngineConfigStore` resides in `application.config`, but directly performs
JSON and filesystem I/O. `SpeechRuntimeSettingsCoordinator` also depends on
this concrete class.

Recommendations:

- define a `SpeechSettingsStore` protocol in the application layer
- move the JSON implementation into an adapter such as
  `adapters/config/json_speech_settings.py`
- make the coordinator depend only on the protocol
- preserve the existing JSON schema and fault-tolerance behavior

This follows Dependency Inversion more closely than merely moving `config.py`
under `application/output/speech`.

### 4.5 UI Shell

The following files are under `apps/shared` but belong directly to the wx UI:

- `tool_app_shell.py`
- `tray_icon.py`
- `panel_controller.py`

They should move to `ui/shared`. This is an ownership correction and does not
require another abstraction layer.

## 5. SOLID Review

| Principle | Current State | Main Problem | Recommendation |
|---|---|---|---|
| SRP | App services are more focused than in v4 | `MrtFlow` and its states jointly handle transitions, navigation mutation, views, messages, and output | Split responsibilities among engine, context, action handlers, and presenter |
| OCP | Adding a state or command requires edits across implicit logic | `getattr` dispatch and state methods make the transition graph unverifiable | Register rules and handlers through a declarative table |
| LSP | No obvious subtype-substitution defect exists | `State` subclasses have different implicit requirements for `view` and navigator shape | Remove the hierarchy and use rules with explicit handler contracts |
| ISP | `SpeechServiceProtocol` has 17 methods | Consumers that only need speak/cancel also depend on settings and lifecycle APIs | Split protocols by output, settings, and lifecycle use |
| DIP | The coordinator depends on a JSON store; some app code depends on broad `Capabilities` | Application policy knows concrete persistence and consumers can access unnecessary output capabilities | Introduce a store port and use narrow output protocols in use-case constructors |

### 5.1 Highest-Priority SRP Problems

Highest-priority files:

- `apps/access8graph/flow.py`
- `apps/access8graph/graphml/mrt_navigator.py`
- `apps/access8graph/graphml/model.py`

Only `flow.py` should be part of the next core rewrite. Although the GraphML
model and navigator are also large, rewriting them at the same time would make
transition parity difficult to assess. They should be handled separately after
the flow stabilizes.

### 5.2 Highest-Priority ISP Problems

`Capabilities.speech` is currently typed as the complete
`SpeechServiceProtocol`. It can be progressively split into:

- `SpeechOutputPort`: `speak`, `cancel`, and `pause`
- `SpeechSettingsPort`: engine, voice, rate, pitch, and volume
- `SpeechLifecyclePort`: `shutdown`

A concrete `SpeechService` or `QueuedService` may implement multiple protocols,
but each consumer declares only the interface it uses. Structural typing makes
additional wrapper layers unnecessary.

### 5.3 Package Cohesion

Recommended changes:

- `RuntimeState`, `ConnectionState`, and `ControlState` from
  `application.state` are used only by NVDA Remote and should move to
  `apps/nvda_remote/state.py`
- remove these speech compatibility shims:
  - `apps/shared/speech_settings_controller.py`
  - `apps/key_echo/use_cases/speech_settings.py`
  - `apps/nvda_remote/use_cases/speech_settings.py`
- move the UI shell classes to `ui/shared`
- retain `application.events` for now because it has real cross-app use; do not
  split it solely for directory tidiness

## 6. Target Access8Graph Architecture

### 6.1 Core Components

#### `NavigationCommand`

- a typed enum or frozen dataclass
- represents domain commands such as `UP`, `DOWN`, `LEFT`, `RIGHT`, `CONFIRM`,
  and `HELP`
- the keyboard translator is the only HID-to-command conversion boundary

#### `NavigationStateId`

- defines stable state identities
- replaces scattered strings such as `"direction_run"`
- gives the transition table, context, and tests one shared set of IDs

#### `TransitionRule`

Each rule contains at least:

- source state
- command
- optional guard ID
- action ID
- target state, or a bounded set of targets explicitly selected by the action
  result

Rules describe collaboration only. They do not directly perform navigator or
output I/O.

#### `TransitionEngine`

Responsibilities:

1. Find a rule from the current state and command.
2. Evaluate its guard.
3. Invoke the injected action handler.
4. Commit the target state only after the action succeeds.
5. Return an explicit `TransitionResult`.

The engine must not:

- create wx/UI objects
- speak or beep directly
- depend on HID key codes
- locate actions through `getattr`

#### `NavigationContext`

The context stores only the session data required by the state machine, such
as:

- current state
- background/return state
- selected navigation mode
- pending messages
- selection/session data

The context must not expose the complete `MrtFlow` to every action.

#### `ActionHandlers`

Responsibilities:

- execute navigator queries or mutations
- build view models
- update context
- return action results and presentation data

Handlers are injected into the engine through a registry. The table references
stable action IDs rather than storing bound methods, making it independently
validatable and testable.

#### `FlowPresenter`

Responsibilities:

- convert transition/action results into speech items
- decide when to cancel speech
- decide whether a failure should beep
- call a narrow `FlowOutput` port

### 6.2 Data Flow

```text
CapturedKeyEvent
    -> Access8GraphKeyTranslator
    -> NavigationCommand
    -> Access8GraphCommandDispatcher
    -> TransitionEngine
       -> guard registry
       -> action handler registry
       -> NavigationContext
    -> TransitionResult
    -> FlowPresenter
    -> speech / beep output
```

### 6.3 Transition Table Grouping

After the complete cutover, tables may be grouped by navigation-mode family:

- common/list/help transitions
- mode-selection transitions
- direction-exploration transitions
- undirected-exploration transitions
- route-planning transitions
- transfer/explore transitions

Grouping exists only for ownership and readability. Once loaded, the groups
still form one fully validatable transition graph.

## 7. Error Handling

### 7.1 Expected Rejections

The following conditions should produce typed results rather than exceptions:

- the current state has no matching command
- a guard fails
- an action determines that movement or selection is currently unavailable

`TransitionResult` should distinguish:

- handled and transitioned
- handled without transition
- rejected
- unhandled

The presenter then decides whether to beep or speak for each result.

### 7.2 Action Failure

- the engine commits the target state only after the action succeeds
- an action should compute its result before updating context whenever possible
- if a navigator mutation cannot be rolled back, the handler must explicitly
  define its failure semantics and have corresponding tests

### 7.3 Unexpected Exceptions

The table and engine must not silently consume unexpected exceptions. They
should propagate to the existing app-service boundary, which:

- emits `ErrorRaised`
- stops navigation
- preserves the current error-speech behavior

## 8. Transition Table Validation

The table should be validated during tests and runtime assembly:

- the same source + command pair must not have ambiguous duplicate rules
- every source and target state must exist
- every guard ID and action ID must be registered
- the initial state must be valid
- every non-terminal state must be reachable from the initial state
- help/menu states must have explicit return paths
- navigation modes must have the required exit/escape behavior
- dynamic targets must remain within the target set declared by the action
  contract

Validation failures should stop startup or CI immediately rather than remain
undetected until a user presses a key.

## 9. Recommended Milestones

### Milestone 1: Low-Risk Boundary and Compatibility Cleanup

Scope:

- complete the move from `application.keyboard` to `application.input`
- remove the `SpeechSettingsController` compatibility shim
- remove the Key Echo and NVDA Remote speech-settings alias modules
- move NVDA Remote runtime state into the app package
- move `ToolAppShell`, `ToolTrayIcon`, and `PanelController` to `ui/shared`
- introduce a `SpeechSettingsStore` port and JSON adapter
- split `SpeechServiceProtocol` into narrow protocols based on consumer needs

Completion criteria:

- the import graph ensures the application layer does not depend on concrete
  JSON persistence
- `apps/shared` no longer contains wx shell/tray code
- speech settings have only one canonical facade name
- all existing unit and integration tests pass

### Milestone 2: Baseline Existing Flow Behavior

Scope:

- complete `MrtFlow` characterization tests
- create a state/command transition matrix
- record speech items, beeps, views, and navigator side effects
- explicitly cover help, return/background state, single-option automatic
  entry, transfers, and error paths

Completion criteria:

- every current state has tests for entry, primary commands, rejected commands,
  and exit
- tests explicitly document all existing implicit behavior
- this milestone does not change production flow behavior

### Milestone 3: Build the New Transition Engine

Scope:

- add typed commands and state IDs
- add transition rules, engine, context, and results
- add guard/action registries
- add the presenter
- build the complete declarative transition table
- validate the new engine against the scenarios from Milestone 2

Completion criteria:

- the new engine reaches behavioral parity with the old flow in tests
- all table validation passes
- the production path still uses only the old flow, avoiding partial mixing

### Milestone 4: Atomic Cutover and Removal of the Old Architecture

Scope:

- make `MrtFlowFactory` build the new flow
- move the command dispatcher to the typed command/result contract
- switch the production path to the transition engine
- delete `State`, `ListState`, `RunState`, and all their subclasses
- remove dynamic `getattr` dispatch and command dictionaries
- do not add a compatibility adapter

Completion criteria:

- key-event-to-speech/beep integration tests pass
- UI, hotkey start/stop, and error-shutdown behavior remains unchanged
- the repository contains no runtime reference to the old flow-state hierarchy

### Milestone 5: Module Consolidation and Integrity Protection

Scope:

- split transition tables and action modules by mode family
- retain a single graph-validation process
- add negative tests for unreachable states, duplicates, and unknown handlers
- update architecture documentation and module-ownership guidance

Completion criteria:

- each table/action module has one navigation concern
- adding a state or command does not require changing the engine
- new rules can be added by registering a table entry and handler
- the full test suite passes

## 10. Testing Strategy

### 10.1 Characterization Tests

Lock down current behavior before the rewrite. Do not confuse whether current
behavior is desirable with whether the rewrite is compatible. If an existing
bug is found, record it and make a separate decision rather than fixing it
incidentally during parity work.

### 10.2 Engine Unit Tests

Cover at least:

- rule matching
- guard success/failure
- action success/rejection/exception
- state commit timing
- ambiguous rule rejection
- dynamic target validation

### 10.3 Handler Tests

Test each action handler with fake navigators and contexts:

- input contract
- navigator query/mutation
- context patch
- presentation result
- failure without an invalid state commit

### 10.4 Table Contract Tests

Validate the complete transition matrix with data-driven tests rather than
repeating extensive imperative setup for every rule.

### 10.5 Integration Tests

Retain a small set of high-value paths:

- select GraphML and start navigation
- direction exploration
- undirected exploration
- route planning
- help/menu return
- transfer
- invalid-command beep
- exception -> error event -> stop navigation

## 11. Risks and Controls

### 11.1 Highest Risk: Missing Implicit Behavior

Existing transitions are distributed across state methods, while some behavior
is triggered indirectly by the property setter, `enter()`, `exit()`, and
`refresh_view()`.

Controls:

- build the transition matrix in Milestone 2
- run the same scenarios against both implementations in tests
- do not mix old and new states in production

### 11.2 Changed Speech Ordering

The order in which `message`, hint, and view display are combined affects the
user experience.

Controls:

- give the presenter exact sequence tests
- make parity tests compare speech-item order, not only final state

### 11.3 Navigator Mutation

Some actions directly change navigator
current/source/destination/line/station fields.

Controls:

- make action handlers explicitly own mutation
- update state only after the action succeeds
- add before/after snapshot assertions for high-risk transfer and route actions

### 11.4 Over-Abstraction

The table engine could incorrectly grow into a repository-wide generic
framework.

Controls:

- keep the engine under `apps/access8graph` initially
- do not force Key Echo or NVDA Remote to adopt it
- consider moving it into a shared/application package only after a second
  equivalent use case appears

## 12. Work Not Recommended for This Phase

- do not mechanically split the 20 old State classes into separate files first
- do not retain a dictionary-command compatibility layer
- do not keep the old and new state engines in parallel long term
- do not rewrite the GraphML parser, model, or navigator at the same time
- do not reopen bootstrap/runtime-provider refactoring
- do not create a repository-wide generic state-machine framework
- do not mix Scheduler concurrency refactoring into this phase
- do not change the speech-settings JSON schema

## 13. Later Candidates

Reassess the following after this phase:

1. Whether `graphml/mrt_navigator.py` should separate queries from mutable
   session state.
2. Whether `graphml/model.py` should separate parsing, domain entities, and
   graph queries.
3. Whether the concurrency contract in `application/output/scheduler.py` needs
   a clearer state model and shutdown semantics.
4. Whether module-level factories and `PlatformProvider` in
   `bootstrap/platform.py` should converge on one Abstract Factory API.
5. Whether app services still need complete `Capabilities` or can use narrow
   output ports throughout.

These items should not begin while the transition-table rewrite remains
unstable.

## 14. Definition of Done for the Next Phase

All five milestones are complete only when:

- package ownership is clear and wx UI code is no longer under `apps/shared`
- speech-settings compatibility shims have been removed
- application policy does not directly depend on a JSON configuration
  implementation
- NVDA Remote-specific state is no longer under the shared application root
- speech consumers use protocols narrowed to their needs
- Access8Graph uses typed commands
- the Access8Graph transition graph is expressed by a fully validatable
  declarative table
- injected action handlers provide navigator and context mutation
- presentation/output policy is outside the transition table and engine
- the old State hierarchy, dynamic `getattr` dispatch, and command dictionaries
  have been removed
- navigation, speech, beep, hotkey, and error behavior remains compatible
- all unit and integration tests pass

## 15. Final Recommendation

The next phase should begin with Milestone 1 to correct low-risk but explicit
ownership, ISP, and DIP problems and stabilize package boundaries. It should
then stop extending the current object-oriented State hierarchy. Milestones 2
through 5 should establish a complete behavioral baseline, build the
declarative transition engine in parallel, and finally perform an atomic
cutover that removes the old architecture.

This approach improves extensibility more than merely splitting `flow.py`.
Adding a command, guard, action, or transition will not require changing the
engine or granting a new state class access to the entire flow.
