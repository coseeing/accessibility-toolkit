# Architecture Review v6

## Design Patterns vs SOLID Principles Review of `src/`

## 1. Review Goal

This document reviews the current `src/` code from two angles:

- **Design Patterns**: where the code already uses useful architectural
  patterns
- **SOLID Principles**: where those patterns still leave overloaded
  responsibilities, broad interfaces, or unclear dependency direction

The goal is not to argue that patterns are bad. The goal is to identify where:

> a pattern exists, but its current packaging still weakens SRP, ISP, OCP, or
> DIP

This document emphasizes **refactor recommendations**, not a generic code-smell
list.

## 2. Main Assessment

The codebase is in a better architectural state than earlier refactor rounds.
Several important patterns are already used correctly:

- app services act as facades
- Access8Graph uses a table-driven state machine
- output and settings behavior use Protocol-based ports
- bootstrap owns more composition than before
- protocol events are more typed than in earlier iterations

The main remaining problem is not “missing patterns.”
It is:

> some successful patterns have accumulated too much responsibility in their
> supporting modules

In other words:

- the pattern choice is often correct
- the ownership boundary around the pattern is still uneven

## 3. Where Design Patterns Are Working Well

### 3.1 Facade in app services

`Access8GraphAppService`, `NvdaRemoteAppService`, and `KeyEchoAppService`
correctly act as UI-facing facades rather than giant business-logic classes in
the older style.

Why this is good:

- UI code gets one stable entrypoint
- deeper use cases can evolve independently
- event and lifecycle orchestration no longer leaks directly everywhere

SOLID impact:

- this improves SRP at the app boundary
- this also helps DIP because UI depends on a stable application-facing surface

### 3.2 Table-Driven State Machine in Access8Graph

The move from the legacy state hierarchy to:

- `navigation/model.py`
- `navigation/engine.py`
- `navigation/tables/`
- `navigation/actions/`

is a strong improvement.

Why this is good:

- transitions are explicit
- validation is possible before runtime
- tests can characterize rules and macrosteps directly
- OCP is better than the old `getattr`-driven state methods

SOLID impact:

- OCP improved because new rules extend a table instead of editing opaque state
  methods
- LSP concerns from uneven `State` subclasses were mostly removed

### 3.3 Strategy / Port usage in output and persistence

The code now uses Protocols for:

- speech output
- speech settings
- speech lifecycle
- settings persistence

This is the right direction.

Why this is good:

- application policy can depend on behavior contracts
- adapters remain replaceable
- tests can use structural fakes easily

SOLID impact:

- DIP is substantially better than earlier refactor stages
- ISP improved because separate ports now exist, even if not every consumer
  fully takes advantage of them yet

## 4. Where Patterns and SOLID Are Still in Tension

### 4.1 `navigation/actions/common.py`

#### Pattern reading

This module supports the table-driven state machine by centralizing shared
actions, guards, IDs, entry effects, and helper objects.

#### SOLID reading

It is now too large and too mixed to count as one responsibility.

Current contents include:

- view models
- action IDs
- guard IDs
- action implementations
- guard implementations
- entry/exit presentation effects
- snapshot assembly support

This is an SRP violation even though the surrounding pattern is sound.

#### Recommendation

Refactor by responsibility, not by line count alone:

- move `ListViewModel` and `RunViewModel` out first
- isolate ID definitions from behavioral functions
- keep “common actions” only for behavior that is truly cross-family

### 4.2 `MrtFlowFactory` and `Access8GraphNavigationSession`

#### Pattern reading

This area uses Factory and Session-style orchestration.

#### SOLID reading

The factory currently acts as:

- graph loader
- model builder
- navigator builder
- registry assembler
- output adapter assembler
- flow starter

The session currently owns:

- selected-graph dependency
- active flag
- flow lifecycle
- output cancellation side effect
- status notification

These are manageable, but the composition boundary is still thick.

#### Recommendation

Split assembly from runtime lifecycle:

- one builder/composition unit assembles the flow
- one session unit owns start/stop/active state

Keep the pattern, but narrow the role of each class.

### 4.3 `Capabilities` as a broad dependency bag

#### Pattern reading

`Capabilities` behaves like a convenience composition object.

#### SOLID reading

At deeper layers it behaves too much like a small service locator:

- consumers receive more than they need
- the existence of narrow ports becomes less useful
- ISP and DIP gains are partially diluted

This is not a catastrophic problem, but it is a structural drag.

#### Recommendation

Use `Capabilities` only near bootstrap if desired.
Below that layer, prefer explicit constructor dependencies with narrow ports.

### 4.4 `QueuedService` as Decorator/Proxy

#### Pattern reading

`QueuedService` is effectively a decorator or proxy around `SpeechService`.

#### SOLID reading

It mixes:

- queueing policy
- output routing
- settings pass-through
- lifecycle shutdown

The pattern is recognizable, but the decorated surface is too wide.

This is a classic case where the pattern exists but ISP and SRP are still weak.

#### Recommendation

Preserve the decorator idea, but narrow what is being decorated:

- decorate speech output behavior only
- do not make the queueing layer own the entire settings API by default

### 4.5 Inline mode classes inside app-service modules

#### Pattern reading

The code uses a small Mode pattern through `ModeManager` plus concrete mode
objects.

#### SOLID reading

The concrete mode objects are still embedded in service modules:

- `Access8GraphNavigationMode`
- `RemoteControlMode`

This keeps the mode pattern partially hidden inside the facade implementation.

#### Recommendation

Promote mode implementations into dedicated modules.
This is a small change, but it aligns the code structure with the pattern that
already exists.

### 4.6 Local `_OutputAdapter` inside navigation assembly

#### Pattern reading

This is an Adapter pattern.

#### SOLID reading

The adapter is real, but its ownership is anonymous and local. That usually
means the boundary exists architecturally but has not yet been given a stable
home.

#### Recommendation

Either:

- turn it into a named adapter module, or
- collapse it into the output class that truly owns the boundary

Do not leave important adapter boundaries hidden as throwaway local helpers if
they survive beyond one experiment.

## 5. SOLID Summary by Principle

### SRP

Improved areas:

- app services are less overloaded than earlier versions
- Access8Graph transitions are no longer mixed into one legacy state hierarchy

Remaining pressure points:

- `navigation/actions/common.py`
- `apps/access8graph/use_cases/navigation.py`
- `application/output/service.py`

### OCP

Improved areas:

- transition rules are more extensible through table registration
- ports make adapters easier to add

Remaining pressure points:

- large shared modules still require editing central files for unrelated
  additions
- `common.py` risks becoming the place every new navigation behavior must touch

### LSP

Improved areas:

- old fragile state subclass assumptions were mostly removed

Remaining pressure points:

- no major subtype defect stands out right now
- current LSP risk is lower than SRP/ISP/DIP risk

### ISP

Improved areas:

- speech ports are split

Remaining pressure points:

- many consumers still receive broad collaborators
- `QueuedService` still exposes a large combined surface
- `Capabilities` still encourages wider-than-needed dependencies

### DIP

Improved areas:

- settings persistence and speech behavior now have clearer ports

Remaining pressure points:

- deeper layers still receive concrete aggregation objects
- some assembly and adapter boundaries are still defined locally instead of as
  stable abstractions

## 6. Refactor Recommendations

## 6.1 Short-Term Independent Slices

### Recommendation 1

Extract Access8Graph navigation assembly out of
`src/apps/access8graph/use_cases/navigation.py`.

Why:

- best balance of SRP improvement and low risk
- directly follows the completed transition-engine work

### Recommendation 2

Split `src/apps/access8graph/navigation/actions/common.py`, starting with the
view-model classes.

Why:

- largest current concentration point in the new navigation stack
- high clarity gain with low behavior risk

### Recommendation 3

Move concrete mode classes out of app-service modules.

Why:

- aligns code structure with the existing Mode pattern
- small, mechanical, easy to test

### Recommendation 4

Replace local adapters with named module-level adapters where the boundary is
stable.

Why:

- makes real architectural seams visible and reusable

### Recommendation 5

Begin narrowing dependencies away from broad `Capabilities` in one app at a
time.

Why:

- activates the value of the ports that already exist
- lowers cross-app constructor coupling gradually

## 6.2 High-Value Larger Themes

### Theme 1. Family-oriented Access8Graph navigation modules

Group each navigation family’s rules, actions, entry behavior, and view
concerns more tightly so that `common.py` stops acting as a second hidden core.

### Theme 2. Output stack redesign around narrower decorators

Redesign `QueuedService` and related composition so queueing, settings, and
lifecycle are intentionally separate roles instead of one pass-through-heavy
object.

### Theme 3. Explicit composition contracts instead of capability bags

Move the repo further toward explicit app constructor dependencies and away from
generic aggregate collaborators.

## 7. Final Recommendation

From a **Design Patterns vs SOLID Principles** perspective, the codebase does
not need a new grand pattern.

It needs to do the following:

1. keep the patterns that are already correct
2. reduce the responsibility concentration around those patterns
3. let narrow ports and explicit composition become real in consumer code, not
   only in protocol definitions

If only one refactor is chosen next, choose:

> Access8Graph navigation assembly extraction

If a second refactor is chosen immediately after that, choose:

> splitting `navigation/actions/common.py`, beginning with view models
