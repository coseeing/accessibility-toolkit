# Accessibility Toolkit Functional Package Reorganization Design

## Overview

This refactor changes `accessibility_toolkit` from a technical-layer-oriented directory structure to one organized around functional domains that accessibility application users can recognize. The goal is for users to find APIs according to the task they want to perform—input, output, scheduling, interaction, events, and remote connectivity—without first having to understand internal architecture terms such as `application`, `interop`, or `adapters`.

This is a complete breaking refactor. All existing paths will be removed; no compatibility shims, deprecated re-exports, or temporary facades will be created. Repository apps, UI, tests, documentation, and packaging configuration must all move to the new paths in the same change.

## Background and Problem

The current implementation of a single feature—keyboard input handling—is spread across three technical layers:

- `interop.key`: data models such as `KeyEvent` and `HID`.
- `adapters.inputs`, `adapters.windows`, and `adapters.macos`: capture contracts and platform implementations.
- `application.input`: the input pipeline, policies, and service.

This arrangement describes internal dependencies well, but a package user must cross several abstraction layers to use one capability. The same issue applies to speech/output, mode lifecycle, and the remote protocol.

## Goals

- Make functional domains the first-level package boundaries in `accessibility_toolkit`.
- Let typical users find APIs through `input`, `output`, `scheduling`, `interaction`, `events`, `remote`, and `runtime`.
- Place platform implementations beneath the features they serve; remove the global `adapters` package.
- Promote the scheduler from its current output-specific location to a neutral shared capability that can serve both input and output.
- Preserve existing runtime behavior and application features; this refactor primarily changes package boundaries, imports, and the public API.
- Ensure `accessibility-toolkit-core` distributes only the core Python namespace and does not include the wx package.

## Non-Goals

- Do not add input scheduling behavior such as debouncing, repeat-key aggregation, or delayed commands in this change; only establish the package boundary for their future use.
- Do not change keyboard pipeline, speech queue, relay protocol, or mode behavior.
- Do not extract `remote` into a separate distribution package.
- Do not move or reorganize the UI structure in `accessibility_toolkit_wx`; it remains a separate UI package.
- Do not replace the existing typed events with a new general-purpose event bus.

## Design Principles

### Function Before Implementation Layer

First-level package names must answer “what does the user want to do?” rather than “which architectural layer contains this code?” Internal files may still contain ports, drivers, or platform-specific details, but they belong inside the package for their functional domain.

### Platform Implementations Belong to Their Features

Windows/macOS keyboard hooks are input; NVDA Controller and pyttsx3 are speech output; clipboard support is output. They are no longer gathered under a global `adapters` package, so users select a capability before selecting a platform.

### Events Are Not a Data-Model Catch-All

Events remain in their owning domain: keyboard events in `input.events` and relay protocol events in `remote.events`. The root `events` package contains only cross-functional lifecycle events that matter to applications and UIs, such as mode, capture, engine, and error state changes.

### Scheduling Is a Neutral Foundation

`Scheduler` is currently first consumed by output, but input will also need scheduled, cancellable, or delayed work. The `scheduling` API, types, parameters, and documentation must not carry speech- or output-specific semantics.

### Remote Remains in Core

Remote remains a core functional module. It must stay self-contained, and `input`, `output`, `scheduling`, `interaction`, and `events` must not depend on it. Applications may combine remote with other features. This rule keeps future extraction into a separate distribution package limited to the `remote` boundary.

## Target Directory Structure

```text
src/accessibility_toolkit/
  input/
    __init__.py
    hid.py
    events.py
    capture.py
    activation.py
    pipeline.py
    policies.py
    results.py
    service.py
    windows/
      __init__.py
      hid_map.py
      hotkey.py
      keyboard_hook.py
      native_key_context.py
    macos/
      __init__.py
      event_tap.py
      hid_map.py
      hotkey.py
      keyboard_hook.py
      keymap.py
      permissions.py

  output/
    __init__.py
    queue.py
    capabilities.py
    clipboard.py
    interfaces.py
    ports.py
    tone.py
    wave.py
    braille.py
    windows/
      __init__.py
      clipboard.py
    speech/
      __init__.py
      commands.py
      sequence.py
      null.py
      service.py
      settings.py
      settings_store.py
      json_settings_store.py
      runtime_settings.py
      settings_facade.py
      backends.py
      drivers/
        __init__.py
        pyttsx3.py
      windows/
        __init__.py
        nvda_controller.py
        vendor/

  scheduling/
    __init__.py
    scheduler.py

  interaction/
    __init__.py
    modes.py

  events/
    __init__.py
    application.py

  remote/
    __init__.py
    connection.py
    messages.py
    serializer.py
    events.py
    routing/
      __init__.py
      message_router.py
    session/
      __init__.py
      remote_session.py
    transport/
      __init__.py
      base.py
      relay.py

  runtime/
    __init__.py
    environment.py
    platform.py
    output.py
    runtime_parts.py
```

`windows/` and `macos/` are subdirectories of a feature package. Their `__init__.py` files should export only implementations supported for that feature on that platform. Runtime platform-selection logic that does not belong to one feature remains in `runtime.platform`.

The NVDA Controller driver owns its vendored DLL and resolves it relative to `output/speech/windows/nvda_controller.py` using `Path(__file__)`. It must not import `runtime.environment` for resource lookup. PyInstaller must preserve the same package-relative `vendor/nvda/x64` layout so the lookup works in source, installed wheels, and frozen applications.

## Functional Boundaries

### `input`

Responsible for obtaining input from platforms, normalizing it, managing the capture lifecycle, and executing the shared keyboard pipeline.

Its public concepts include:

- `HID`, `KeyEvent`, and `CapturedKeyEvent`
- `InputCapture` and `HotkeyCapture`
- `KeyboardInputService` and `KeyEventHandler`
- `InputActivationUseCase`
- `KeyboardPipelineResult` and `AppKeyEventResult`
- Active-key and system-toggle policies
- Windows/macOS keyboard hooks, hotkeys, HID mappings, and macOS input-permission implementations

Input does not contain application-specific command semantics and is not responsible for speech or other feedback.

### `output`

Responsible for presenting application feedback to users, including speech, tone, wave, braille, and clipboard support.

Its public concepts include:

- `QueuedService` and its output mode
- `Capabilities`, speech ports, and output interfaces
- `ClipboardService`
- `SpeechService`, speech backends, settings, and settings stores
- `SpeechRuntimeSettingsCoordinator` and `SpeechSettingsFacade`
- `JsonSpeechSettingsStore`
- `SpeechSequence` and speech commands
- Tone, wave, and braille output
- pyttsx3 and the Windows NVDA Controller implementation

Output uses `scheduling` for work ordering and cancellation, but does not own the scheduler implementation.

### `scheduling`

Responsible for general queued, cancellable work that can wait for completion and use timeouts.

Its public concepts include:

- `Scheduler`
- `CancellationToken`
- `ScheduledFuture`
- `EventCallbacks`

Its first consumer is the output speech queue and backend, while input may later use the same API for debouncing, repeat-key aggregation, delayed activation, or cancellable processing. This package must not import `input`, `output`, `interaction`, or `remote`.

### `interaction`

Responsible for the non-UI interaction contexts, state, and rules of an accessibility application. It answers “what does this input mean in the current context, and how should the application transition its interaction state?” rather than “how is a key acquired?” or “how is feedback spoken?”

This refactor includes:

- `ModeManager` and mode types
- Shared lifecycle coordination needed for mode entry, exit, switching, and rollback

It may later contain shared command routing or interaction/session state. It must not contain platform hooks, speech drivers, wx UI, or application-specific navigation rules.

### `events`

Responsible for cross-functional typed lifecycle events that are meaningful to applications and UIs.

This refactor includes:

- `ErrorRaised`
- `SpeechEngineChanged`
- `InputCaptureChanged`
- `HotkeyCaptureChanged`
- `ClipboardAvailabilityChanged`
- `ModeChanged`
- `AppEvent`

Keyboard data events remain in `input.events`; remote protocol events remain in `remote.events`.

### `remote`

Responsible for the relay protocol, serialization, transport, session, and message routing. Applications may use it, but no other core feature package may depend on it.

Its public concepts include:

- Connection information and remote messages
- Protocol serializer and events
- Message router
- `RemoteSession`
- Transport interfaces and relay transport

### `runtime`

Responsible for application composition, environment setup, platform selection, and shared runtime parts. It is the composition layer and may depend on all feature packages; feature packages must not depend on runtime.

## Existing File Migration Map

| Current location | Target location |
|---|---|
| `interop/key/*` | `input/events.py` or the corresponding module under `input/` |
| `adapters/inputs/*` | `input/capture.py`, `input/events.py` |
| `adapters/windows/{keyboard_hook,hotkey,hid_map,native_key_context}.py` | `input/windows/` |
| `adapters/macos/{event_tap,keyboard_hook,hotkey,hid_map,keymap,permissions}.py` | `input/macos/` |
| `application/input/*` | `input/{activation,pipeline,policies,...}.py` |
| `application/output/scheduler.py` | `scheduling/scheduler.py` |
| `application/output/{service,capabilities,ports,clipboard}.py` | Corresponding modules under `output/` |
| `interop/speech/*` | `output/speech/{commands,sequence}.py` |
| `application/output/speech/*` | Corresponding modules under `output/speech/` |
| `application_support/{speech_runtime_settings,speech_settings_facade}.py` | `output/speech/{runtime_settings,settings_facade}.py` |
| `adapters/config/json_speech_settings.py` | `output/speech/json_settings_store.py` |
| `adapters/outputs/*` | Corresponding modules under `output/` or `output/speech/` |
| `adapters/outputs/ref𦳒.txt` | Delete; it is an unused, non-importable reference artifact with no repository consumers |
| `adapters/windows/clipboard.py` | `output/windows/clipboard.py` |
| `adapters/windows/nvda_controller.py` and its vendored DLL | `output/speech/windows/nvda_controller.py` and `output/speech/windows/vendor/` |
| `application_support/{mode_manager,mode_types}.py` | `interaction/modes.py` |
| `application/events.py` | `events/application.py` |
| `interop/protocol/*` | Corresponding modules under `remote/` |
| `runtime/*` | Remain under `runtime/`; only imports change |

Implementations may retain multiple existing files according to the size of a functional area. The merged filenames in this table show functional ownership and do not require logic to be combined solely for this move.

## Public API

Every first-level feature package, plus the public `output.speech`, `input.windows`, `input.macos`, `remote.routing`, `remote.session`, and `remote.transport` subpackages, must define a clear, stable public API and explicit `__all__` in its `__init__.py`. Typical use cases must not require importing private or implementation-oriented paths. Driver modules and vendored-resource directories are implementation paths and do not require root-level re-exports.

Expected usage:

```python
from accessibility_toolkit.input import KeyEvent, KeyboardInputService
from accessibility_toolkit.input.windows import WindowsKeyboardHook
from accessibility_toolkit.output import QueuedService
from accessibility_toolkit.output.speech import SpeechSequence, SpeechService
from accessibility_toolkit.scheduling import Scheduler
from accessibility_toolkit.interaction import ModeManager
from accessibility_toolkit.remote import RemoteSession
```

Platform- or driver-specific imports may use implementation paths within their feature, for example `output.speech.drivers.pyttsx3`. Users must not need to find a capability through `adapters`.

## Dependency Rules

```text
output ──────────────> scheduling
interaction ─────────> input, events
remote ──────────────> output.speech (wire-format speech models)
runtime ─────────────> input, output, scheduling, interaction, events, remote

input ··············> scheduling (permitted future dependency; absent in this refactor)
```

- `scheduling` does not depend on any feature package.
- `events` does not depend on any feature package.
- No other core feature package may depend on `remote`.
- `remote` may depend on stable `output.speech` command and sequence models required by the existing wire format; output must not depend on remote.
- `runtime` may compose all features, but no feature package may depend on it.
- The NVDA Controller driver resolves its package-owned DLL without importing `runtime`.
- `accessibility_toolkit_wx` may depend on the core public API; core must not depend on wx.
- Application-specific domain logic remains in `apps/*` and does not move into the toolkit because of this refactor.

## Breaking Migration Rules

- Delete the `application/`, `application_support/`, `interop/`, and `adapters/` packages.
- Do not create re-exports, import forwarding, warnings, or compatibility modules at old paths.
- Update every import in `src/apps`, `src/ui`, `tests`, and documentation.
- Use ripgrep to verify that the following old namespaces are no longer usable imports in source or tests: `accessibility_toolkit.application`, `accessibility_toolkit.application_support`, `accessibility_toolkit.interop`, and `accessibility_toolkit.adapters`. Historical documents may mention them only when explicitly describing the former architecture.

## Packaging and Documentation

Package discovery in `packages/accessibility-toolkit-core/pyproject.toml` must change from the broad `accessibility_toolkit*` to only include:

```toml
include = ["accessibility_toolkit", "accessibility_toolkit.*"]
```

This prevents `accessibility_toolkit_wx` from being included in the core distribution because it has the same prefix.

Update package-data declarations in both the core package metadata and the root development package metadata to point at `accessibility_toolkit.output.speech.windows` and its new `vendor/nvda/x64/*.dll` location. Update `packaging/windows_apps.spec` to use the new DLL source/destination and hidden-import module paths. Packaging must not retain any reference to the removed `adapters` tree.

The README and architecture documents must replace their outdated `application/interop/adapters/bootstrap` layout with the new functional package structure, and add short usage examples beginning with input, output, and scheduling.

## Acceptance Criteria

- `src/accessibility_toolkit` contains only the first-level functional packages defined in this specification and its root `__init__.py`.
- No `accessibility_toolkit.application`, `application_support`, `interop`, or `adapters` directories or importable modules exist.
- Apps, UI, unit tests, and integration tests use the new import paths and pass.
- `Scheduler` is located in `accessibility_toolkit.scheduling` and does not depend on output or input.
- Every first-level feature package and public nested package identified by this specification has a deliberate `__init__.py` and `__all__` public API.
- `remote` remains in core, and no core feature package other than runtime imports it.
- No core feature package imports `runtime`; in particular, the NVDA Controller driver resolves its DLL from its own package directory.
- The `accessibility-toolkit-core` wheel and sdist do not contain `accessibility_toolkit_wx`.
- The Windows executable specification and Python package metadata include the NVDA Controller DLL from its new output/speech location.
- The README, Traditional Chinese README, specifications, and package-migration documentation reflect the new structure.

## Verification

At a minimum, run:

```bash
python -c "import accessibility_toolkit"
pytest tests/unit tests/integration -v
rg -n "^(from|import) accessibility_toolkit\.(application|application_support|interop|adapters)" src tests
rg -n "adapters[./]|accessibility_toolkit\.adapters" packages packaging pyproject.toml
```

The final two commands must find no active import, package-data path, hidden import, or bundled-file path that refers to a removed namespace. Historical design documents may describe the former architecture when they are explicitly historical rather than current usage.
