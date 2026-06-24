# Speech Engine Settings Design

## Overview

This document defines the design for evolving the speech settings panel from raw integer text fields into NVDA-like speech engine settings with normalized `0-100` sliders for rate, pitch, and volume.

The implementation keeps the existing speech command and speech sequence direction aligned with NVDA. Each speech engine driver owns its own supported settings, current values, and percent-to-engine mapping. The UI and application layers operate on normalized percentages and engine capabilities rather than engine-specific raw values.

## Goals

- Replace the rate, pitch, and volume text fields with sliders.
- Normalize speech setting values to `0-100` in the UI and application-facing API.
- Keep speech engine drivers responsible for mapping normalized percentages to engine-specific raw values.
- Move terminology from `backend` to `speech engine`.
- Disable unsupported controls in the UI based on the active engine's capabilities.
- Persist selected speech engine, voice, and normalized numeric settings across restarts.
- Keep the design close to NVDA's synth driver architecture.

## Non-Goals

- Do not change the remote speech protocol or speech command payload format.
- Do not introduce automatic engine detection or fallback logic.
- Do not preserve compatibility with the old `speech_backend` config key.
- Do not add macOS- or Linux-specific speech engines in this round.
- Do not redesign unrelated connection, relay, keyboard, clipboard, or tone features.

## Recommended Architecture

The active speech engine remains a concrete driver class implementing the generic speech output protocol. The application layer continues to route requests to the active engine, but no longer treats numeric values as engine-specific raw integers.

### Layers

#### `adapters`

Concrete speech engine drivers remain the source of truth for speech behavior and settings.

Responsibilities:

- Speak, cancel, and pause speech.
- Enumerate and select voices when supported.
- Declare supported numeric settings for rate, pitch, and volume.
- Store current normalized percent values for supported settings.
- Convert normalized percent values to engine-specific raw values.

Initial drivers continue to be:

- `NvdaControllerSpeechOutput`
- `Pyttsx3SpeechOutput`

#### `application`

The application layer continues to manage active engine selection and routing.

Responsibilities:

- Hold the selected speech engine id.
- Create and replace the active speech engine.
- Forward `speak()`, `cancel()`, `pause()`, voice selection, and numeric setting updates to the active engine.
- Persist selected engine and per-engine settings.
- Stay independent from engine-specific mapping formulas.

#### `ui`

The speech settings panel reflects active engine capabilities.

Responsibilities:

- Render the speech engine choice control.
- Render the voice choice control.
- Render rate, pitch, and volume sliders using normalized percentages.
- Disable unsupported controls.
- Sync the active engine's current values into the controls.

## Speech Engine Model

### Terminology

All user-facing and application-level naming should use `speech engine` rather than `backend`.

Recommended renames:

- `SpeechBackendOption` -> `SpeechEngineOption`
- `SpeechBackendManager` -> `SpeechEngineManager`
- `get_speech_backend_options()` -> `get_speech_engine_options()`
- `get_selected_speech_backend()` -> `get_selected_speech_engine()`
- `set_speech_backend()` -> `set_speech_engine()`

Driver class names may remain concrete and implementation-specific, but the design treats them as speech engine drivers in the NVDA synth-driver sense.

### Driver-Owned Settings

Each speech engine driver must own its own supported settings and mapping behavior.

Add a small setting model similar in intent to NVDA `NumericDriverSetting`, for example:

```python
@dataclass(frozen=True)
class SpeechNumericSetting:
    id: str
    label: str
    default_percent: int = 50
    min_percent: int = 0
    max_percent: int = 100
    step: int = 1
    large_step: int = 10
```

Each driver exposes the numeric settings it supports. The simplest shape is a method such as:

```python
def get_supported_numeric_settings(self) -> tuple[SpeechNumericSetting, ...]:
    ...
```

The setting ids for this feature are:

- `rate`
- `pitch`
- `volume`

If an engine does not support a setting, it should omit it from its supported settings list.

### Normalized Value Contract

The public getter and setter methods for numeric speech settings return and accept normalized percentages:

- `get_rate() -> int | None`
- `set_rate(value: int) -> None`
- `get_pitch() -> int | None`
- `set_pitch(value: int) -> None`
- `get_volume() -> int | None`
- `set_volume(value: int) -> None`

These values are always interpreted as `0-100` percentages. Raw engine values remain private to the concrete driver.

### Common Helpers

Shared helper functions may be added for generic operations such as:

- `clamp_percent(value: int) -> int`
- `percent_to_range(percent: int, min_value: float, max_value: float) -> float`
- `range_to_percent(raw: float, min_value: float, max_value: float) -> int`

These helpers should stay low-level. The actual mapping policy remains owned by each driver.

## Runtime Flow

### Startup

1. The application loads the configured speech engine id.
2. The speech engine manager creates the active speech engine driver.
3. The application loads any saved per-engine voice and numeric settings.
4. Saved numeric values are treated as normalized percentages and passed into the active engine.
5. The speech settings frame syncs voice availability, supported sliders, enabled states, and current normalized values.

### Speech Engine Switch

1. The user chooses a different speech engine in the settings frame.
2. The controller updates the selected engine id in the application layer.
3. The current engine is canceled.
4. The speech engine manager creates the new engine driver.
5. The application loads saved values for that engine and applies them.
6. The settings frame re-syncs control values and enabled states.

### Numeric Setting Update

1. The user moves a slider.
2. The UI sends the normalized percent value to the controller.
3. The controller forwards it to the speech service.
4. The speech service forwards it to the active engine.
5. The active engine clamps the percent if needed, stores the normalized value, converts it to an engine-specific raw value, and applies it to the engine runtime.
6. The application persists the normalized value for the selected engine.

## UI Design

### Panel Controls

The speech settings frame keeps a stable control layout:

- speech engine choice
- voice choice
- rate slider
- pitch slider
- volume slider

The three numeric sliders always use a `0-100` range. The default visual position for a supported setting with no saved value is `50`.

### Unsupported Numeric Settings

Unsupported settings are reflected directly in the UI.

Rules:

- If the active engine does not declare a numeric setting, the corresponding slider is disabled.
- Disabled sliders should show the neutral/default position `50`.
- Disabled sliders must not call `set_rate()`, `set_pitch()`, or `set_volume()`.
- After switching engines, the enabled and disabled state of all sliders must be recalculated.

### Voice Selection

Voice selection follows the same capability-based model.

Rules:

- If `list_voices()` returns one or more voices, the voice choice is enabled and synchronized with `get_voice()`.
- If `list_voices()` returns an empty tuple, the voice choice is disabled.
- When voice choice is disabled, `_on_voice_change()` must not call `set_voice()`.

This is especially important for `NvdaControllerSpeechOutput`, which cannot currently provide voice selection even though it may support rate, pitch, and volume via SSML prosody behavior.

## Driver Mapping Strategy

### General Rule

Each driver owns its own mapping from normalized percent values to raw engine values.

The application layer must not know whether the mapping is linear, piecewise, capped, rounded, or based on engine-specific formulas.

### `Pyttsx3SpeechOutput`

`Pyttsx3SpeechOutput` should treat `rate`, `pitch`, and `volume` as normalized percentages internally.

Expected behavior:

- `rate` stores a normalized percent and maps it to the underlying engine's raw rate value.
- `pitch` stores a normalized percent and maps it to the engine `pitch` property when the engine supports it.
- `volume` stores a normalized percent and maps it to the engine's `0.0-1.0` volume range.

The exact raw mapping formula may be conservative and implementation-driven, but it belongs in the driver.

### `NvdaControllerSpeechOutput`

`NvdaControllerSpeechOutput` should also expose normalized percent settings even though the underlying implementation speaks SSML.

Expected behavior:

- It stores normalized `rate`, `pitch`, and `volume` values as the current local baseline.
- These normalized values are used when converting offset-based speech commands into SSML prosody percentages.
- The conversion logic stays in the driver.

This keeps the engine aligned with the same normalized contract as other drivers while preserving its SSML-specific implementation.

## Persistence

Configuration should store normalized values and use the new `speech engine` terminology without any compatibility layer for the old `speech_backend` key.

Recommended config shape:

- `speech_engine`
- `speech_engines.<engine_id>.voice`
- `speech_engines.<engine_id>.rate`
- `speech_engines.<engine_id>.pitch`
- `speech_engines.<engine_id>.volume`

Persistence rules:

- Store voice and numeric settings per engine id.
- Store numeric values as normalized percentages only.
- Do not store raw engine values.
- On startup or engine switch, ignore saved values for unsupported settings.
- Clamp restored numeric values to `0-100`.
- If a saved voice no longer exists in `list_voices()`, ignore it and keep the engine default.

## Error Handling

- If switching to a new speech engine fails, keep the current engine active and restore the previous UI selection.
- If a voice enumeration call fails and the engine returns no voices, keep the voice control disabled rather than surfacing a broken selection state.
- If an engine does not support a numeric setting, that setting remains disabled rather than attempting best-effort application.
- If restored config values are out of range, clamp them before applying them.

## Testing Strategy

### Unit Tests

- Rename-oriented tests for speech engine option and manager naming.
- Controller tests for speech engine selection methods.
- UI tests confirming rate, pitch, and volume use sliders rather than text fields.
- UI tests confirming unsupported sliders are disabled and do not call setters.
- UI tests confirming empty voice lists disable the voice choice.
- Persistence tests for selected engine, per-engine voice, and per-engine normalized numeric settings.
- Driver tests for each engine's own percent-to-raw mapping behavior.

### Integration Tests

- Start with one engine selected, persist settings, restart, and confirm the same engine and normalized values are restored.
- Switch from one engine to another and confirm saved values are applied per engine rather than globally.
- Confirm incoming speech sequences still route through the selected engine unchanged.

### Manual Checks

- Open the speech settings frame and verify the three numeric controls are sliders with a `0-100` range.
- Verify `NvdaControllerSpeechOutput` disables voice selection.
- Verify a driver without pitch support disables only pitch while leaving supported controls active.
- Change voice and numeric values, restart the app, and confirm they are restored for the same engine.

## Implementation Notes

- Keep the speech engine manager in `application`, not in `ui`.
- Keep engine-specific mapping logic in the drivers.
- Prefer a small `SpeechNumericSetting` model over a large abstraction hierarchy.
- Keep the speech command and speech sequence model unchanged.
- Do not add compatibility code for the old `speech_backend` config key.
