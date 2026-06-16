# accessibility-toolkit Architecture Spec

## 1. Purpose

This document explains the current system architecture of `accessibility-toolkit`.

It is intended for new contributors and collaborators who need to understand:

- what the toolkit is responsible for
- what belongs in shared layers versus app-specific layers
- how the current reference apps use the toolkit
- why the architecture evolved into its current shape

This is an architecture and system-context document. It is not the primary onboarding guide and it is not the product requirements document.

## 2. System Positioning

`accessibility-toolkit` is a shared desktop runtime for accessibility applications.

Its core architectural responsibilities are:

- capture keyboard and hotkey input across supported platforms
- normalize input into shared models
- manage mode switching and interaction control
- route events through a shared keyboard event handling pipeline
- provide reusable speech and output scheduling services
- provide reusable application interface behavior

The toolkit is currently exercised by three reference apps:

- `access8graph`
- `key_echo`
- `nvda_remote`

## 3. Core Toolkit Capabilities

### 3.1 Keyboard and Hotkey Capture

The toolkit provides two capture concepts:

- `HotkeyCapture`
  - used while the app is idle and waiting for mode entry
- `InputCapture`
  - used while the app is active and handling full keyboard input

Platform adapters are responsible for capturing native events and converting them into shared event models. Business meaning is intentionally left out of the adapter layer.

### 3.2 HID-First Input Model

The toolkit standardizes on a HID-first model for keyboard identity.

Why this matters:

- shared app logic no longer depends on Windows-only `vk/scan/extended` semantics
- Windows and macOS can participate in the same app-level rules
- legacy protocol compatibility is isolated to the boundary that needs it

Current rule:

- shared layers and app logic should reason in HID usages
- only `nvda_remote` converts HID input back into legacy relay key payloads

### 3.3 Mode Switching and Interaction Control

The toolkit uses a shared lifecycle model:

- `idle`
  - `HotkeyCapture` is active
  - app waits for an enter-mode hotkey
- `active`
  - `InputCapture` is active
  - app handles general key events and exit behavior

This lifecycle is coordinated by shared logic so apps do not each invent their own capture-switching model and interaction-control flow.

Key shared components:

- `InputActivationUseCase`
  - owns capture switching and rollback on failure
- `ModeManager`
  - owns current active mode and routes active events

### 3.4 Keyboard Event Handling Pipeline

The toolkit separates two concerns that were previously conflated:

- should an event be sent to the operating system?
- did the app handle the event?

Current result model:

- `AppKeyEventResult`
  - app-handling semantics
- `KeyboardPipelineResult`
  - final system-facing result, including `send_to_system`

This allows valid combinations such as:

- system still receives the key
- app also performs local behavior

That is important for cases such as Windows `Num Lock`.

### 3.5 Speech and Output Scheduling

The toolkit provides:

- `SpeechService`
  - backend selection
  - voice/rate/pitch/volume settings
  - speech sequence playback
- `QueuedOutputService`
  - higher-level output entrypoint
  - output sequencing behavior
  - a future extension point for non-speech outputs

The shared output model allows apps to produce spoken feedback without rewriting backend-specific logic in each app.

### 3.6 Application Interfaces

The toolkit includes reusable desktop application interface behavior for wxPython apps.

The interface supports:

- tray or menu-bar style app presence
- main panel lifecycle
- speech settings panel access
- hide-on-close behavior for utility-style apps

This is what makes `key_echo` and `access8graph` feel like related tools instead of completely separate shells.

## 4. Toolkit Boundaries

This is the most important architectural boundary in the repository.

### 4.1 What Belongs to the Toolkit

The toolkit owns:

- platform input/output adapters
- shared input normalization and capture contracts
- mode switching and interaction-control rules
- keyboard event handling pipeline
- speech and output scheduling services
- shared bootstrap/runtime wiring
- reusable application interface behavior

### 4.2 What Does Not Belong to the Toolkit

The toolkit does not own:

- NVDA Remote session semantics
- remote relay message handling rules
- graph-navigation business rules
- app-specific user flows
- app-specific validation or domain state

These belong in app-local modules and services.

### 4.3 Why This Boundary Matters

Without this separation:

- platform logic leaks into app behavior
- app-specific rules harden into fake "shared" abstractions
- adding a new app becomes expensive because the shared layer is no longer trustworthy

The architecture is intentionally shaped to keep the shared toolkit reusable while allowing the apps themselves to remain meaningfully different.

## 5. Reference Apps and Their Roles

### 5.1 `access8graph`

Role:

- prove the toolkit can host a non-remote accessibility tool

App-specific responsibilities:

- GraphML loading
- MRT model creation
- navigation commands and spoken graph exploration

Toolkit responsibilities used by the app:

- input activation
- keyboard event handling pipeline
- speech and output scheduling
- application interfaces and speech settings UI

### 5.2 `key_echo`

Role:

- prove the toolkit's shared input and speech infrastructure can power a minimal local app

App-specific responsibilities:

- echo-mode behavior
- keydown-to-speech mapping

Toolkit responsibilities used by the app:

- capture lifecycle
- keyboard event handling pipeline
- speech backend management
- application interface behavior

### 5.3 `nvda_remote`

Role:

- provide the original remote-control use case that motivated the project

App-specific responsibilities:

- relay transport and session handling
- remote key forwarding rules
- remote speech consumption
- clipboard synchronization behavior

Toolkit responsibilities used by the app:

- shared input model
- shared output model
- speech backend management
- runtime/bootstrap wiring

Special case:

- `nvda_remote` is the only current app that still needs the legacy relay compatibility boundary

## 6. Shared Execution Flow

### 6.1 Startup Flow

Each app follows the same high-level runtime shape:

1. initialize logging and runtime paths
2. resolve platform-specific adapters and backend options
3. create output scheduler and speech service
4. create queued output service
5. create app-specific service
6. create keyboard input service
7. create wx app / interface / frames

This keeps platform policy, runtime policy, and app-specific business wiring separate.

### 6.2 Input Flow

Shared input flow:

1. platform adapter captures native event
2. adapter emits shared key event structures
3. app service evaluates system pass-through policy
4. mode manager or active handler performs app logic
5. app service assembles `KeyboardPipelineResult`
6. adapter decides whether to suppress or pass through

### 6.3 Output Flow

Shared output flow:

1. app behavior produces a speech/output request
2. request goes through `QueuedOutputService`
3. queued service routes directly or sequentially depending on output mode
4. `SpeechService` uses the selected backend
5. backend scheduler handles chunk-level playback

## 7. Design Evolution

The repository did not begin as a general toolkit. The current architecture is the result of several concrete pressure points.

### 7.1 Standalone NVDA Remote Client

Initial goal:

- build an NVDA Remote client without depending on NVDA Python runtime internals

Architectural result:

- protocol and platform concerns were separated from the start

### 7.2 Shared Input/Output Extraction

Pressure:

- `key_echo` demonstrated that input and output could not remain remote-specific

Architectural result:

- speech, keyboard input, and output capability layers became shared services

### 7.3 Shared Bootstrap

Pressure:

- multiple apps exposed repeated startup, platform resolution, and runtime policy code

Architectural result:

- `bootstrap.platform` and `bootstrap.runtime` centralized shared runtime wiring

### 7.4 Unified Mode Lifecycle

Pressure:

- different apps were drifting in how they entered and exited active keyboard handling

Architectural result:

- shared activation use cases and mode management became first-class

### 7.5 HID-First Model

Pressure:

- Windows-oriented key semantics were not a stable long-term core model

Architectural result:

- shared logic moved to HID-first keyboard identity

### 7.6 Application Interface Platform

Pressure:

- `access8graph` and `key_echo` needed reusable application interface behavior

Architectural result:

- the repository became a toolkit for multiple accessibility desktop apps rather than a single client with extras

## 8. Current Source Mapping

The architecture maps to the repository roughly like this:

- `src/adapters/`
  - platform-specific implementations
- `src/application/`
  - shared input, output, keyboard, and speech behavior
- `src/bootstrap/`
  - shared runtime/bootstrap wiring
- `src/interop/`
  - shared protocol, transport, key, and speech models
- `src/apps/`
  - app-specific composition
- `src/apps/shared/`
  - reusable interface, mode, and controller helpers
- `src/ui/`
  - wxPython UI

The key principle is not the folder names themselves. The key principle is that shared runtime behavior stays shared, and domain behavior stays with the app that owns it.
