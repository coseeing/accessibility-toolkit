# Architecture refactor review v4

Context
-------
This review compares `docs/refactor/refactor3.md` with the current codebase.

Since `refactor3.md`, the codebase has completed most of the refactor slice
that was identified there as the recommended next move:

- shared speech runtime settings wiring now exists in
  `src/apps/shared/speech_runtime_settings.py`
- app entrypoints now use the shared coordinator instead of repeating speech
  settings persistence logic inline
- typed protocol events have landed in the NVDA Remote protocol/session layer
- `NvdaRemoteAppService` is no longer the central place where raw protocol
  status dictionaries are translated into UI-facing events
- NVDA Remote orchestration has already been split into focused use cases such
  as:
  - `RemoteConnectionUseCase`
  - `RemoteProtocolEventHandler`
  - `RemoteStatusPresenter`
  - existing control/input-forwarding use cases

Because of that, the next refactor should no longer focus on NVDA Remote as the
main architectural bottleneck. That work is now largely in the "complete and
stabilize" category.

The next phase should instead focus on the parts of the codebase that still
have incomplete boundaries or unclear abstraction value.

What Changed Since v3
---------------------

1. Shared speech runtime settings are now a solved cross-app problem.

`refactor3.md` identified duplicated speech engine/voice/rate/pitch/volume
startup wiring across the three app entrypoints. That duplication has now been
centralized under `SpeechRuntimeSettingsCoordinator`.

Current assessment:
- This is no longer a primary refactor target.
- Remaining differences between entrypoints are mostly legitimate app-specific
  runtime policy, not accidental duplication.

2. NVDA Remote is no longer the most urgent service-boundary problem.

`refactor3.md` prioritized typed protocol events and service decomposition in
NVDA Remote. The current code now reflects that split:

- `RemoteSession` and `MessageRouter` no longer appear to be dict-first at the
  app boundary.
- `NvdaRemoteAppService` composes focused use cases instead of owning all
  connection/protocol/presentation logic directly.
- protocol event handling and connection lifecycle are now meaningfully
  separated.

Current assessment:
- NVDA Remote still deserves normal cleanup and test maintenance.
- It is no longer the highest-leverage place to spend the next major refactor
  pass.

3. The remaining architectural imbalance is now more visible in Access8Graph.

With bootstrap extraction, speech runtime settings, typed events, and NVDA
Remote orchestration largely improved, the biggest remaining "service as
controller plus workflow plus lifecycle owner" shape is now in
`Access8GraphAppService`.

Current assessment:
- This is now the clearest remaining mismatch with the architecture direction
  established in earlier refactors.
- It is local enough to improve safely, but large enough to justify being the
  next main focus.

4. Some shared/controller abstractions are still carrying policy and persistence
knowledge together.

The codebase now has better runtime composition, but there is still a blurred
boundary between:

- UI-facing controller methods
- persistence callbacks
- app-service-level policy

The main examples are:
- `src/apps/shared/speech_settings_controller.py`
- app service speech-setting pass-through methods

Current assessment:
- This is not broken, but it still creates broad service surfaces.
- It is a good follow-up refactor after Access8Graph service decomposition.

5. `application.output.Manager` now looks more obviously transitional.

The active architecture is centered around:
- `Capabilities`
- `QueuedService`
- speech runtime services
- direct router callbacks

`application.output.Manager` still exists and is tested, but its generic name
does not match its narrower role.

Current assessment:
- This is still lower priority than app-service boundary work.
- But the abstraction should now be either clarified or retired, rather than
  left ambiguous.

Current Highest-Leverage Refactor Directions
--------------------------------------------

1. Bring Access8Graph up to the same facade/use-case standard as NVDA Remote
   and Key Echo.

Why this is now the top priority:
- `Access8GraphAppService` still owns file validation, flow lifecycle,
  navigation state, hotkey startup policy, error speech side effects, and
  speech-settings pass-through.
- `Access8GraphNavigationMode` still reaches into private service methods.
- translator creation and command execution are still coupled to mode handling
  instead of a stable boundary.

Why this matters:
- It keeps one app behind the architecture standard already established
  elsewhere.
- It makes local changes harder because workflow, state, and UI-facing methods
  are mixed together.
- It preserves private-method coupling that makes later reuse or testing
  harder.

Recommended direction:
- keep `Access8GraphAppService` as the UI-facing facade
- extract focused units for:
  - graph selection and validation
  - flow construction/destruction
  - navigation session lifecycle
  - command translation/dispatch
  - hotkey-start policy and startup error reporting
- remove mode-to-private-service coupling

2. Narrow the shared speech settings boundary.

Why this is the second priority:
- app services still expose many speech pass-through methods directly
- `SpeechSettingsController` combines speech adapter calls with persistence
  callbacks
- the current shape works, but still encourages app services to become
  "everything controller" facades

Why this matters:
- it broadens the public surface of each app service
- it makes speech settings a repeated UI-facing concern in every app service
- it leaves unclear whether speech settings are app-service behavior or shared
  feature-module behavior

Recommended direction:
- decide whether speech settings should remain:
  - a shared controller owned by each app service, or
  - a dedicated shared facade/module passed to UI code separately
- if they remain inside app services, at least reduce repetition through a more
  explicit shared protocol/mixin/facade boundary

3. Standardize command translation boundaries where the pattern is already
   emerging.

Why this is third, not first:
- the repo already has useful input primitives and does not need a large
  generic input pipeline refactor
- but translator creation and command execution are still uneven between apps

Why this matters:
- it affects testability and local clarity
- it is likely to become simpler after Access8Graph is split properly

Recommended direction:
- define a small translator contract where it adds value
- apply it first in Access8Graph, where translator construction is still inline
- avoid building a large framework; standardize only the boundary that is
  already recurring

4. Resolve the role of `application.output.Manager`.

Why this is fourth:
- it is conceptually muddy, but not blocking current runtime work
- the class is smaller risk than service-boundary issues

Recommended direction:
- choose one path:
  - keep it as a compatibility utility and rename/document it to reflect its
    narrower purpose, or
  - remove it after confirming no active runtime path needs it
- do not expand it into a more generic abstraction without a real use case

Recommended Refactor Slices
---------------------------

Slice 1. Access8Graph flow lifecycle extraction
-----------------------------------------------

Goal:
- remove flow construction/destruction and navigation session state ownership
  from `Access8GraphAppService`

Files most likely involved:
- `src/apps/access8graph/service.py`
- `src/apps/access8graph/flow.py`
- `src/apps/access8graph/output.py`
- `src/apps/access8graph/input.py`
- possibly a new module such as:
  - `src/apps/access8graph/use_cases/navigation.py`
  - `src/apps/access8graph/use_cases/graph_selection.py`

Target shape:
- `Access8GraphAppService` delegates start/stop logic to a navigation use case
- flow construction is owned by a dedicated factory/builder
- mode entry/exit talks to a stable public interface, not private service
  methods

Key risks:
- changing start/stop timing can alter current speech cancellation behavior
- hotkey startup failure handling may regress if error reporting moves without
  keeping the current semantics

Definition of done:
- `Access8GraphNavigationMode` no longer calls private service methods
- flow creation/destruction no longer lives directly in the app service
- current behavior for selecting a graph, starting navigation, stopping
  navigation, and error speech remains unchanged

Slice 2. Access8Graph command translation boundary
--------------------------------------------------

Goal:
- move command translation and command execution away from inline mode logic

Files most likely involved:
- `src/apps/access8graph/input.py`
- `src/apps/access8graph/service.py`
- `src/apps/access8graph/flow.py`

Target shape:
- a stable translator or command-dispatch boundary exists
- `Access8GraphNavigationMode` handles mode semantics, not translator assembly
- command execution happens through a clearer unit boundary

Key risks:
- subtle behavior changes for unknown keys
- accidentally changing whether a key is consumed or passed through

Definition of done:
- translator instantiation is no longer embedded in `handle_key_event()`
- tests express command translation behavior separately from mode lifecycle
- pass-through/handled behavior remains stable

Slice 3. Shared speech settings facade tightening
-------------------------------------------------

Goal:
- reduce repeated speech-settings pass-through surfaces in app services

Files most likely involved:
- `src/apps/shared/speech_settings_controller.py`
- `src/apps/nvda_remote/service.py`
- `src/apps/key_echo/service.py`
- `src/apps/access8graph/service.py`
- related UI controller call sites

Target shape:
- speech settings have a more explicit boundary as a shared feature
- app services either:
  - expose a smaller speech-settings interface, or
  - delegate that interface through a clearly named shared facade

Key risks:
- UI code may currently depend on exact controller method names
- over-abstracting this area could add indirection without reducing complexity

Definition of done:
- speech settings behavior is still shared across apps
- repeated boilerplate methods on app services are reduced or isolated behind a
  clearer boundary
- UI behavior and persisted settings remain unchanged

Slice 4. Output manager clarification or retirement
---------------------------------------------------

Goal:
- remove ambiguity around `application.output.Manager`

Files most likely involved:
- `src/application/output/manager.py`
- tests under `tests/unit/test_output_manager.py`
- any remaining consumers

Target shape:
- either the class is clearly documented/renamed as compatibility-oriented, or
- it is removed and its remaining usage is folded into clearer runtime paths

Key risks:
- this can produce churn without much practical payoff if done too early
- tests may encode legacy behavior that still matters for backward
  compatibility

Definition of done:
- the codebase no longer presents `Manager` as a core abstraction unless it
  truly is one
- maintainers can tell whether it is active architecture or compatibility code
  without reading multiple files

Suggested Order
---------------

Recommended order for the next phase:

1. Access8Graph flow lifecycle extraction
2. Access8Graph command translation boundary cleanup
3. Shared speech settings facade tightening
4. Output manager clarification or retirement

Why this order:
- it addresses the largest remaining app-service boundary problem first
- it keeps the next refactor mostly local to one app before touching shared
  controller surfaces
- it avoids spending early effort on low-leverage conceptual cleanup

What Not To Start With
----------------------

1. Do not reopen bootstrap/runtime extraction.

That work is already in place and no longer the main architecture issue.

2. Do not introduce a fully generic input command framework.

The current codebase does not need a large new abstraction here. It needs one
remaining app brought up to the same standard as the others.

3. Do not build a more ambitious output bus yet.

There is still no strong evidence that current app requirements justify a more
generic multimodal output architecture.

Concrete definition of done for the next phase
----------------------------------------------

The next phase is complete when:

- `Access8GraphAppService` becomes a thin facade rather than the owner of flow
  construction, navigation lifecycle, and mode-private workflow details
- `Access8GraphNavigationMode` depends only on stable public interfaces
- Access8Graph command translation has a clearer testable boundary
- speech settings exposure is narrowed or isolated behind a more explicit
  shared boundary
- the role of `application.output.Manager` is clearly resolved as either active
  architecture or compatibility code

Summary
-------

Compared with `refactor3.md`, the codebase has already finished most of the
high-priority NVDA Remote and shared runtime cleanup that previously justified
the next refactor phase.

That changes the center of gravity. The best next move is no longer to keep
splitting NVDA Remote, but to bring Access8Graph up to the same architectural
standard, then tighten the shared speech settings boundary, and finally resolve
whether `application.output.Manager` still belongs in the active design.
