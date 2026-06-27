# Access8Graph Facade, Shared Speech Settings, and Output Manager Retirement Design

## Goals

This design completes the next refactor phase defined in `refactor4.md` through
four sequential milestones:

1. Collapse `Access8GraphAppService` from a workflow owner into a thin facade
2. Extract a dedicated command translation boundary for Access8Graph
3. Promote speech settings from an app-service-internal controller into an
   independent shared facade
4. Remove `application.output.Manager` and fold any remaining usage back into
   clearer runtime paths

This is a single spec containing both the overall target architecture and four
milestones that can be implemented and validated incrementally. Each milestone
should be reviewable and verifiable on its own before moving to the next one.

## Decisions Already Made

This spec assumes the earlier discussion is already settled and does not reopen
the following decisions:

- `application.output.Manager` will be retired, not renamed as a
  compatibility-oriented abstraction
- the end state for Access8Graph is a fully thinned facade, but implementation
  will proceed through milestones
- `SpeechSettingsController` will not remain inside each app service and will
  instead be extracted into an independent shared facade
- milestone-first delivery is the primary execution model; this is not a
  one-shot rewrite

## Current State

According to `docs/refactor/refactor4.md`, the codebase has already completed:

- bootstrap/runtime extraction
- the shared speech runtime settings coordinator
- typed NVDA Remote protocol events and the main orchestration split

Because of that, the center of gravity for the next phase is no longer NVDA
Remote. It is now these three unfinished boundary problems:

- `Access8GraphAppService` still combines facade, workflow, lifecycle, and
  mode-private details
- speech settings still appear across apps as app-service pass-through surfaces
- `application.output.Manager` is still present in the codebase even though it
  no longer matches the center of the active architecture

## Non-Goals

This design does not include the following work:

- redesigning the bootstrap/runtime provider architecture
- introducing a generic input command framework
- reworking UI layout, interaction flow, or visual design
- changing the persistence schema or existing keys for speech settings
- designing a new multimodal output bus
- rewriting the already-completed NVDA Remote typed event and orchestration
  split

## Target End State

After all four milestones are complete, the system should have the following
shape:

- `Access8GraphAppService` retains only a UI-facing facade and a small amount
  of wiring responsibility
- Access8Graph has clear boundaries for graph selection, flow lifecycle,
  navigation session management, command translation, and hotkey startup policy
- speech settings become an independent shared feature used through a clearly
  named facade by UI or app wiring code
- `application.output.Manager` disappears from the active design
- each milestone has explicit behavioral validation so that the refactor can
  proceed incrementally without changing external behavior

## Overall Strategy

This refactor does not start by inventing abstractions and then looking for
places to apply them. It starts by separating the existing areas with the
highest responsibility density and the most direct coupling, in risk order.

The overall sequence is:

1. First clean up the Access8Graph flow lifecycle and facade boundary
2. Then isolate the Access8Graph translator / command dispatch boundary
3. Once the app service is thinner, extract speech settings into a true shared
   facade
4. Finally remove `application.output.Manager` from paths where it no longer
   belongs

The purpose of this order is to avoid changing shared surfaces while the app
service is still too large, which would create large concurrent changes on both
sides of the boundary.

---

## Milestone 1: Access8Graph Flow Lifecycle and Facade Narrowing

### Intent

Address the heaviest workflow and lifecycle responsibilities in Access8Graph
first, so that `Access8GraphAppService` no longer directly owns flow creation,
flow teardown, or navigation session state transitions.

### Problem

`Access8GraphAppService` currently owns:

- graphml path selection and validation
- flow creation and teardown
- navigation running state
- error-reporting policy during hotkey startup flow
- private-method coupling during mode entry and exit

At the same time, `Access8GraphNavigationMode` still calls private service
methods directly. That means mode-to-service interaction is based on internal
structure coupling rather than interface collaboration.

### Design

The first step is not to split all of Access8Graph at once, but to extract the
lifecycle responsibilities first:

- `Access8GraphAppService` keeps the start / stop / query surface exposed to UI
- actual flow creation, teardown, and navigation lifecycle move into a focused
  use case or lifecycle object
- graph selection and file validation should also move behind a clearer
  boundary, so the service does not mix UI surface concerns with domain
  validation
- `Access8GraphNavigationMode` may depend only on stable public interfaces and
  may no longer touch private service methods

This milestone does not require translator extraction yet. That is the next
milestone.

### Suggested File Structure

- Modify: `src/apps/access8graph/service.py`
- Modify: `src/apps/access8graph/flow.py`
- Modify: `src/apps/access8graph/output.py`
- Possibly add:
  - `src/apps/access8graph/use_cases/navigation.py`
  - `src/apps/access8graph/use_cases/graph_selection.py`
  - `src/apps/access8graph/use_cases/__init__.py`

### Boundary Rules

`Access8GraphAppService` should be responsible for:

- providing a stable facade to UI
- assembling the navigation lifecycle collaboration
- forwarding status events to the UI listener

The navigation lifecycle/use case should be responsible for:

- creating the flow
- tearing down the flow
- maintaining whether navigation is currently active
- managing side effects when starting and stopping

The mode should be responsible for:

- mode enter / exit semantics
- handing key events to a stable interface

The mode should not:

- know how the flow is built
- directly access private service state
- directly call private service methods

### Risks

- start / stop timing changes may alter speech cancellation behavior
- error reporting during hotkey startup may be lost if moved carelessly
- splitting graphml selection and file existence checks may change exception
  types or when they are raised

### Definition of Done

`M1` is complete only when all of the following are true:

- `Access8GraphNavigationMode` no longer calls private service methods
- flow creation and teardown are no longer implemented directly inside
  `Access8GraphAppService`
- graph selection and lifecycle responsibilities are clearly separated from the
  service
- the main UI-facing call pattern for `Access8GraphAppService` remains stable
- existing navigation start/stop, error speech, and hotkey startup behavior
  stays unchanged

### Validation

- Unit tests verify:
  - graph selection, start, stop, missing file, and error speech behavior
  - mode enter / exit no longer rely on private methods
- Existing Access8Graph flow / service / UI tests continue to pass
- If new tests are needed, prioritize service-to-use-case boundary tests rather
  than only adding integration coverage

---

## Milestone 2: Independent Access8Graph Command Translation Boundary

### Intent

Extract command translation and command dispatch from inline mode logic so that
Access8Graph key handling has a boundary that is as clear as the lifecycle
boundary established in the previous milestone.

### Problem

`Access8GraphNavigationMode.handle_key_event()` still directly:

- creates `Access8GraphKeyTranslator()`
- converts the key event into a command
- sends the command directly into the flow

That means the mode currently owns:

- mode semantics
- translator assembly
- command dispatch

This structure makes translation rules and lifecycle rules difficult to test
separately, and it makes later key-handling policy changes more likely to
become entangled with mode state changes.

### Design

After `M1` has established a cleaner lifecycle boundary, extract a dedicated
command translation boundary on top of it:

- define a small translator / dispatcher collaboration
- the mode should only decide whether the current mode accepts the event and
  which collaborator should receive it
- the translator should convert key events into app commands
- the dispatcher or navigation collaboration should execute the command

This should not become a large generic framework. It should only formalize the
small recurring boundary that already exists in Access8Graph.

### Suggested File Structure

- Modify: `src/apps/access8graph/input.py`
- Modify: `src/apps/access8graph/service.py`
- Modify: `src/apps/access8graph/flow.py`
- Possibly add:
  - `src/apps/access8graph/use_cases/command_dispatch.py`
  - `src/apps/access8graph/use_cases/navigation_commands.py`

### Boundary Rules

The translator should be responsible for:

- receiving a key event
- returning a command or `None`

The dispatcher / navigation collaboration should be responsible for:

- checking whether an active flow exists
- executing commands against the flow
- deciding how execution failures are reported

The mode should be responsible for:

- applying mode-specific handled / unhandled semantics
- converting the result into the app pipeline result shape

### Risks

- unknown key handling may accidentally change from pass-through to consume, or
  vice versa
- command execution failures may follow a different error-reporting path
- changed return values when no active flow exists may affect the whole
  keyboard pipeline

### Definition of Done

`M2` is complete only when all of the following are true:

- translator instantiation no longer lives inside `handle_key_event()`
- the responsibilities of mode, translator, and dispatcher are separated
- tests can describe translation rules independently from mode lifecycle
  behavior
- handled / unhandled / pass-through behavior remains unchanged

### Validation

- Unit tests verify the translation rules themselves
- Unit tests verify mode behavior for command / no command / no active flow
- Regress existing Access8Graph keyboard pipeline tests

---

## Milestone 3: Extract Shared Speech Settings into an Independent Facade

### Intent

Change speech settings from "each app service owns a set of pass-through
methods" into an independent shared facade, so that speech settings become a
true shared feature module rather than part of each app service surface.

### Problem

Each app service currently exposes nearly the same methods:

- `get_speech_engine_options()`
- `get_selected_speech_engine()`
- `set_speech_engine()`
- `get_available_voices()`
- `set_selected_voice()`
- `get_rate()` / `set_rate()`
- `get_pitch()` / `set_pitch()`
- `get_volume()` / `set_volume()`

Most of these methods simply delegate to `SpeechSettingsController`, which
causes:

- larger public app service surfaces
- speech settings to appear as app-specific service behavior
- unnecessary UI-controller coupling to app services

### Design

Promote speech settings directly into an independent shared facade rather than
doing a smaller surface-tightening step:

- create a clearly named shared speech settings facade
- move the current `SpeechSettingsController` behavioral responsibility into
  that facade
- have UI or app wiring depend directly on the facade
- app services should no longer expose the full set of speech settings
  pass-through methods, except for the rare app-specific coordination cases
  that truly need to remain

This facade still needs to accept:

- the speech service adapter
- the engine-change callback
- the voice-change callback
- the numeric-setting-change callback

But it should no longer exist as "part of an app service."

### Suggested File Structure

- Modify or Rename: `src/apps/shared/speech_settings_controller.py`
- Modify: `src/apps/nvda_remote/service.py`
- Modify: `src/apps/key_echo/service.py`
- Modify: `src/apps/access8graph/service.py`
- Modify: corresponding UI controller / app wiring call sites
- Possibly add:
  - `src/apps/shared/speech_settings_facade.py`

### Boundary Rules

The shared speech settings facade should be responsible for:

- reading and writing speech engine / voice / numeric settings
- encapsulating callback triggering and shared policy

App services should be responsible for:

- coordinating speech settings with app-domain behavior only where necessary
- no longer exposing the full speech settings API as part of their primary
  surface

The UI wiring layer should be responsible for:

- explicitly injecting the speech settings facade into the UI controllers that
  need it

### Risks

- existing UI code may assume app services have speech settings methods
- if naming or injection is unclear, the coupling may simply move from the
  service to the app wiring layer
- if engine-change status events currently flow through app services, that
  responsibility may need to be reassigned explicitly

### Definition of Done

`M3` is complete only when all of the following are true:

- speech settings have an independent, clearly named shared facade
- at least the main UI controllers no longer depend directly on app-service
  speech settings pass-through methods
- app service public surfaces are noticeably smaller
- speech settings persistence and behavior remain unchanged

### Validation

- Unit tests verify the shared speech settings facade API and callback behavior
- UI / app wiring tests verify controllers can still read and write speech
  settings
- Regress `test_speech_settings_controller.py`, `test_app_wx.py`, and related
  app service tests

---

## Milestone 4: Remove `application.output.Manager`

### Intent

Remove a transitional abstraction that no longer belongs at the center of the
active architecture, so that output paths return to more direct and
understandable runtime collaboration.

### Problem

`application.output.Manager` currently provides:

- speech routing
- cancel
- pause
- tone routing
- clipboard push

But the active runtime path now depends mainly on:

- `Capabilities`
- `QueuedService`
- speech runtime services
- direct router callbacks

That means the generic name `Manager` no longer matches its actual role. Keeping
it only increases the chance that maintainers misread it as still being part of
the core design.

### Design

This milestone does not rename it or repackage it for compatibility. It retires
it directly:

- find any remaining call sites that still depend on `Manager`
- fold any still-useful routing behavior back into clearer runtime paths
- adjust tests so they verify the collaborations that actually remain, instead
  of verifying the `Manager` wrapper class itself

If some tests only protect legacy wrapper forwarding behavior, they should be
deleted or rewritten to validate the new explicit paths.

### Suggested File Structure

- Delete: `src/application/output/manager.py`
- Modify: `src/application/output/__init__.py`
- Modify: any file that still imports `Manager`
- Modify or Delete: `tests/unit/test_output_manager.py`

### Boundary Rules

After removal:

- protocol/router code should depend directly on clear callback collaborations
- clipboard push should remain where transport and clipboard context actually
  exist
- no generic manager class should be used as a routing container

### Risks

- if there is an untested hidden consumer, removal may miss it
- `test_output_manager.py` may still protect forwarding semantics that matter,
  so it must be separated into wrapper noise versus real behavioral contract

### Definition of Done

`M4` is complete only when all of the following are true:

- `application.output.Manager` has been removed from production code
- no active runtime path still depends on it
- the remaining output collaboration can be understood through clearer named
  runtime paths
- tests have been updated to validate the new paths rather than the old wrapper
  class

### Validation

- Search confirms production imports no longer reference `Manager`
- Regress output / message router / app service related tests
- Delete or rewrite tests that only covered wrapper forwarding

---

## Cross-Milestone Validation Strategy

Each milestone must be validated independently. Validation cannot wait until
everything is complete.

The rules are:

1. Change only one primary responsibility surface at a time
   For example, `M1` should not also change translator behavior, and `M3`
   should not also change output paths.

2. Prioritize boundary tests over expanding large integration suites
   The purpose of this refactor is to clarify responsibilities, so tests should
   land first on the new boundaries.

3. Keep UI-facing behavior stable
   User-visible keyboard handling, speech feedback, navigation start / stop,
   and speech settings behavior must not change during the refactor.

4. Regress after every milestone
   If existing tests already cover the area, run the smallest relevant subset.
   If a new boundary is introduced, add the most direct tests for that boundary.

## Exit Criteria

This refactor plan is complete only when all of the following are true:

- Access8Graph is no longer controlled by a single app service that owns facade,
  lifecycle, translation, and mode-private details at the same time
- speech settings have become an independent shared facade rather than an
  attached app service surface
- `application.output.Manager` has been retired
- all four milestones have corresponding tests and validation results
- the main next-phase decisions recorded in `docs/refactor/refactor4.md` have
  all been implemented

## Summary

This spec turns the higher-level direction in `refactor4.md` into four
incremental milestones. Its purpose is not to create more abstractions, but to
bring the existing responsibility boundaries into a state that can evolve
cleanly:

- first make the Access8Graph service thin
- then separate command translation from lifecycle handling
- next extract speech settings out of app services into a true shared facade
- finally remove `application.output.Manager`, which no longer belongs in the
  core design

That leaves future app evolution built on clearer collaborations instead of on
historical wrappers and oversized facades.
