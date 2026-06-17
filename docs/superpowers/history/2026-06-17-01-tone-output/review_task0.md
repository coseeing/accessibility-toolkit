# Tone Output Task0 Review

Date: 2026-06-17

## Review Scope

Reviewed the completed Task0 implementation against:

- `docs/superpowers/finish_task0.md`
- `docs/superpowers/specs/2026-06-17-tone-output-design.md`
- `docs/superpowers/plans/2026-06-17-tone-output-implementation.md`

Commits reviewed in chronological order:

| Order | Commit | Message |
|---:|---|---|
| 1 | `a203fe8` | `test: add remote tone router coverage` |
| 2 | `b70345d` | `feat: route remote tone messages` |
| 3 | `b75a04a` | `feat: handle remote tones in output layer` |
| 4 | `8a94b74` | `feat: add default tone output backend` |
| 5 | `b79cb2a` | `feat: compose default tone output` |

## Findings

### Important: remote tone duration/frequency are unbounded before synchronous WAV generation

Files:

- `src/interop/protocol/routing/message_router.py:90`
- `src/adapters/outputs/tone.py:52`
- `src/adapters/outputs/tone.py:138`
- `src/interop/protocol/transport/relay.py:123`

The router only clamps `hz` and `length` to non-negative values, and the backend repeats the same non-negative normalization. There is no maximum bound for `length` or `hz`, despite the spec/plan requiring tone values to be clamped to safe bounds and edge-case values to be normalized defensively.

Impact:

- A remote peer can send a `type: "tone"` payload with a very large `length`.
- `generate_beep_wav()` computes `sample_count = int(SAMPLE_RATE * params.length / 1000)` and then writes one stereo frame per sample.
- For remote messages this happens synchronously on the `RelayTransport` reader thread, because `_read_loop()` calls the message handler inline.
- A malicious or malformed tone can therefore consume CPU/memory and block subsequent remote messages or disconnect handling for an arbitrary duration.

Recommended fix:

- Add explicit constants such as `MAX_TONE_LENGTH_MS` and `MAX_TONE_HZ`.
- Clamp or reject non-finite values (`inf`, `nan`) and excessively large values in the router and/or backend.
- Add tests proving large remote values are bounded before reaching playback and that `generate_beep_wav()` cannot allocate or loop unboundedly from remote input.

## Commit-By-Commit Review

### 1. `a203fe8` - `test: add remote tone router coverage`

Result: acceptable as a TDD setup commit.

Notes:

- Adds failing coverage for `RemoteMessageType.TONE`, valid tone dispatch, invalid field handling, and balance/non-negative clamping.
- The tests cover missing and non-numeric fields.
- The tests do not assert any maximum safety bounds for `length` or `hz`, which allowed the later unbounded-input issue to pass.

### 2. `b70345d` - `feat: route remote tone messages`

Result: mostly matches protocol/router requirements, with the Important finding above.

Notes:

- Adds `RemoteMessageType.TONE = "tone"`, matching the requested NVDA Remote-compatible message type.
- Adds a dedicated router path and `invalid_message` reporting for uncoercible fields.
- Correctly rejects `bool` values as tone numerics.
- Missing: safe upper bounds and non-finite numeric handling.

### 3. `b75a04a` - `feat: handle remote tones in output layer`

Result: acceptable.

Notes:

- `OutputManager` accepts optional `tone_output` and noops when absent.
- `NvdaRemoteAppService` routes remote tones through `_handle_tone()` into `OutputCapabilities.tone`.
- Existing speech paths remain separate from tone handling.
- Test coverage proves both configured and missing tone-output behavior.

### 4. `8a94b74` - `feat: add default tone output backend`

Result: functionally aligned with the plan, with the Important finding above.

Notes:

- Replaces the logging stub with a standalone backend that uses stdlib WAV generation.
- No NVDA runtime imports were added to `src/adapters/outputs/tone.py`.
- Playback failures are caught and logged.
- Zero or negative normalized tones are skipped safely.
- Missing: maximum bounds on generated sample count and non-finite value handling.

Residual risk:

- Windows playback uses synchronous `winsound.PlaySound(..., SND_MEMORY)`. That may be acceptable for short bounded tones, but it makes the missing max-duration clamp more important because remote playback currently runs inline on the reader thread.

### 5. `b79cb2a` - `feat: compose default tone output`

Result: acceptable.

Notes:

- Adds `create_tone_output()` and injects the default backend into `nvda_remote`.
- Injects the same backend into `access8graph`, so local failure beeps can become audible.
- Runtime composition tests cover both apps.

## Requirements Check

| Requirement | Status | Notes |
|---|---|---|
| Remote `tone` message is recognized | Pass | `RemoteMessageType.TONE = "tone"` and router dispatch are present. |
| Payload shape uses `hz`, `length`, `left`, `right` | Pass | Matches spec and local NVDA reference path. |
| Tone remains separate from `SpeechSequence` | Pass | No tone command was added to speech serialization. |
| No NVDA runtime dependencies in tone backend | Pass | Verified no `config`, `extensionPoints`, `nvwave`, `NVDAHelper`, or `logHandler` imports in source. |
| Default output device only | Pass | Windows uses `winsound`; macOS uses `afplay`; no device selector added. |
| Backend failures do not tear down app/session | Pass | Playback exceptions are logged and swallowed. |
| Defensive normalization of edge values | Partial | Negative and invalid values are handled, but maximum bounds are missing. |

## Verification Performed

Commands run:

```bash
python3 -m pytest tests/unit/test_message_router.py tests/unit/test_tone_output.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_bootstrap_platform.py -v
```

Result: `61 passed in 1.09s`

```bash
python3 -m pytest tests/unit tests/integration -v
```

Result: `445 passed in 3.24s`

```bash
rg -n "^\s*(from|import)\s+(config|extensionPoints|nvwave|logHandler)\b|NVDAHelper" src/adapters/outputs/tone.py src
```

Result: no matches.

## Overall Assessment

The implementation satisfies the main feature and compatibility goals, and the test suite passes. I would not merge this without addressing the unbounded remote tone input issue, because it is directly exposed to remote peer input and can block the transport reader thread.
