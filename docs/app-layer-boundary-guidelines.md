# App Layer Boundary Guidelines

## Purpose

This document defines a practical rule set for deciding what should be extracted into shared infrastructure first, and what can remain inside an app service for now.

Primary goal: future apps should be able to reuse the input/output foundation without depending on `nvda_remote`-specific behavior.

## Core Rule

Extract something into shared code when it represents a reusable capability, policy, or lifecycle that another app is likely to need unchanged.

Keep something in an app service when it is specific to that app's workflow, UI semantics, or remote business rules.

## Extract First

These should move into shared layers before splitting `NvdaRemoteAppService` aggressively.

### 1. Platform and adapter resolution

Move out of app entrypoints:
- platform checks such as `sys.platform == "darwin"` or `win32`
- lazy loading of Windows/macOS adapters
- runtime selection of keyboard capture, hotkey capture, clipboard, and speech backend factories

Why:
- every new app will need the same wiring problem solved
- this is infrastructure, not app logic

Current sources:
- `src/apps/nvda_remote/main.py`
- `src/apps/key_echo/main.py`

### 2. Input lifecycle abstractions

Extract shared control over:
- start/stop input capture
- start/stop hotkey capture
- attach listener / handler semantics
- shared normalized key event pipeline

Why:
- multiple apps will need input capture lifecycle
- apps should consume input services, not own low-level capture setup

Current sources:
- `src/application/keyboard.py`
- `src/adapters/inputs/base.py`
- parts of `src/apps/nvda_remote/service.py`

### 3. Output capability contracts

Extract and stabilize:
- speech playback contract
- tone output contract
- wave output contract
- braille output contract
- backend registry / capability discovery

Why:
- this is the actual reusable foundation for future apps
- current structure is still too speech-centric

Current sources:
- `src/adapters/outputs/interfaces.py`
- `src/application/output_service.py`
- `src/application/output_capabilities.py`
- `src/application/speech_backends.py`

### 4. Typed shared capability/runtime events

Extract shared event models only for reusable capability/runtime concerns, for example:
- input capture started/stopped
- hotkey capture started/stopped
- error notifications
- speech backend changes
- clipboard availability

Why:
- future apps should not depend on ad hoc `dict` payloads
- typed events make shared controllers and presenters easier to reuse
- remote connection/control state is not generic enough to belong here

Current sources:
- `src/apps/nvda_remote/service.py`
- `src/interop/protocol/routing/message_router.py`
- `src/interop/protocol/session/remote_session.py`

### 5. Process-level bootstrap concerns

Extract:
- logging setup
- config path policy
- runtime factory / composition root helpers

Why:
- these are cross-app startup concerns
- leaving them in each app entrypoint guarantees duplication

Current sources:
- `src/apps/nvda_remote/main.py`

## Input Event Contracts

The phrase "attach listener / handler semantics" refers to the event contract of the low-level capture layer, not UI callbacks.

### InputCapture listener contract

Applies to:
- `InputCapture.set_listener(...)` in `src/adapters/inputs/base.py`
- `KeyboardInputService.bind()` in `src/application/keyboard.py`

Current role:
- receives normalized `KeyEvent` instances
- lets the app decide whether to suppress or pass through the key
- acts as the bridge from low-level key capture into app behavior

Current usage:
- `src/apps/nvda_remote/service.py`
  - forwards keys to remote transport when controlling
  - returns `KeyEventDecision.SUPPRESS` or `PASS_THROUGH`
- `src/apps/key_echo/service.py`
  - converts pressed keys into local speech output
  - returns `KeyEventDecision.SUPPRESS`

Recommended shared contract:
- `InputCapture` accepts one listener at a time
- `set_listener()` may be called before `start()` or while running
- a new listener replaces the previous one
- `start()` must either require a listener first, or the upper layer must guarantee binding before start
- key events are delivered synchronously to the listener
- the listener returns `KeyEventDecision`
- `stop()` stops the event source but does not implicitly clear the listener
- listener failures must produce a defined failure policy instead of leaving hook state ambiguous

### HotkeyCapture handler contract

Applies to:
- `HotkeyCapture.set_handler(...)` in `src/adapters/inputs/base.py`

Current role:
- receives a hotkey trigger, not a full `KeyEvent`
- runs an app action such as toggling control mode

Current usage:
- `src/apps/nvda_remote/service.py`
  - invokes `_handle_hotkey_toggle`

Recommended shared contract:
- `HotkeyCapture` accepts one handler at a time
- `set_handler()` may be called before `start()` or while running
- a new handler replaces the previous one
- the handler is invoked when the configured hotkey fires
- hotkey delivery order and threading model must be documented
- `stop()` stops hotkey monitoring but does not implicitly clear the handler
- handler failures must produce a defined failure policy instead of leaving hotkey state ambiguous

## Keep In App Service For Now

These can stay inside `NvdaRemoteAppService` or other app services until a second app proves they are shared.

### 1. App-specific user workflow

Keep:
- connect / disconnect flow specific to NVDA Remote
- start control / stop control UX behavior
- local stop key semantics for this app
- clipboard push command as part of the remote-control workflow

Why:
- these are not generic input/output capabilities
- they belong to the `nvda_remote` app's use case

### 2. Remote protocol business rules

Keep:
- what to send when controlling
- when control state becomes active
- how `channel_joined`, `version_mismatch`, or remote status affect this app
- remote-specific events such as:
  - `RemoteConnectionStateChanged`
  - `RemoteControlStateChanged`
  - `RemoteSessionJoined`
  - `RemoteVersionMismatch`

Why:
- these rules are specific to the remote-control domain
- another app may use the same I/O foundation without using relay transport at all

### 3. Screen-specific controller surface

Keep:
- methods exposed only because the NVDA Remote UI needs them
- view synchronization behavior tightly coupled to a given screen

Why:
- these should only be extracted after a second screen or app needs the same shape

## Decision Checklist

Before extracting code from an app service, ask:

1. Would a future app need this behavior without knowing anything about NVDA Remote?
2. Is this about a reusable capability or only about this app's workflow?
3. Does this code mention transport protocol, control state, or remote-specific commands?
4. Would extracting it reduce duplication across app entrypoints or future apps?
5. Can the extracted interface be named without using the current app's name?

Decision rule:
- If answers 1, 2, 4, and 5 are mostly yes, extract it.
- If answer 3 is yes, it usually stays app-specific.

## Immediate Refactor Priority

Do these first:

1. Extract shared bootstrap/provider logic from app entrypoints.
2. Stabilize reusable input/output interfaces and capability boundaries.
3. Introduce typed events instead of free-form status dictionaries.
   Scope them carefully: shared capability events in shared layers, remote domain events in remote-specific layers.

Do not prioritize this yet:

1. Splitting `NvdaRemoteAppService` into many small classes only for style.
2. Moving remote-control business rules into shared code before a second app needs them.

## Practical Target State

Future apps should be able to do this:

- choose input capture through shared providers
- choose output capabilities through shared registries
- subscribe to typed shared capability events
- build their own app-specific workflow without importing `nvda_remote` service logic

If that is possible, the app layer is independent enough even if `NvdaRemoteAppService` remains somewhat large internally.
