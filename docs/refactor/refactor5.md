# Architecture Refactor Review v5

## 1. Review Scope

This document reviews the current `src/` tree after the work recorded in:

- `docs/refactor/refactor4.md`
- `docs/superpowers/specs/`
- `docs/superpowers/plans/`
- `docs/superpowers/history/`

The main purpose of this v5 update is to answer a different question than the
previous version:

> Now that the Access8Graph transition-engine rewrite has landed, what should
> the next refactor phase be?

This document prioritizes **short, independently deliverable slices** first.
Large architecture themes are listed only after the short-term queue.

## 2. What Changed Since the Earlier v5 Direction

The earlier v5 recommendation centered on two items:

1. low-risk package-boundary cleanup
2. replacing the legacy Access8Graph state hierarchy with a declarative
   transition engine

That recommendation has now largely been executed.

Observed current state:

- `apps/access8graph/navigation/engine.py` provides the new transition engine
- `apps/access8graph/navigation/model.py` defines typed commands, states, and
  transition values
- `apps/access8graph/navigation/tables/` and
  `apps/access8graph/navigation/actions/` split most transition content by
  navigation concern
- `application.output.ports` already contains narrower speech protocols
- wx shell classes are already under `ui/shared`
- NVDA Remote-only runtime state already lives under `apps/nvda_remote/state.py`

Therefore, the next phase should **not** reopen the old state-machine rewrite
or repeat already-finished package moves. The highest-leverage work has moved
to the remaining concentration points that the rewrite exposed.

## 3. Main Conclusion

The next refactor phase should focus on **shrinking the new concentration
points without changing behavior**.

The most important observation is this:

- the legacy Access8Graph flow was removed successfully
- but some responsibilities were re-concentrated into new modules such as
  `navigation/actions/common.py`, `use_cases/navigation.py`,
  `application/output/service.py`, and the app-service composition code

So the next phase is no longer “replace the architecture.”
It is:

> consolidate the new boundaries by extracting smaller assembly, view-model,
> and dependency surfaces around the code that already works

## 4. Recommended Next Slices

The following slices are ordered by:

1. independent deliverability
2. low regression risk
3. architectural leverage for later work

### Slice 1. Split Access8Graph navigation assembly from runtime behavior

#### Why this should be first

`src/apps/access8graph/use_cases/navigation.py` currently mixes:

- GraphML graph/model creation
- navigator construction
- transition rule assembly
- registry assembly
- output adaptation
- flow startup
- navigation-session lifecycle

The transition engine itself is already separated, but the composition of that
engine is still concentrated in one place.

#### Recommended change

Extract a small assembly boundary, for example:

- `apps/access8graph/navigation/runtime.py`
- `apps/access8graph/navigation/assembly.py`
- or `apps/access8graph/navigation/factory.py`

Target responsibilities:

- one unit builds Graph/model/navigators
- one unit builds rule/guard/action/entry/exit registries
- one unit adapts output and assembles `TransitionNavigationFlow`
- `Access8GraphNavigationSession` keeps only session lifecycle

#### Why now

- behavior is already protected by parity and transition tests
- this is a structural cleanup, not a behavioral redesign
- it reduces the size and change surface of the current composition root

#### Main risk

- accidental startup-order differences
- accidental change to when `flow.start()` is invoked

### Slice 2. Extract navigation view models from `actions/common.py`

#### Why this is now high value

`src/apps/access8graph/navigation/actions/common.py` is currently the new
largest Access8Graph concentration point at over 1100 lines. It contains:

- `ListViewModel`
- `RunViewModel`
- shared action IDs
- shared guard IDs
- base actions
- guard logic
- entry/exit effects
- snapshot factory wiring

This is no longer a good “common” module. It is effectively a second
application core hidden behind a utility name.

#### Recommended change

Split at least these responsibilities:

- `navigation/view_models.py`
- `navigation/ids.py` or family-local ID modules
- keep shared guards/actions in a smaller `actions/common.py`

At minimum, remove the view-model classes from the action registry module.

#### Why now

- low risk if behavior is preserved
- improves readability immediately
- makes later family-specific extraction easier without touching engine logic

#### Main risk

- import churn only

### Slice 3. Narrow app-service dependency surfaces instead of passing broad `Capabilities`

#### Problem

`Capabilities` is better than ad hoc globals, but it is still a broad carrier
object:

- `Access8GraphAppService` only needs part of speech plus optional tone
- `NvdaRemoteAppService` needs speech, tone, and clipboard-related behavior
- use cases underneath still receive more capability than they actually use

This weakens the benefit already gained from `SpeechOutputPort`,
`SpeechSettingsPort`, and `SpeechLifecyclePort`.

#### Recommended change

Move to app-specific constructor dependencies:

- inject narrow ports into use cases directly
- keep `Capabilities` only at bootstrap/composition boundaries if still useful
- avoid passing a broad capability bag into deeper app layers

Example direction:

- `Access8GraphFlowOutput` depends on `SpeechOutputPort` and `ToneOutput | None`
- app services receive explicit collaborators instead of one multi-purpose bag

#### Why now

- the protocol split already exists
- this is mostly dependency cleanup, not feature work
- it will make speech/output changes safer later

#### Main risk

- constructor churn across app entrypoints and tests

### Slice 4. Extract mode objects out of app-service modules

#### Problem

Both:

- `apps/access8graph/service.py`
- `apps/nvda_remote/service.py`

still define mode classes inline with the app service:

- `Access8GraphNavigationMode`
- `RemoteControlMode`

This is workable, but it keeps mode-policy behavior physically attached to the
facade/controller module and makes the service files longer than they need to
be.

#### Recommended change

Move these classes to dedicated modules, for example:

- `apps/access8graph/modes.py`
- `apps/nvda_remote/modes.py`

or under the corresponding `use_cases/` package if that matches repo style.

#### Why now

- behavior is already explicit and testable
- extraction is mechanical
- it makes app services easier to review as facades rather than mixed facades
  plus mode implementations

#### Main risk

- low; import changes and focused test updates

### Slice 5. Refactor `QueuedService` into a narrower decorator role

#### Problem

`src/application/output/service.py` currently behaves like a decorator/proxy
around `SpeechService`, but it also re-exposes the full speech settings and
lifecycle API:

- output sequencing concern
- engine/voice/settings concern
- shutdown concern

in one class.

This works functionally, but it is still an SRP and ISP pressure point.

#### Recommended change

Refactor toward:

- one explicit output-queueing/decorator concern
- one speech settings/lifecycle concern

Possible shape:

- `QueuedSpeechOutput`
- `SpeechSettingsPort` still served by the underlying speech service
- composition points decide which object is passed to which consumer

#### Why now

- the protocol split is already in place
- this is a contained internal refactor with strong unit-test coverage

#### Main risk

- accidental behavior change in sequential/parallel routing

### Slice 6. Replace local one-off adapters with named reusable adapters

#### Problem

`apps/access8graph/use_cases/navigation.py` currently defines a local
`_OutputAdapter` class. This is a sign that the boundary is real, but the
abstraction has not been given first-class ownership.

#### Recommended change

Promote these adapter boundaries into named modules when they survive beyond a
single assembly file.

Examples:

- `navigation/output_adapter.py`
- or fold the behavior into `Access8GraphFlowOutput` if that is the real stable
  boundary

#### Why now

- very low risk
- improves naming clarity
- reduces “hidden architecture” inside assembly modules

## 5. Deferred High-Value Themes

These are important, but they are not the best immediate slices.

### Theme A. Reorganize Access8Graph navigation by domain family, not helper type

The current engine/table/action split is already much better than the legacy
state hierarchy. But the next larger architectural improvement would be to make
each navigation family more self-contained:

- direction
- undirected
- route plan
- transfer
- help/mode selection

That means grouping each family’s:

- rules
- actions
- view builders
- state-entry behavior

more tightly, instead of keeping too much shared machinery in `common.py`.

This is valuable, but it should follow Slices 1 and 2.

### Theme B. Replace `Capabilities` with explicit composition contracts across apps

The short-term slice is only to narrow dependencies at the service boundary.
The larger theme would be to stop using a generic capability bag as a dominant
cross-app composition pattern.

That is a bigger shift because it touches:

- bootstrap
- app constructors
- many tests

It should be approached incrementally after Slice 3 proves the narrower
dependency style in one or two apps.

### Theme C. Separate speech-output transport concerns from speech-engine settings entirely

The long-term output architecture still has three different concerns near each
other:

- queueing/scheduling
- engine/voice/settings
- runtime shutdown/lifecycle

The larger redesign would turn these into deliberately separate layers instead
of one object that happens to satisfy all ports.

This has real value, but it is larger than the next safe slice.

## 6. Recommended Order of Execution

Recommended near-term order:

1. Slice 1: Access8Graph navigation assembly extraction
2. Slice 2: navigation view-model extraction from `actions/common.py`
3. Slice 6: promote one-off adapters into named boundaries
4. Slice 4: extract mode objects from app-service modules
5. Slice 3: narrow app-service dependencies away from broad `Capabilities`
6. Slice 5: narrow `QueuedService` into a clearer decorator role

Reason for this order:

- start with Access8Graph structural cleanup where the transition rewrite just
  completed
- then clean low-risk naming and ownership boundaries
- only after that widen the changes into cross-app dependency cleanup
- leave output-stack reshaping until the narrower ports are actually used by
  consumers

## 7. Final Recommendation

If only one next refactor slice is chosen, it should be:

> extract Access8Graph navigation assembly from
> `src/apps/access8graph/use_cases/navigation.py`

If two slices are chosen, the second should be:

> split `src/apps/access8graph/navigation/actions/common.py`, beginning with
> the view-model classes

Those two steps have the best balance of:

- immediate codebase clarity
- low behavioral risk
- alignment with the superpowers design history
- leverage for later dependency and output cleanup
