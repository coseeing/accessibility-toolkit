# NVDA Remote Accessible Connection Cues Design

## Purpose

Improve the NVDA Remote client in three related areas:

- Give every connection-editor field a visible, mnemonic label associated with its edit control.
- Give connection lifecycle changes audible feedback modelled on NVDA Remote Access.
- Tell the user whether F11 has switched keyboard control to the remote or local computer.

The implementation also completes the reusable file-based wave-output capability in
`accessibility-toolkit-core`, so application code does not use platform audio APIs
directly.

## Scope

### Connection editor labels

`ConnectionEditorDialog` will create visible `wx.StaticText` labels for Name, Host,
Port, and Key. The labels use mnemonic text (`&Name:`, `&Host:`, `&Port:`, and
`&Key:`) and are laid out beside their corresponding controls, matching the
remotePlusPlus `addLabeledControl` convention.

The existing `SetName` values remain in place as stable accessible names. Tests will
verify both the visual-label/control pairing and the current keyboard defaults,
validation, and focus behavior.

### Core wave-output capability

The existing public protocol remains:

```python
class WaveOutput(Protocol):
    def play(self, path: str) -> None: ...
```

`accessibility-toolkit-core` will add a concrete default implementation and expose
it through the normal runtime composition path:

```text
PlatformProvider.create_wave_output()
    -> AppRuntimeParts.wave_output
    -> OutputServices.capabilities.wave
    -> application use case
```

`Capabilities.wave` is optional, just like `Capabilities.tone`. This preserves
compatibility for applications and tests that do not need wave playback.

`DefaultWaveOutput.play(path)` is non-blocking. On Windows it uses the standard
Windows WAV playback facility; on macOS it starts `afplay` in the background. On an
unsupported platform, or if the requested file cannot be played, it logs a warning
and returns without raising. A cue is feedback only; it must never alter connection
or control state.

The existing tone generator remains responsible only for generated beeps. It may
share a low-level playback implementation where useful, but its public behavior and
tests must not change.

### NVDA Remote cue behavior

The NVDA Remote app will package these verbatim NVDA assets:

```text
src/apps/nvda_remote/waves/connected.wav
src/apps/nvda_remote/waves/disconnected.wav
```

They originate from `ref/nvda/source/waves/`. The app package configuration must
include them in built distributions. A notice next to the assets must identify NVDA
as the source and preserve the GPL v2-or-later licensing information applicable to
those copied files. Distribution of the resulting project must remain GPL-compatible.

The app-level cue mapping is intentionally fixed; this change does not add the
TeleNVDA-style preference that substitutes generated tones for WAV files.

| Transition | Wave cue | Speech |
| --- | --- | --- |
| Session becomes connected | `connected.wav` | none |
| Session becomes idle after a real disconnect | `disconnected.wav` | `Disconnected` |
| F11 / Start Control enters remote control | none | `Controlling remote computer` |
| F11 / Stop Control returns to local control | none | `Controlling local computer` |

The lifecycle and control use cases own notification timing. This guarantees a
single cue per actual state transition regardless of whether the transition was
started through a UI button, F11, replacement connection, or transport disconnect.
The UI remains a state consumer and must not emit duplicate audio feedback.

Speech uses the configured local speech capability. Cue WAV files are played only on
the local client and are not sent through the remote protocol.

## Components and Responsibilities

| Component | Responsibility |
| --- | --- |
| `accessibility_toolkit.output.wave` | Define the concrete safe, asynchronous local WAV player. |
| `accessibility_toolkit.output.Capabilities` | Carry the optional `WaveOutput` alongside speech and tone capabilities. |
| `accessibility_toolkit.runtime.platform` | Construct the platform-appropriate wave player lazily. |
| `accessibility_toolkit.runtime.output` and `runtime_parts` | Pass the wave player through runtime composition unchanged. |
| `apps.nvda_remote` cue helper/use cases | Resolve packaged cue paths and map lifecycle/control transitions to wave and speech output. |
| `ui.nvda_remote.connection_editor` | Display mnemonic field labels adjacent to their edit controls. |

## Error Handling

- A missing optional `wave` capability skips only the WAV cue; state transitions and
  required speech feedback continue.
- Exceptions from a wave backend are caught and logged at warning level by the core
  implementation.
- A speech backend is already required by `Capabilities`; no transition is rolled
  back when speech output reports a failure.
- Repeated `stop_control()` calls and duplicate disconnect notifications retain their
  existing idempotence and must not add duplicate announcements.

## Testing and Acceptance Criteria

1. The editor visibly contains four mnemonic labels, each paired with its intended
   text or spin control; validation and standard dialog keyboard behavior still pass.
2. A runtime built with a default provider exposes the same wave-output object via
   runtime parts and `Capabilities`; callers can omit it safely.
3. Default wave playback delegates asynchronously to the platform backend and turns
   playback failures into warnings rather than exceptions.
4. Packaged distributions include both NVDA cue WAV files and their source/license
   notice.
5. A successful session connection produces exactly one connected WAV request.
6. A real disconnection produces exactly one disconnected WAV request and one
   `Disconnected` speech sequence.
7. Entering and leaving remote control produces respectively the remote/local speech
   phrases, whether driven by the visible control button or F11.
8. The focused unit tests and the complete `pytest tests/unit tests/integration -v`
   suite pass.

## Non-goals

- No sound-versus-tone preference or persistent audio setting.
- No remote-protocol change and no forwarding of local cue audio to peers.
- No replacement of the existing remote speech, tone, clipboard, or input-routing
  behavior.
- No unrelated refactoring of connection management or UI layout.
