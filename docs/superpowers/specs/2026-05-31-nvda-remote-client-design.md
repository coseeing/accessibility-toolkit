# NVDA Remote Client Design

## Overview

This document defines the first implementation of a standalone NVDA Remote client for Windows. The client connects to an existing NVDA Remote relay endpoint and controls another computer that is already running NVDA Remote. The new client must run outside the NVDA Python runtime and keep input, output, control, and platform concerns modular so the design can be extended to other platforms later.

Version 1 targets Windows and uses Python for the application and core logic. The UI is built with `wxPython`. Local speech output may use `nvdaControllerClient64.dll` when NVDA is available on the local machine, but the application must remain functional even when local NVDA is not running.

## Goals

- Build a standalone client that can connect to an NVDA Remote relay and join a channel as a controlling client.
- Support real keyboard capture on Windows and forward keyboard events to the remote machine.
- Receive remote speech output and present it locally through a modular output pipeline.
- Support clipboard synchronization in both directions.
- Keep protocol, session, transport, input, output, and UI responsibilities separated.
- Avoid dependencies on NVDA's Python runtime APIs in the new application's core.

## Non-Goals for V1

- Implement follower mode for letting another machine control this client.
- Implement full braille output support.
- Implement production-quality tone and wave playback.
- Implement secure desktop handling and full SAS support.
- Implement URL handler integration.
- Implement full NVDA script and braille gesture compatibility.
- Support local relay server startup inside the client.
- Deliver non-Windows platform adapters.

## Recommended Architecture

The recommended architecture is a layered Python application with clear separation between pure client logic and Windows-specific adapters.

### Layers

#### `remote_core`

Pure client logic with no direct dependency on `wxPython`, Win32 hooks, clipboard APIs, or NVDA controller DLLs.

Responsibilities:

- Protocol definitions
- Serialization and deserialization
- Transport abstraction and relay connection handling
- Session state and connection lifecycle
- Message routing
- Domain models for normalized input and output events

#### `application`

Application services that coordinate the UI, core, and adapters.

Responsibilities:

- High-level use cases such as connect, disconnect, start control, pause control, and clipboard push
- Runtime state exposed to the UI
- Event propagation between core and UI
- Wiring dependencies together

#### `adapters`

Platform-specific or device-specific implementations behind stable interfaces.

Windows v1 adapters include:

- Keyboard capture
- Clipboard access
- Optional keyboard injection helpers
- NVDA controller DLL speech output
- Logging or null implementations for unsupported outputs

#### `app_wx`

Thin GUI shell built with `wxPython`.

Responsibilities:

- Main window and dialogs
- User-triggered actions
- Display of connection state and errors
- Status messages for local user feedback

The GUI must not own transport logic or protocol logic.

## Core Runtime Model

V1 should keep the concept of connection role but not duplicate NVDA's current object model directly. Internally, the application should retain a `mode` field for future extensibility, but the Windows v1 UI should not expose role selection. V1 always operates as a controlling client.

### Primary Runtime Objects

#### `ClientRuntime`

Top-level coordinator for the running application.

Responsibilities:

- Hold references to transport, session, adapters, and application state
- Activate and deactivate control mode
- Route normalized events between input capture, transport, and output services

#### `RemoteSession`

Represents a live relay session and owns session lifecycle state.

Responsibilities:

- Join a relay channel
- Validate protocol version compatibility
- Track connection state
- Handle ping, disconnect, MOTD, and join/leave events

#### `MessageRouter`

Receives decoded protocol messages and dispatches them to domain handlers.

Responsibilities:

- Map message types to handlers
- Translate inbound output-related messages to normalized output requests
- Keep routing logic independent from GUI and platform APIs

#### `ControlState`

State machine for input forwarding:

- `idle`
- `connected`
- `controlling`
- `suspended`

Meaning:

- `idle`: not connected
- `connected`: connected to relay but keyboard capture is not forwarding input
- `controlling`: keyboard capture is active and outbound key messages are sent
- `suspended`: transport remains connected but control forwarding is paused

This separation is required so users can stay connected without always surrendering the local keyboard.

## Message and Data Flow

### Connection Flow

1. The GUI gathers `host`, `port`, and `key`.
2. The application builds connection information with internal mode fixed to controlling behavior.
3. The transport establishes the TCP/TLS connection to the relay.
4. The session completes protocol negotiation and channel join.
5. Runtime state moves to `connected`.

### Control Flow

1. The user starts control from the GUI.
2. The application activates the Windows keyboard capture adapter.
3. Captured key events are normalized into platform-neutral `KeyEvent` objects.
4. `remote_core` maps `KeyEvent` objects into NVDA Remote `KEY` messages.
5. The transport sends the encoded messages to the relay.

This keeps capture logic separate from protocol encoding. Future platforms should only need a new capture adapter if they can produce the same normalized `KeyEvent` model.

### Output Flow

1. The transport receives a message.
2. The serializer decodes the payload.
3. `MessageRouter` dispatches based on protocol type.
4. Output-related handlers create normalized output requests.
5. `OutputManager` forwards those requests to the appropriate output adapter.

The GUI receives status events from the application layer only. It should not consume raw transport messages directly.

## Input Design

V1 requires true keyboard capture on Windows. A command-only or text-console control model is not sufficient.

### Input Abstraction

Define an `InputCapture` interface with operations similar to:

- `start()`
- `stop()`
- `set_listener(listener)`

The listener receives normalized `KeyEvent` objects containing at least:

- virtual key code
- scan code when available
- whether the key is extended
- press or release state

### Windows V1 Input Adapter

Implement `WindowsKeyboardCapture` as a Windows-specific adapter.

Responsibilities:

- Install and remove the keyboard hook
- Normalize captured events
- Avoid embedding NVDA Remote protocol details in the hook layer

The keyboard hook must live outside `remote_core`.

## Output Design

Output handling must be modular and must not require the local machine to run NVDA.

### `OutputManager`

Central application-facing coordinator for outputs.

Responsibilities:

- Receive normalized output requests from `MessageRouter`
- Dispatch to the correct output service
- Provide graceful fallback behavior when a specific output backend is unavailable

### Output Interfaces

#### `SpeechOutput`

Operations:

- `speak(payload)`
- `cancel()`
- `pause(is_paused)`

#### `BrailleOutput`

Reserved interface for future support. V1 should provide a null implementation.

#### `ToneOutput`

Reserved interface for future support. V1 should provide a logging implementation.

#### `WaveOutput`

Reserved interface for future support. V1 should provide a logging implementation.

#### `ClipboardService`

Operations:

- `set_text(text)`
- `get_text()`

## Speech Compatibility Strategy

Speech is the highest-risk output area because NVDA Remote currently serializes NVDA-specific speech command objects. The new client core must not depend on NVDA runtime internals to interpret those objects directly.

### Normalization Requirement

Inbound speech must be translated into an intermediate model before it reaches output adapters.

Define a `NormalizedSpeech` model with:

- `segments: list[SpeechSegment]`

V1 `SpeechSegment` types:

- `text`
- `break`
- optional prosody hints such as pitch changes, which may be preserved structurally even if a backend ignores them

This intermediate model becomes the contract between `remote_core` and speech backends.

### Windows V1 Speech Backend

Implement `NvdaControllerSpeechOutput`.

Behavior:

- When local NVDA is available, use `nvdaControllerClient64.dll` to present normalized speech through local NVDA.
- When local NVDA is unavailable, fail gracefully without breaking the client runtime.
- Surface status information to the GUI when useful, but do not make local NVDA a hard dependency for connection or control.

The DLL integration is an adapter concern. `remote_core` must not know how the speech is spoken.

## Clipboard Synchronization

Clipboard sync is in scope for V1.

### Inbound Clipboard

- Receive `SET_CLIPBOARD_TEXT`
- Route through `MessageRouter`
- Call `ClipboardService.set_text(text)`

### Outbound Clipboard

- Provide a user action in the GUI or menu to push the local clipboard to the remote session
- Read local clipboard text through `ClipboardService.get_text()`
- Send `SET_CLIPBOARD_TEXT` through transport

Clipboard logic should follow the same message-to-adapter pipeline as other outputs, not live directly in GUI code.

## Windows V1 Feature Scope

### Included

- Connect to an existing NVDA Remote relay endpoint
- Join a channel using host, port, and key
- Run as a controlling client
- `wxPython` GUI for connection management and control toggling
- Windows keyboard capture for remote control
- Receive remote speech and process it through the output pipeline
- Clipboard sync in both directions
- Session events: protocol mismatch, join/leave, ping, disconnect, and MOTD
- Stub or logging output implementations for braille, tone, and wave

### Excluded

- Follower mode
- Full braille rendering
- Production tone and wave playback
- Secure desktop and complete SAS workflows
- Local relay hosting
- Cross-platform adapter implementations

## Error Handling and Fallback Behavior

The runtime must treat most platform failures as degraded behavior rather than fatal errors.

Examples:

- Relay connection failure blocks session startup and must be shown clearly in the GUI.
- Keyboard hook startup failure prevents control mode and must be surfaced clearly.
- Local NVDA unavailable for speech should not terminate the session.
- Unsupported speech command details should degrade into the best available normalized representation rather than crash the router.
- Clipboard access failures should produce user-visible errors for the specific action but should not kill the transport session.

## Concurrency Model

Windows UI, network I/O, and keyboard capture must remain separated.

Guidance:

- Keep transport and socket I/O off the `wxPython` UI thread.
- Keep keyboard hook processing outside the UI thread.
- Marshal state changes and user-facing notifications through the application layer before they reach the GUI.
- Avoid direct GUI calls from transport or hook callbacks.

Exact thread and event-loop implementation can be decided during planning, but the layering constraint is mandatory.

## Test Strategy

V1 should include three levels of verification.

### Unit Tests

- Protocol encoding and decoding
- Message routing by type
- Speech normalization behavior
- Clipboard service contract behavior

### Integration Tests

- Connect to a relay server
- Join a channel
- Exchange `KEY`, `SPEAK`, `SET_CLIPBOARD_TEXT`, and `PING`
- Verify disconnect and protocol mismatch handling

### Manual Windows Tests

- GUI connection workflow
- Start and suspend control mode
- Basic key forwarding for navigation and typing keys
- Local NVDA present and absent scenarios
- Clipboard sync in both directions
- Reconnect and disconnect behavior

## Suggested Project Structure

```text
nvda_remote_client/
  src/
    app_wx/
      main.py
      app.py
      main_frame.py
      dialogs/
    application/
      services.py
      controller.py
      state.py
      events.py
    remote_core/
      protocol.py
      serializer.py
      connection_info.py
      transport/
      session/
      routing/
      models/
    adapters/
      windows/
        keyboard_hook.py
        keyboard_sender.py
        clipboard.py
        nvda_controller.py
      outputs/
        speech.py
        braille.py
        tone.py
        wave.py
      inputs/
        base.py
    tests/
      unit/
      integration/
  docs/
    superpowers/
      specs/
```

The exact filenames may change during implementation planning, but the high-level separation must be preserved.

## Open Decisions Intentionally Deferred to Planning

These items are deliberately left to the implementation planning step, not because they are unknown, but because they depend on local experimentation or packaging constraints:

- Exact keyboard hook implementation details on Windows
- Exact event bridge mechanism between worker threads and `wxPython`
- Packaging and distribution format
- Whether a second speech backend such as Windows SAPI should exist in v1 as an optional fallback

These are execution details, not unresolved product scope.

## Verification Notes

- Tested environment: Linux headless container (`x86_64`, Python 3.12.3). `DISPLAY` was unset and no Windows runtime was available.
- Automated tests: `pytest tests/unit tests/integration -v` passed with 53 tests.
- UI/manual Windows checks: `PYTHONPATH=src python3 -m app_wx.main` was attempted, but manual UI smoke was not executed because `wxPython` is not installed (`ModuleNotFoundError: No module named 'wx'`) and the environment is headless. Real Windows UI, keyboard hook, NVDA, and clipboard checks remain unverified here.
- Implemented but not manually validated in this environment: TCP/TLS relay socket framing, Windows low-level keyboard hook adapter, Windows clipboard backend, and `nvdaControllerClient64.dll` loading path.
- Known limitations: real end-to-end relay compatibility, real Windows UI behavior, keyboard hook behavior under Windows focus/security boundaries, actual clipboard updates, and NVDA DLL speech output still require Windows manual validation.
- Speech normalization cases intentionally unsupported in the v1 skeleton include unknown NVDA speech command objects and malformed command payloads beyond the simplified text and break handling.

## Final Recommendation

Build the client as a layered Python application with:

- `remote_core` for protocol, session, and routing
- `application` for use-case orchestration and state
- Windows adapters for input, clipboard, and optional NVDA speech output
- `wxPython` as a thin GUI shell

V1 should deliver a usable controlling client on Windows with modular boundaries that preserve future portability. The mandatory functional target is keyboard control, remote speech handling through a normalized pipeline, and bidirectional clipboard sync, with braille, tone, and wave preserved as extension points rather than full features.
