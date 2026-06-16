# accessibility-toolkit PRD

This document defines the product framing for `accessibility-toolkit`. It explains why the toolkit exists, who it is for, what it should provide, and how success should be measured. It is not the primary installation or architecture guide.

## 1. Executive Summary

`accessibility-toolkit` is a Python toolkit for building desktop accessibility applications that need shared keyboard and hotkey capture, a keyboard event handling pipeline, speech and output scheduling, mode switching and interaction control, and application interfaces. The product goal is to turn the current repository into a clearly defined toolkit that supports multiple accessibility apps, rather than treating shared runtime infrastructure as a side effect of one NVDA Remote client. If successful, the toolkit will reduce duplicated engineering work, accelerate new accessibility app development, and provide a stable base for both internal app development and future reuse.

## 2. Problem Statement

### Who has this problem?

- Developers building accessibility-focused desktop applications in Python
- Maintainers evolving multiple desktop accessibility apps in one codebase
- Developers migrating accessibility workflows out of tightly coupled NVDA add-on environments

### What is the problem?

Accessibility desktop applications repeatedly need the same infrastructure:

- keyboard and hotkey capture
- keyboard event handling pipelines plus mode entry/exit behavior
- speech backend selection and output scheduling control
- reusable application interfaces
- clean separation between shared runtime and app-specific behavior

Without a toolkit, each app tends to implement these concerns independently or entangle them with domain logic.

### Why is it painful?

- New apps spend time rebuilding plumbing instead of user-facing behavior
- Shared behaviors diverge across apps and become harder to maintain
- Platform-specific details leak upward into business logic
- Migrating standalone accessibility tools out of NVDA runtime assumptions becomes slower and riskier

### Evidence

Evidence comes from the repository's own evolution:

- The project started as an NVDA Remote client and later had to extract shared input, output, bootstrap, and application-interface layers
- `key_echo` exists to prove that the shared input/output foundation is not remote-specific
- `access8graph` exists to prove that the same foundation can support a non-remote spoken navigation tool
- Current project documentation now describes the repository as a toolkit with multiple apps on top of it

## 3. Target Users & Personas

### Primary Persona: Accessibility App Developer

- Role: Python developer building desktop accessibility tools
- Goal: deliver app-specific behavior without rebuilding input, speech, and application-interface infrastructure
- Pain points:
  - low-level input handling is easy to get wrong
  - speech backend wiring is repetitive
  - cross-platform desktop concerns are costly

### Secondary Persona: Repository Maintainer

- Role: Maintainer of shared toolkit code plus multiple concrete apps
- Goal: keep shared behavior aligned while letting apps remain different
- Pain points:
  - duplicated runtime wiring
  - unclear boundaries between toolkit and app logic
  - documentation drift between product, architecture, and implementation

### Secondary Persona: NVDA Add-on Migration Author

- Role: Developer porting an accessibility workflow out of NVDA runtime dependencies
- Goal: preserve user interaction patterns while using a standalone desktop runtime
- Pain points:
  - legacy code assumes NVDA runtime APIs
  - replacing runtime infrastructure is expensive

### Jobs to be Done

- When I build an accessibility desktop tool, I want shared runtime capabilities so I can focus on user value instead of infrastructure.
- When I maintain multiple accessibility apps, I want shared behaviors defined once so the apps stay aligned and testable.
- When I migrate an NVDA-dependent tool, I want a reusable desktop base that preserves interaction patterns without requiring the NVDA runtime.

## 4. Strategic Context

### Product Goals

- Reposition the repository from a project-specific client to a reusable accessibility toolkit
- Lower future engineering cost for new desktop accessibility apps
- Create a stable shared base for experiments, migrations, and reference apps
- Make the repo easier to understand for new contributors and future adopters

### Why Now?

The repository has already crossed the point where toolkit framing is justified:

- multiple apps now exist with different user-facing purposes
- shared bootstrap, input lifecycle, speech, and application-interface layers already exist
- the project name and top-level documentation are being normalized around the toolkit concept

If product framing does not catch up to implementation reality, the repository will remain technically reusable but conceptually confusing.

### Opportunity

This PRD does not estimate external market size. The immediate opportunity is product and engineering leverage:

- faster delivery of additional accessibility desktop apps
- lower migration cost for NVDA-bound functionality
- clearer external positioning if the toolkit is later published or shared

### Alternatives

The practical alternatives today are:

- build each accessibility app independently
- keep relying on NVDA runtime assumptions
- assemble a custom stack from general-purpose GUI and TTS libraries without a shared app model

`accessibility-toolkit` differentiates itself through:

- keyboard and hotkey capture
- keyboard event handling pipeline
- speech and output scheduling
- mode switching and interaction control
- application interfaces
- demonstrated reuse across multiple app categories

## 5. Solution Overview

### High-Level Description

`accessibility-toolkit` will serve as the shared product identity for the current runtime and app platform in this repository. It will continue to host concrete reference applications while exposing a coherent toolkit story for contributors and future app builders.

### Core Product Capabilities

1. Keyboard and hotkey capture
- normalize native keyboard and hotkey input into shared models
- provide a consistent foundation for idle/active capture switching

2. Keyboard event handling pipeline
- support mode entry, exit, and active keyboard routing
- keep capture switching and event-handling state out of app-local reinvention

3. Speech and output scheduling
- provide a stable speech facade with backend and settings control
- provide centralized output sequencing behavior

4. Mode switching and interaction control
- provide shared rules for mode entry/exit and interaction control
- let different apps build consistent hotkey-driven interaction flows

5. Application interfaces
- provide common tray/menu behavior and settings access
- support utility-style app window lifecycle conventions

On top of these 5 shared capabilities, the toolkit also supports app-specific composition:

- keep domain logic inside each app
- allow remote-control, key echo, and graph navigation to coexist on the same shared runtime

### Reference User Flows

#### Flow A: Developer builds a new app on the toolkit

1. Developer adopts the toolkit runtime model
2. Developer wires app-specific services into shared input/output and application-interface layers
3. Developer defines mode entry, active handling, and exit behavior
4. App launches using shared runtime infrastructure

#### Flow B: User runs `nvda_remote`

1. User launches the app
2. User connects to an NVDA Remote relay
3. User enters control mode
4. Toolkit manages capture lifecycle and local speech infrastructure
5. App-specific logic handles remote forwarding and relay messaging

#### Flow C: User runs `access8graph`

1. User launches the tool app
2. User selects a `.graphml` file
3. User starts navigation mode
4. Toolkit manages input activation and speech output
5. App-specific graph-navigation logic drives spoken exploration

## 6. Success Metrics

### Primary Metric

- Number of distinct applications in the repository that use the shared toolkit runtime model without creating bespoke infrastructure forks

### Secondary Metrics

- Percentage of startup/runtime wiring that lives in shared toolkit layers rather than app-local duplication
- Coverage of shared toolkit behavior in tests
- Time and code volume required to add a new tool-style app
- Documentation consistency across README, architecture spec, and PRD

### Targets

Current:

- 3 apps use the shared foundation at varying depth
- toolkit framing exists but is still being normalized in docs and naming

Next milestone:

- all 3 current apps are clearly documented as toolkit consumers
- 1 additional app can be added without inventing a new runtime pattern
- top-level docs, build guidance, and product framing consistently reflect the toolkit identity

## 7. User Stories & Requirements

### Epic Hypothesis

If the current shared runtime is formalized as `accessibility-toolkit`, then developers and maintainers will build and evolve accessibility desktop apps faster and more consistently because keyboard and hotkey capture, keyboard event handling pipelines, speech and output scheduling, mode switching and interaction control, and application interfaces will already exist as reusable product capabilities.

### User Story 1: Shared Input Lifecycle

As an accessibility app developer, I want a shared idle/active keyboard lifecycle so I can implement hotkey-driven modes without writing custom capture-switching logic.

#### Acceptance Criteria

- Toolkit exposes a shared activation model for hotkey-driven mode entry and active keyboard handling
- Toolkit prevents idle hotkey capture and active full-keyboard capture from overlapping in normal operation
- Activation failures can be surfaced back to the app cleanly

### User Story 2: Shared Speech and Output

As an app developer, I want shared speech and output services so I can provide spoken feedback without binding my app directly to backend-specific code.

#### Acceptance Criteria

- Apps can use a stable speech facade for playback, cancelation, backend selection, and voice settings
- Output sequencing behavior is available through shared services
- Apps can reuse shared speech settings UI behavior

### User Story 3: Shared Application Interfaces

As a maintainer building multiple utility-style accessibility apps, I want common application interfaces so window lifecycle and settings access behave consistently across apps.

#### Acceptance Criteria

- Toolkit apps can use a shared desktop interface pattern
- Utility-style main windows can hide instead of exiting on close
- Shared menu actions for main panel, speech settings, and exit are reusable

### User Story 4: App-Specific Domain Isolation

As a toolkit maintainer, I want domain logic to stay outside the shared toolkit core so the toolkit remains reusable across different app categories.

#### Acceptance Criteria

- `nvda_remote`, `key_echo`, and `access8graph` keep domain behavior in app-local services and flows
- Shared toolkit code does not need to know remote protocol semantics or graph-navigation rules
- Shared services remain usable without importing app-specific modules

### User Story 5: Migration Support

As a developer migrating an accessibility workflow out of an NVDA-dependent environment, I want a reusable standalone desktop base so I can preserve interaction patterns while removing direct NVDA runtime dependencies.

#### Acceptance Criteria

- Toolkit documentation explains the role of shared input, output, and application-interface behavior
- Reference apps demonstrate both remote-control and non-remote use cases
- Migrated app logic can run without assuming NVDA runtime APIs

### Constraints

- Python 3.11+ is required
- Real runtime validation currently focuses on Windows and macOS
- NVDA Controller speech integration remains Windows-specific
- Existing NVDA Remote relay compatibility must remain intact for `nvda_remote`

### Edge Cases

- Some keys may need both system pass-through and app-side handling
- Some apps fit the utility-style application interface model more naturally than others
- Toolkit identity must not flatten meaningful differences between apps

## 8. Out of Scope

- Replacing NVDA Remote relay protocol with a new network protocol
- Building a plugin marketplace or dynamic plugin system
- Supporting every desktop platform immediately
- Providing a full visual design system for all accessibility apps
- Turning the toolkit into a hosted service or cloud platform
- Publishing a public distribution package in this phase
- Rewriting existing app logic only for abstraction aesthetics

## 9. Dependencies & Risks

### Technical Dependencies

- stable Windows and macOS adapter behavior
- shared speech backend support through `pyttsx3` and NVDA Controller
- wxPython desktop UI support
- continued compatibility between shared input models and app-specific needs

### External Dependencies

- NVDA Controller DLL on Windows for the NVDA-backed speech path
- NVDA Remote relay compatibility for `nvda_remote`
- GraphML inputs for `access8graph`

### Risks

#### Risk 1: The toolkit story becomes clearer than the actual boundaries

If naming and documentation move faster than code boundaries, the product may sound more reusable than it really is.

Mitigation:

- keep toolkit/app boundaries explicit in docs and code
- use current reference apps as concrete proof points
- avoid claiming unsupported generality

#### Risk 2: Platform assumptions leak back into app logic

If abstractions are incomplete, app code may reintroduce Windows- or macOS-specific assumptions.

Mitigation:

- keep HID-first rules as the default shared model
- continue testing adapter boundaries
- prefer shared lifecycle policies over app-local reinvention

#### Risk 3: Productization stops at documentation

If the repo is renamed but not treated as a real product surface, it will remain hard to adopt.

Mitigation:

- align naming, README, architecture spec, PRD, and build guidance
- use future app additions as a validation test for the toolkit model

## 10. Open Questions

- Should the repository remain a monorepo with reference apps, or eventually separate toolkit code from example applications?
- What is the intended long-term distribution model: internal toolkit, open-source repo, Python package, or all three?
- Which current shared application-interface behaviors should become a stable public API surface?
- What is the next candidate app that will validate whether the toolkit abstraction is strong enough?
