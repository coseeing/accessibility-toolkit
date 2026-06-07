# Speech Backend Selection Design

## Overview

This document defines the design for letting the Windows GUI choose and switch the local speech output backend at runtime. The feature applies to the standalone NVDA Remote client and does not affect relay connectivity, keyboard forwarding, clipboard sync, or session state.

The GUI will expose a dropdown with exactly two backend choices:

- `NVDA Controller`
- `pyttsx3`

The selected backend must be switchable while a relay session is already connected. Switching backends must stop the currently active speech output cleanly and route subsequent speech, cancel, and pause requests to the newly selected backend without reconnecting the relay session.

## Goals

- Let the user choose the local speech backend from the Windows GUI.
- Support runtime switching while connected to a relay session.
- Keep relay/session/control logic independent from the specific speech backend implementation.
- Preserve the existing modular `SpeechOutput` abstraction.
- Continue to support `NVDA Controller` when local NVDA is running.
- Provide a self-contained `pyttsx3` backend for cases where local NVDA is not desired or not available.

## Non-Goals

- Add automatic backend detection or `auto` mode.
- Add macOS or Linux speech backends in this feature.
- Change the NVDA Remote protocol.
- Change keyboard capture, hotkey handling, or clipboard sync behavior.
- Add a second speech provider selection UI elsewhere in the application.

## Recommended Architecture

The recommended design is a small backend manager in the application layer plus two concrete speech output adapters under `adapters`.

### Layers

#### `interop`

No change to the core protocol/session/routing responsibilities except that `CANCEL` and `PAUSE_SPEECH` continue to route into the generic speech output interface.

Responsibilities remain:

- Decode inbound protocol messages
- Route `SPEAK`, `CANCEL`, `PAUSE_SPEECH`, and clipboard messages to application services
- Keep protocol logic independent from GUI and platform APIs

#### `application`

Add a speech backend manager responsible for the active speech output implementation.

Responsibilities:

- Hold the selected backend id
- Create and replace the active `SpeechOutput` backend
- Cancel existing output during backend switches
- Expose the active backend name/state to the UI

#### `adapters`

Add concrete Windows speech backend implementations:

- `NvdaControllerSpeechOutput`
- `Pyttsx3SpeechOutput`

#### `ui`

Add a dropdown control that lists the two supported backends.

Responsibilities:

- Render the available backend list
- Notify the controller when the user changes the selection
- Show the currently selected backend

## Speech Backend Model

### Backend IDs

Use stable internal backend ids rather than storing UI labels directly.

- `nvda_controller`
- `pyttsx3`

The UI should display user-facing labels, but the application should persist and exchange backend ids internally.

### Backend Selection Rules

- The dropdown must always show both options.
- The default selection should be `NVDA Controller` on Windows.
- Switching the dropdown while connected must take effect immediately.
- Switching away from the current backend must first call `cancel()` on the active backend to avoid lingering speech.
- Switching backends must not disconnect the relay session or reset control state.

## Runtime Flow

### Initial Startup

1. UI initializes with the speech backend dropdown.
2. The application creates the initial speech backend from the selected backend id.
3. The active `SpeechOutput` is passed into the controller and output manager.
4. The relay session behaves exactly as before.

### Runtime Switch

1. The user changes the dropdown while connected or disconnected.
2. The UI sends the new backend id to the application layer.
3. The application layer calls `cancel()` on the current backend.
4. The application layer instantiates the new backend.
5. The controller and output manager start using the new backend for all subsequent `SPEAK`, `CANCEL`, and `PAUSE_SPEECH` requests.
6. The relay session remains connected.

### Inbound Speech Flow

1. The transport receives a `SPEAK` message.
2. `MessageRouter` normalizes it into `NormalizedSpeech`.
3. `OutputManager` forwards the normalized speech to the active backend.
4. The current backend speaks the text.

### Inbound Cancel/Pause Flow

1. The transport receives a `CANCEL` or `PAUSE_SPEECH` message.
2. `MessageRouter` dispatches the request to the application output manager.
3. The current backend receives `cancel()` or `pause(is_paused)`.

## Backend Specifications

### `NvdaControllerSpeechOutput`

This backend keeps the current NVDA controller DLL integration.

Responsibilities:

- Load the vendored NVDA controller DLL using the existing runtime resource path
- Speak normalized text through the NVDA controller API
- Cancel current speech when requested

Notes:

- This backend remains preferred when the user wants NVDA to handle local speech.
- It requires local NVDA to be running for actual speech output.

### `Pyttsx3SpeechOutput`

This backend provides local system TTS via `pyttsx3`.

Responsibilities:

- Initialize the system TTS engine
- Speak normalized text using the local Windows voice engine
- Stop current speech when `cancel()` is called
- Provide best-effort handling for `pause(is_paused)`; if the engine does not support true pause/resume, document the limitation and treat it as no-op or stop-only behavior

Notes:

- This backend is intended to work without NVDA running locally.
- It should be implemented in a way that does not require the NVDA controller DLL.

## UI Design

### Dropdown

Add a labeled dropdown to the main Windows window, near the connection controls.

The dropdown items are:

- `NVDA Controller`
- `pyttsx3`

The control should:

- default to the current configured backend
- remain enabled while connected
- apply changes immediately when the user selects a different backend

### Status Handling

The UI should not silently switch backends behind the user’s back.

Recommended behavior:

- If a backend switch succeeds, the dropdown stays on the new selection.
- If a backend switch fails, keep the old backend active and show an error dialog.
- If the current backend is unavailable at startup, surface a clear error and fall back only if the application explicitly chooses to do so.

## Configuration

Persist the selected backend id in the client configuration so the choice survives restarts.

Recommended persistence rule:

- Store the backend id, not the UI label
- Read the stored backend id during startup
- If the stored value is unknown, fall back to `nvda_controller`

## Error Handling

- If `NVDA Controller` is selected but the DLL cannot be loaded, show a clear error message and keep the current backend active.
- If `pyttsx3` fails to initialize, show a clear error message and keep the current backend active.
- If a switch happens while speech is active, cancel the old backend before instantiating the new one.
- If the new backend fails to initialize, restore the previous backend and continue.

## Testing Strategy

### Unit Tests

- Backend selection and backend id persistence
- UI dropdown events dispatching into the controller/application layer
- Runtime backend switching cancels the previous backend
- `NvdaControllerSpeechOutput` continues to speak and cancel correctly
- `Pyttsx3SpeechOutput` speaks and stops correctly

### Integration Tests

- Start the app with `NVDA Controller`, switch to `pyttsx3`, and confirm subsequent speech routes to the new backend
- Start the app with `pyttsx3`, switch to `NVDA Controller`, and confirm routing changes without disconnecting the relay session
- Verify `CANCEL` still interrupts current speech after switching

### Manual Windows Checks

- Connect to a relay session and verify the dropdown is visible
- Switch from `NVDA Controller` to `pyttsx3` while speech is playing
- Switch back to `NVDA Controller` while connected
- Confirm the relay connection stays alive across backend changes
- Confirm keyboard and clipboard behavior are unaffected

## Implementation Notes

- Keep the speech backend manager in `application`, not in `ui`.
- Keep backend-specific code isolated in `adapters`.
- Do not let the UI instantiate backend implementations directly.
- Preserve the existing `SpeechOutput` interface so the router/output manager remains stable.
- Keep the runtime resource helper for vendored DLL loading; the new system TTS backend should not depend on it.
