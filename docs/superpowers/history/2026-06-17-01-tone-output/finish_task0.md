# Tone Output - Task0 Completion

Date: 2026-06-17

## Summary

Added real default-device tone playback and made `nvda_remote` play incoming NVDA Remote-compatible `type: "tone"` messages locally. The implementation keeps tone separate from speech, following the existing `OutputCapabilities` design.

## What Was Implemented

1. **Protocol** — Added `RemoteMessageType.TONE = "tone"` with NVDA Remote-compatible payload schema (hz, length, left, right).
2. **Router** — `MessageRouter` now validates and dispatches `TONE` messages with clamping and `invalid_message` error reporting.
3. **Output Layer** — `OutputManager` accepts optional `tone_output` and delegates `handle_tone()` calls. `NvdaRemoteAppService` wires `_handle_tone` into the message router.
4. **Tone Backend** — Replaced the `LoggingToneOutput` stub with a real `DefaultToneOutput` that generates 16-bit stereo PCM WAV at 44100Hz and plays through platform defaults (`winsound` on Windows, `afplay` on macOS, warning on other platforms). No NVDA runtime dependencies.
5. **Runtime Composition** — `create_tone_output()` factory in `bootstrap/platform.py` injects the default tone backend into both `nvda_remote` (for remote tone playback) and `access8graph` (for local failure beeps).

## Verification

- 445/445 tests pass (`pytest tests/unit tests/integration -v`)
- No NVDA runtime imports in tone backend
- Speech serialization unchanged (no tone commands in `SpeechSequence`)
- Protocol shape matches NVDA Remote: `type: "tone"` with `hz`, `length`, `left`, `right`

## Commit List

| Commit | Message |
|--------|---------|
| `a203fe8` | test: add remote tone router coverage |
| `b70345d` | feat: route remote tone messages |
| `b75a04a` | feat: handle remote tones in output layer |
| `8a94b74` | feat: add default tone output backend |
| `b79cb2a` | feat: compose default tone output |
