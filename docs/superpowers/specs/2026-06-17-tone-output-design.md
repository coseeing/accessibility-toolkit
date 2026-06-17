# Tone Output Design

Date: 2026-06-17

## Goal

Add real tone output to the client and make remote tone playback work for `nvda_remote`, while keeping the protocol compatible with current NVDA Remote behavior.

This work must satisfy these requirements:

- A remote tone sent by another client is played locally.
- The wire protocol for `nvda_remote` matches NVDA Remote's existing `TONE` message shape.
- Tone playback uses the default output device only.
- NVDA runtime dependencies are not imported into this repository.
- Speech serialization remains speech-only; tone is not added to `SpeechSequence`.

## Current State

The repository already has output capability separation:

- `speech` is modeled and transported through `SpeechSequence`.
- `tone` exists as an optional capability in `OutputCapabilities`.
- `braille` is separate as well.

However, tone support is incomplete:

- `src/adapters/outputs/tone.py` is only a logging stub.
- The remote protocol in `src/interop/protocol/messages.py` does not include a tone message.
- The message router and output manager have no tone handling path.
- `access8graph` can request a local failure beep, but that only works if a real `ToneOutput` is injected.

## NVDA Compatibility Constraints

The implementation should follow NVDA's current split between speech and tones:

- NVDA Remote uses `RemoteMessageType.TONE = "tone"`.
- Tone payload uses `hz`, `length`, `left`, and `right`.
- Remote tones are handled separately from remote speech.
- NVDA does not model tones as a speech command inside the speech sequence used for `SPEAK`.

This repo should mirror that behavior for `nvda_remote` rather than introducing a new message type such as `BEEP`, or adding a synthetic `BeepCommand` to speech serialization.

## Recommended Approach

Add a dedicated remote `TONE` message and a real `ToneOutput` backend.

Why this approach:

- It matches NVDA Remote's current protocol shape and semantics.
- It keeps the `speech` and `tone` responsibilities separate.
- It fits the existing `OutputCapabilities` design.
- It keeps future output extensions straightforward, such as `WAVE`, without forcing unrelated output types into the speech model.

Rejected alternatives:

- Adding a `BeepCommand` to `SpeechSequence`: this mixes non-speech behavior into the speech model and diverges from NVDA Remote.
- Introducing a generic output event envelope now: this adds abstraction without solving an immediate problem.

## Design

### 1. Tone backend

Replace the logging stub in `src/adapters/outputs/tone.py` with a real implementation that generates PCM samples and plays them through the platform's default audio output device.

Design constraints:

- No dependency on NVDA runtime modules such as `config`, `extensionPoints`, `nvwave`, or `NVDAHelper.localLib`.
- The implementation may reuse the high-level algorithm from `/workspace/nvda/source/tones.py`, but the runtime integration must be rewritten for this repository.
- The output device is always the default device. No tone output device setting is added.
- The implementation should support stereo balance via `left` and `right`.
- Invalid or edge-case values should be normalized defensively before playback.

Expected backend behavior:

- `hz` is converted to an audible waveform at a fixed sample rate.
- `length` controls duration in milliseconds.
- `left` and `right` scale per-channel amplitude.
- Backend failures are logged and do not tear down the app or the network session.

### 2. Protocol

Extend `src/interop/protocol/messages.py` with:

- `RemoteMessageType.TONE = "tone"`

Payload schema:

- `hz`: numeric frequency in Hertz
- `length`: numeric duration in milliseconds
- `left`: numeric left-channel volume, nominally `0..100`
- `right`: numeric right-channel volume, nominally `0..100`

This shape is intentionally aligned with NVDA Remote.

### 3. Routing

Extend `src/interop/protocol/routing/message_router.py` with a dedicated tone path:

- Add an `on_tone` callback to `MessageRouter.__init__`
- Handle `RemoteMessageType.TONE`
- Validate and normalize the payload
- Forward valid values to the callback
- Report malformed payloads through the existing `invalid_message` status path

Validation rules:

- `hz`, `length`, `left`, and `right` must be coercible to numeric values
- final playback values should be clamped to safe bounds
- messages with uncoercible fields are rejected as invalid

Tone messages do not require custom serializer hooks because they are plain JSON payloads, unlike `SPEAK`.

### 4. Output manager and capabilities

Extend `src/application/services.py` so `OutputManager` can handle tones in addition to speech and clipboard:

- accept an optional `tone_output`
- add `handle_tone(hz, length, left, right)`
- noop if no tone backend is configured

This preserves existing behavior on runtimes or tests that only configure speech.

`OutputCapabilities` already has an optional `tone` field, so no model redesign is needed there.

### 5. Runtime composition

Update runtime/bootstrap assembly so the relevant apps receive a real tone backend:

- `nvda_remote` should receive a real `tone` capability so remote `TONE` messages play locally
- `access8graph` should also benefit from the same backend so its local failure tone becomes audible
- any other app can continue leaving `tone` unset unless it needs it

No UI or config work is included in this change:

- no tone device picker
- no persisted tone backend selection
- no tone settings screen

### 6. Scope boundary

This design intentionally does not:

- add tone commands to `SpeechSequence`
- change speech serializer behavior beyond existing speech support
- add wave playback remote forwarding
- add user-configurable tone output routing

## Data Flow

### Remote tone playback

1. A remote peer sends `type: "tone"` with `hz`, `length`, `left`, and `right`.
2. The local transport deserializes the JSON payload.
3. `MessageRouter` recognizes `RemoteMessageType.TONE`.
4. The router validates the payload and calls `on_tone(hz, length, left, right)`.
5. `OutputManager.handle_tone(...)` forwards the request to the configured `ToneOutput`.
6. The local tone backend plays the beep on the default output device.

### Local app tone playback

1. An app such as `access8graph` calls `outputs.tone.beep(...)`.
2. The shared tone backend plays the tone locally.

## Error Handling

Tone failures must not destabilize the app.

Rules:

- Missing tone capability: noop.
- Invalid remote payload: emit an `invalid_message` status event.
- Playback backend exception: log and return.
- Unsupported or degenerate numeric values: clamp or short-circuit safely.

This mirrors the repository's general preference for resilient output behavior.

## Testing Strategy

### Unit tests

Add or extend tests for:

- `RemoteMessageType.TONE` existence and router dispatch
- router invalid-payload handling for tone messages
- `OutputManager.handle_tone(...)`
- `nvda_remote` service behavior when a remote tone arrives
- `access8graph` local tone behavior using the real backend contract
- tone backend parameter normalization and failure handling

### Integration confidence

The implementation does not require a heavy audio integration test if unit coverage proves:

- the protocol path dispatches correctly
- the runtime composes a real tone backend where needed
- the backend produces the expected calls or buffers for bounded inputs

## Implementation Notes

Implementation should favor the current repository structure:

- protocol changes stay in `src/interop/protocol`
- playback implementation stays in `src/adapters/outputs`
- orchestration changes stay in `src/application` and app runtime assembly

When adapting NVDA tone generation logic, keep the copied code narrow and isolate any repository-specific adjustments inside this repository's tone adapter so the dependency boundary stays explicit.

## Open Decisions Already Resolved

These decisions were confirmed during brainstorming:

- remote tone playback is required
- `nvda_remote` protocol must align with existing NVDA Remote behavior
- use `TONE`, not a new `BEEP` message
- do not add a speech `BeepCommand`
- always use the default audio output device for tones

## Success Criteria

This work is complete when:

- a remote `tone` message received by `nvda_remote` plays locally
- the local `access8graph` failure beep produces sound with the same backend
- protocol names and payload shape match NVDA Remote for tone playback
- tone playback has no NVDA runtime dependency
- existing speech transport behavior remains unchanged
