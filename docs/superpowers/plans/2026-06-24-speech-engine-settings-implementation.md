# Speech Engine Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement NVDA-like speech engine settings with `0-100` sliders, driver-owned numeric setting support, speech engine terminology, fixed engine ids/labels, and per-engine persistence.

**Architecture:** Keep speech engines as concrete driver classes that own `speak()`, voice APIs, numeric setting support, and percent-to-engine mapping. The application/service/controller/UI layers pass normalized `0-100` values and route to the active engine, while persistence stores selected engine and per-engine normalized settings. Rename backend terminology to speech engine at application/UI boundaries.

**Tech Stack:** Python 3.11+, `pytest`, wxPython-compatible shared UI controls, existing `SpeechService`, `QueuedService`, `Scheduler`, JSON config store

---

## File Structure

| File | Responsibility |
|---|---|
| `src/application/output/speech/settings.py` | New `SpeechNumericSetting` model and percent helper functions |
| `src/application/output/speech/backends.py` | Rename classes conceptually to speech engine option/manager while preserving focused engine selection logic |
| `src/application/output/speech/service.py` | Expose speech engine methods and supported numeric settings through `SpeechService` |
| `src/application/output/service.py` | Update `SpeechServiceProtocol` and `QueuedService` pass-through methods to speech engine terminology |
| `src/adapters/outputs/interfaces.py` | Add `get_supported_numeric_settings()` to the speech output protocol |
| `src/adapters/outputs/drivers/pyttsx3.py` | Store normalized `rate`/`pitch`/`volume`, declare supported settings, map percent to raw engine properties |
| `src/adapters/windows/nvda_controller.py` | Store normalized `rate`/`pitch`/`volume`, declare supported settings, keep SSML mapping inside the driver |
| `src/application/config.py` | Replace backend config store with speech engine config store using new keys and per-engine setting persistence |
| `src/bootstrap/platform.py` | Use `NvdaController`/`Pyttsx3` ids and `Nvda Controller`/`Pyttsx3` labels |
| `src/bootstrap/output.py`, `src/bootstrap/app_runtime.py` | Rename selected/fallback backend parameters to engine parameters |
| `src/apps/shared/speech_settings_controller.py` | Route speech engine, voice, numeric setting APIs and invoke persistence callbacks after successful changes |
| `src/apps/nvda_remote/service.py`, `src/apps/key_echo/service.py`, `src/apps/access8graph/service.py` | Rename app-facing methods to speech engine terminology and preserve status notifications |
| `src/apps/nvda_remote/main.py` | Load selected engine and per-engine saved voice/numeric settings; wire save callbacks |
| `src/ui/shared/speech_controls.py` | Replace text fields with sliders; disable unsupported sliders and empty voice choices |
| `tests/unit/test_speech_backends.py` | Engine manager, config store, driver setting, and mapping tests |
| `tests/unit/test_speech_service.py`, `tests/unit/test_output_service.py`, `tests/unit/test_speech_settings_controller.py` | Service/controller pass-through tests |
| `tests/unit/test_app_wx.py` | Fake wx slider support and speech settings frame behavior |
| `tests/unit/test_bootstrap_platform.py`, `tests/unit/test_bootstrap_output.py`, `tests/unit/test_bootstrap_app_runtime.py` | Engine id/label and bootstrap rename tests |
| `tests/unit/test_nvda_remote_app_service.py`, `tests/unit/test_key_echo_app_service.py`, `tests/unit/test_access8graph_app_service.py` | App-facing speech engine notification tests |

## Task 1: Add Speech Numeric Setting Model

**Files:**
- Create: `src/application/output/speech/settings.py`
- Modify: `src/application/output/speech/__init__.py`
- Test: `tests/unit/test_speech_backends.py`

- [ ] **Step 1: Write the failing tests**

Append these tests to `tests/unit/test_speech_backends.py`:

```python
from application.output.speech import SpeechNumericSetting
from application.output.speech.settings import clamp_percent, percent_to_range, range_to_percent


def test_speech_numeric_setting_defaults_to_zero_to_one_hundred_percent():
    setting = SpeechNumericSetting(id="rate", label="Rate")

    assert setting.id == "rate"
    assert setting.label == "Rate"
    assert setting.default_percent == 50
    assert setting.min_percent == 0
    assert setting.max_percent == 100
    assert setting.step == 1
    assert setting.large_step == 10


def test_percent_helpers_clamp_and_map_ranges():
    assert clamp_percent(-1) == 0
    assert clamp_percent(0) == 0
    assert clamp_percent(50) == 50
    assert clamp_percent(100) == 100
    assert clamp_percent(101) == 100
    assert percent_to_range(50, 50, 300) == 175
    assert percent_to_range(0, 50, 300) == 50
    assert percent_to_range(100, 50, 300) == 300
    assert range_to_percent(175, 50, 300) == 50
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_speech_backends.py -k "numeric_setting or percent_helpers" -v`

Expected: FAIL with import errors for `SpeechNumericSetting` and helper functions.

- [ ] **Step 3: Add the setting model and helpers**

Create `src/application/output/speech/settings.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class SpeechNumericSetting:
    id: str
    label: str
    default_percent: int = 50
    min_percent: int = 0
    max_percent: int = 100
    step: int = 1
    large_step: int = 10


def clamp_percent(value: int) -> int:
    return max(0, min(100, int(value)))


def percent_to_range(percent: int, min_value: float, max_value: float) -> float:
    clamped = clamp_percent(percent)
    return (clamped / 100) * (max_value - min_value) + min_value


def range_to_percent(raw: float, min_value: float, max_value: float) -> int:
    if max_value == min_value:
        return 0
    percent = round(((raw - min_value) / (max_value - min_value)) * 100)
    return clamp_percent(percent)
```

Update `src/application/output/speech/__init__.py`:

```python
from application.output.speech.backends import SpeechBackendManager, SpeechBackendOption
from application.output.speech.service import SpeechService
from application.output.speech.settings import SpeechNumericSetting

__all__ = [
    "SpeechBackendManager",
    "SpeechBackendOption",
    "SpeechNumericSetting",
    "SpeechService",
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_speech_backends.py -k "numeric_setting or percent_helpers" -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/application/output/speech/settings.py src/application/output/speech/__init__.py tests/unit/test_speech_backends.py
git commit -m "feat: add speech numeric setting model"
```

## Task 2: Rename Backend Domain To Speech Engine Domain

**Files:**
- Modify: `src/application/output/speech/backends.py`
- Modify: `src/application/output/speech/service.py`
- Modify: `src/application/output/speech/__init__.py`
- Modify: `src/application/output/service.py`
- Modify: tests importing `SpeechBackendOption` or `SpeechBackendManager`

- [ ] **Step 1: Write the failing tests**

In `tests/unit/test_speech_backends.py`, rename the manager tests to engine terminology and add this assertion:

```python
from application.output.speech import SpeechEngineManager, SpeechEngineOption


def test_speech_engine_manager_switches_engine_and_cancels_previous():
    created: list[FakeSpeechOutput] = []

    def factory() -> FakeSpeechOutput:
        output = FakeSpeechOutput()
        created.append(output)
        return output

    manager = SpeechEngineManager(
        engine_options=(
            SpeechEngineOption(engine_id="NvdaController", label="Nvda Controller", factory=factory),
            SpeechEngineOption(engine_id="Pyttsx3", label="Pyttsx3", factory=factory),
        ),
        selected_engine_id="NvdaController",
    )

    first = manager.current_output
    manager.set_engine("Pyttsx3")

    assert first.cancelled == 1
    assert manager.selected_engine_id == "Pyttsx3"
    assert manager.engine_choices() == (
        ("NvdaController", "Nvda Controller"),
        ("Pyttsx3", "Pyttsx3"),
    )
```

In `tests/unit/test_output_service.py`, update the import smoke test:

```python
def test_application_output_speech_exports_engine_types():
    from application.output.speech import SpeechEngineManager, SpeechEngineOption

    assert SpeechEngineManager is not None
    assert SpeechEngineOption is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_speech_backends.py::test_speech_engine_manager_switches_engine_and_cancels_previous tests/unit/test_output_service.py::test_application_output_speech_exports_engine_types -v`

Expected: FAIL because `SpeechEngineManager` and `SpeechEngineOption` do not exist yet.

- [ ] **Step 3: Rename core classes and methods**

Replace `src/application/output/speech/backends.py` with:

```python
from dataclasses import dataclass
from typing import Callable

from adapters.outputs.interfaces import SpeechOutput


@dataclass(frozen=True)
class SpeechEngineOption:
    engine_id: str
    label: str
    factory: Callable[[], SpeechOutput]


class SpeechEngineManager:
    def __init__(
        self,
        *,
        engine_options: tuple[SpeechEngineOption, ...],
        selected_engine_id: str,
    ) -> None:
        if not engine_options:
            raise ValueError("At least one speech engine is required")
        self._options = engine_options
        self._options_by_id = {option.engine_id: option for option in engine_options}
        if selected_engine_id not in self._options_by_id:
            raise ValueError(f"Unknown speech engine: {selected_engine_id}")
        self._selected_engine_id = selected_engine_id
        self._current_output = self._create_output(selected_engine_id)

    @property
    def current_output(self) -> SpeechOutput:
        return self._current_output

    @property
    def selected_engine_id(self) -> str:
        return self._selected_engine_id

    def engine_choices(self) -> tuple[tuple[str, str], ...]:
        return tuple((option.engine_id, option.label) for option in self._options)

    def set_engine(self, engine_id: str) -> SpeechOutput:
        if engine_id not in self._options_by_id:
            raise ValueError(f"Unknown speech engine: {engine_id}")
        if engine_id == self._selected_engine_id:
            return self._current_output
        self._current_output.cancel()
        self._current_output = self._create_output(engine_id)
        self._selected_engine_id = engine_id
        return self._current_output

    def _create_output(self, engine_id: str) -> SpeechOutput:
        return self._options_by_id[engine_id].factory()
```

Update `src/application/output/speech/__init__.py`:

```python
from application.output.speech.backends import SpeechEngineManager, SpeechEngineOption
from application.output.speech.service import SpeechService
from application.output.speech.settings import SpeechNumericSetting

__all__ = [
    "SpeechEngineManager",
    "SpeechEngineOption",
    "SpeechNumericSetting",
    "SpeechService",
]
```

Update imports and constructor parameter names in `src/application/output/speech/service.py`:

```python
from application.output.speech.backends import SpeechEngineManager, SpeechEngineOption


class SpeechService:
    def __init__(
        self,
        *,
        engine_options: tuple[SpeechEngineOption, ...],
        selected_engine_id: str,
        scheduler: "Scheduler | None" = None,
    ) -> None:
        self._engine_manager = SpeechEngineManager(
            engine_options=engine_options,
            selected_engine_id=selected_engine_id,
        )
        self._scheduler = scheduler

    def get_engine_options(self) -> tuple[tuple[str, str], ...]:
        return self._engine_manager.engine_choices()

    def get_selected_engine(self) -> str:
        return self._engine_manager.selected_engine_id

    def set_engine(self, engine_id: str) -> None:
        self._engine_manager.set_engine(engine_id)
```

Keep the existing speech, voice, and numeric methods in `SpeechService`, but change every `self._backend_manager.current_output` reference to `self._engine_manager.current_output`.

Update `src/application/output/service.py` protocol and `QueuedService` pass-through names:

```python
def get_engine_options(self) -> tuple[tuple[str, str], ...]: ...
def get_selected_engine(self) -> str: ...
def set_engine(self, engine_id: str) -> None: ...
```

and:

```python
def get_engine_options(self) -> tuple[tuple[str, str], ...]:
    return self._speech.get_engine_options()

def get_selected_engine(self) -> str:
    return self._speech.get_selected_engine()

def set_engine(self, engine_id: str) -> None:
    self._speech.set_engine(engine_id)
```

- [ ] **Step 4: Update test imports and constructor calls**

Replace test usages:

```python
SpeechBackendOption(backend_id="nvda_controller", ...)
SpeechBackendManager(backend_options=..., selected_backend_id=...)
```

with:

```python
SpeechEngineOption(engine_id="NvdaController", ...)
SpeechEngineManager(engine_options=..., selected_engine_id=...)
```

Use `"NvdaController"` and `"Pyttsx3"` for the real engine ids. Test-local fake ids such as `"default"` may remain where they are not representing the real engines.

- [ ] **Step 5: Run focused tests**

Run: `pytest tests/unit/test_speech_backends.py tests/unit/test_speech_service.py tests/unit/test_output_service.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/application/output/speech src/application/output/service.py tests/unit/test_speech_backends.py tests/unit/test_speech_service.py tests/unit/test_output_service.py
git commit -m "refactor: rename speech backend domain to engine"
```

## Task 3: Update Bootstrap Engine IDs And Labels

**Files:**
- Modify: `src/bootstrap/platform.py`
- Modify: `src/bootstrap/output.py`
- Modify: `src/bootstrap/app_runtime.py`
- Test: `tests/unit/test_bootstrap_platform.py`
- Test: `tests/unit/test_bootstrap_output.py`
- Test: `tests/unit/test_bootstrap_app_runtime.py`

- [ ] **Step 1: Write the failing tests**

Update `tests/unit/test_bootstrap_platform.py` expectations:

```python
def test_default_speech_engine_id_is_nvda_controller_on_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")

    assert default_speech_engine_id() == "NvdaController"


def test_default_speech_engine_id_is_pyttsx3_off_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")

    assert default_speech_engine_id() == "Pyttsx3"


def test_default_speech_engine_options_use_fixed_ids_and_labels(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")

    options = default_speech_engine_options(FakeScheduler())

    assert [(option.engine_id, option.label) for option in options] == [
        ("NvdaController", "Nvda Controller"),
        ("Pyttsx3", "Pyttsx3"),
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_bootstrap_platform.py -k "speech_engine" -v`

Expected: FAIL because bootstrap still exposes backend-named functions and old ids.

- [ ] **Step 3: Rename bootstrap speech provider functions**

In `src/bootstrap/platform.py`, replace `default_speech_backend_options()` and `default_speech_backend_id()` with:

```python
from application.output.speech import SpeechEngineOption


def default_speech_engine_options(
    scheduler: Scheduler,
) -> tuple[SpeechEngineOption, ...]:
    options = [
        SpeechEngineOption(
            engine_id="Pyttsx3",
            label="Pyttsx3",
            factory=lambda: Pyttsx3SpeechOutput.load_default(scheduler=scheduler),
        ),
    ]
    if sys.platform == "win32":
        options.insert(
            0,
            SpeechEngineOption(
                engine_id="NvdaController",
                label="Nvda Controller",
                factory=lambda: _get_nvda_controller_speech_output_class().load_default(
                    scheduler=scheduler
                ),
            ),
        )
    return tuple(options)


def default_speech_engine_id() -> str:
    return "NvdaController" if sys.platform == "win32" else "Pyttsx3"
```

Update `PlatformProvider`:

```python
def default_speech_engine_options(
    self, scheduler: Scheduler
) -> tuple[SpeechEngineOption, ...]:
    return default_speech_engine_options(scheduler)

def default_speech_engine_id(self) -> str:
    return default_speech_engine_id()
```

In `src/bootstrap/output.py`, rename parameters:

```python
def build_output_services(
    *,
    engine_options_factory: Callable[[Scheduler], tuple[SpeechEngineOption, ...]],
    selected_engine_id: str,
    fallback_engine_id: str | None = None,
    tone_output: ToneOutput | None = None,
    on_engine_fallback: Callable[[str], None] | None = None,
) -> OutputServices:
```

Construct `SpeechService(engine_options=..., selected_engine_id=...)` and log `"Unknown configured speech engine %r; falling back to %s"`.

In `src/bootstrap/app_runtime.py`, update the provider calls to `default_speech_engine_id()` and `default_speech_engine_options()`.

- [ ] **Step 4: Update bootstrap tests**

Replace old names and parameter names in `tests/unit/test_bootstrap_output.py` and `tests/unit/test_bootstrap_app_runtime.py`:

```python
build_output_services(
    engine_options_factory=lambda scheduler: (
        SpeechEngineOption("primary", "Primary", lambda: FakeSpeechOutput()),
        SpeechEngineOption("fallback", "Fallback", lambda: FakeSpeechOutput()),
    ),
    selected_engine_id="primary",
)
```

- [ ] **Step 5: Run bootstrap tests**

Run: `pytest tests/unit/test_bootstrap_platform.py tests/unit/test_bootstrap_output.py tests/unit/test_bootstrap_app_runtime.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/bootstrap tests/unit/test_bootstrap_platform.py tests/unit/test_bootstrap_output.py tests/unit/test_bootstrap_app_runtime.py
git commit -m "refactor: use speech engine ids in bootstrap"
```

## Task 4: Add Driver-Supported Numeric Settings And Percent Mapping

**Files:**
- Modify: `src/adapters/outputs/interfaces.py`
- Modify: `src/adapters/outputs/drivers/pyttsx3.py`
- Modify: `src/adapters/windows/nvda_controller.py`
- Test: `tests/unit/test_speech_backends.py`

- [ ] **Step 1: Write failing driver tests**

Append these tests to `tests/unit/test_speech_backends.py`:

```python
def test_pyttsx3_backend_declares_supported_numeric_settings():
    output = Pyttsx3SpeechOutput(engine=FakeEngine(), task_manager=FakeTaskManager())

    settings = {setting.id: setting for setting in output.get_supported_numeric_settings()}

    assert tuple(settings) == ("rate", "pitch", "volume")
    assert settings["rate"].label == "Rate"
    assert settings["pitch"].label == "Pitch"
    assert settings["volume"].label == "Volume"
    assert output.get_rate() == 50
    assert output.get_pitch() == 50
    assert output.get_volume() == 50


def test_pyttsx3_backend_maps_normalized_values_to_engine_properties():
    engine = FakeEngine()
    output = Pyttsx3SpeechOutput(engine=engine, task_manager=FakeTaskManager())

    output.set_rate(100)
    output.set_pitch(80)
    output.set_volume(25)
    output.speak(SpeechSequence(items=("hello",)))

    assert engine.properties["rate"] == 300
    assert engine.properties["pitch"] == 80
    assert engine.properties["volume"] == 0.25


def test_pyttsx3_backend_clamps_normalized_values():
    output = Pyttsx3SpeechOutput(engine=FakeEngine(), task_manager=FakeTaskManager())

    output.set_rate(999)
    output.set_pitch(-1)
    output.set_volume(150)

    assert output.get_rate() == 100
    assert output.get_pitch() == 0
    assert output.get_volume() == 100


def test_nvda_controller_backend_declares_supported_numeric_settings():
    output = NvdaControllerSpeechOutput(controller=FakeNvdaController())

    settings = {setting.id: setting for setting in output.get_supported_numeric_settings()}

    assert tuple(settings) == ("rate", "pitch", "volume")
    assert output.get_rate() == 50
    assert output.get_pitch() == 50
    assert output.get_volume() == 50


def test_nvda_controller_backend_uses_normalized_baseline_for_offsets():
    controller = FakeNvdaController()
    output = NvdaControllerSpeechOutput(controller=controller)
    output.set_rate(80)
    output.set_pitch(40)
    output.set_volume(60)

    output.speak(
        SpeechSequence(
            items=(
                RateCommand(offset=20),
                PitchCommand(offset=10),
                VolumeCommand(offset=30),
                "hello",
            )
        )
    )

    assert controller.speak_ssml_calls == [
        (
            '<speak><prosody rate="125%"><prosody pitch="125%"><prosody volume="150%">hello'
            "</prosody></prosody></prosody></speak>",
            0,
            0,
            True,
        )
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_speech_backends.py -k "supported_numeric_settings or normalized_values or normalized_baseline" -v`

Expected: FAIL because drivers do not expose supported numeric settings and still default to old raw values.

- [ ] **Step 3: Update the speech output protocol**

In `src/adapters/outputs/interfaces.py`, import `SpeechNumericSetting` and add:

```python
def get_supported_numeric_settings(self) -> tuple[SpeechNumericSetting, ...]: ...
```

Add the same method to `NullSpeechOutput` in `src/adapters/outputs/speech.py`:

```python
def get_supported_numeric_settings(self) -> tuple[SpeechNumericSetting, ...]:
    return ()
```

- [ ] **Step 4: Update `Pyttsx3SpeechOutput`**

In `src/adapters/outputs/drivers/pyttsx3.py`, add imports and constants:

```python
from application.output.speech.settings import (
    SpeechNumericSetting,
    clamp_percent,
    percent_to_range,
)

_SUPPORTED_NUMERIC_SETTINGS = (
    SpeechNumericSetting("rate", "Rate"),
    SpeechNumericSetting("pitch", "Pitch"),
    SpeechNumericSetting("volume", "Volume"),
)
_MIN_RAW_RATE = 50
_MAX_RAW_RATE = 300
```

Initialize normalized defaults:

```python
self._rate = 50
self._pitch = 50
self._volume = 50
```

Add:

```python
def get_supported_numeric_settings(self) -> tuple[SpeechNumericSetting, ...]:
    return _SUPPORTED_NUMERIC_SETTINGS
```

Clamp setters:

```python
def set_rate(self, value: int) -> None:
    self._rate = clamp_percent(value)

def set_pitch(self, value: int) -> None:
    self._pitch = clamp_percent(value)

def set_volume(self, value: int) -> None:
    self._volume = clamp_percent(value)
```

In `_speak_text()`, map to raw engine properties:

```python
engine.setProperty("rate", round(percent_to_range(self._rate, _MIN_RAW_RATE, _MAX_RAW_RATE)))
try:
    engine.setProperty("pitch", self._pitch)
except Exception:
    logger.debug("pyttsx3 engine does not support pitch property")
engine.setProperty("volume", self._volume / 100.0)
```

Keep speech command handling normalized:

```python
if isinstance(item, PitchCommand):
    self._pitch = clamp_percent(item.offset if item.mode == "offset" else round(item.multiplier * 100))
    continue
if isinstance(item, RateCommand):
    self._rate = clamp_percent(item.offset if item.mode == "offset" else round(item.multiplier * 100))
    continue
if isinstance(item, VolumeCommand):
    self._volume = clamp_percent(item.offset if item.mode == "offset" else round(item.multiplier * 100))
```

- [ ] **Step 5: Update `NvdaControllerSpeechOutput`**

In `src/adapters/windows/nvda_controller.py`, add:

```python
from application.output.speech.settings import SpeechNumericSetting, clamp_percent

_SUPPORTED_NUMERIC_SETTINGS = (
    SpeechNumericSetting("rate", "Rate"),
    SpeechNumericSetting("pitch", "Pitch"),
    SpeechNumericSetting("volume", "Volume"),
)
```

Initialize normalized defaults:

```python
self._rate = 50
self._pitch = 50
self._volume = 50
```

Add:

```python
def get_supported_numeric_settings(self) -> tuple[SpeechNumericSetting, ...]:
    if not self.available:
        return ()
    return _SUPPORTED_NUMERIC_SETTINGS
```

Clamp setters:

```python
def set_rate(self, value: int) -> None:
    self._rate = clamp_percent(value)
```

Do the same for pitch and volume.

Keep `_prosody_percent()` as the driver-owned offset/multiplier mapping:

```python
@staticmethod
def _prosody_percent(command: PitchCommand | RateCommand | VolumeCommand, *, baseline: int) -> int:
    if command.mode == "multiplier":
        return round(command.multiplier * 100)
    if command.mode == "offset":
        if baseline == 0:
            return 100
        return round(((baseline + command.offset) / baseline) * 100)
    return 100
```

- [ ] **Step 6: Run driver tests**

Run: `pytest tests/unit/test_speech_backends.py -k "pyttsx3 or nvda_controller or numeric_setting or percent_helpers" -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/adapters/outputs/interfaces.py src/adapters/outputs/speech.py src/adapters/outputs/drivers/pyttsx3.py src/adapters/windows/nvda_controller.py tests/unit/test_speech_backends.py
git commit -m "feat: add driver-owned speech engine settings"
```

## Task 5: Expose Supported Settings Through Service And Controller

**Files:**
- Modify: `src/application/output/speech/service.py`
- Modify: `src/application/output/service.py`
- Modify: `src/apps/shared/speech_settings_controller.py`
- Test: `tests/unit/test_speech_service.py`
- Test: `tests/unit/test_output_service.py`
- Test: `tests/unit/test_speech_settings_controller.py`

- [ ] **Step 1: Write failing tests**

In `tests/unit/test_speech_settings_controller.py`, add to `FakeSpeech`:

```python
def get_supported_numeric_settings(self):
    return ("rate", "pitch", "volume")
```

Add:

```python
def test_speech_settings_controller_proxies_supported_numeric_settings():
    speech = FakeSpeech()
    controller = SpeechSettingsController(speech=speech)

    assert controller.get_supported_numeric_settings() == ("rate", "pitch", "volume")
```

In `tests/unit/test_output_service.py`, add:

```python
def test_queued_output_service_proxies_supported_numeric_settings() -> None:
    service, _created, _scheduler = build_service()

    assert service.get_supported_numeric_settings() == ()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_speech_settings_controller.py::test_speech_settings_controller_proxies_supported_numeric_settings tests/unit/test_output_service.py::test_queued_output_service_proxies_supported_numeric_settings -v`

Expected: FAIL because pass-through methods are missing.

- [ ] **Step 3: Add service/controller pass-through**

In `src/application/output/speech/service.py`:

```python
def get_supported_numeric_settings(self):
    return self._engine_manager.current_output.get_supported_numeric_settings()
```

In `src/application/output/service.py`, add the protocol method and `QueuedService` method:

```python
def get_supported_numeric_settings(self): ...

def get_supported_numeric_settings(self):
    return self._speech.get_supported_numeric_settings()
```

In `src/apps/shared/speech_settings_controller.py`:

```python
def get_supported_numeric_settings(self):
    return self._speech.get_supported_numeric_settings()
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_speech_settings_controller.py tests/unit/test_output_service.py tests/unit/test_speech_service.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/application/output/speech/service.py src/application/output/service.py src/apps/shared/speech_settings_controller.py tests/unit/test_speech_settings_controller.py tests/unit/test_output_service.py tests/unit/test_speech_service.py
git commit -m "feat: expose speech numeric setting support"
```

## Task 6: Rename App-Facing APIs And Events To Speech Engine

**Files:**
- Modify: `src/application/events.py`
- Modify: `src/apps/shared/speech_settings_controller.py`
- Modify: `src/apps/nvda_remote/service.py`
- Modify: `src/apps/key_echo/service.py`
- Modify: `src/apps/access8graph/service.py`
- Modify: use case alias modules under `src/apps/*/use_cases/speech_settings.py`
- Test: app service and use case tests

- [ ] **Step 1: Write failing tests**

Update app service tests to expect new methods:

```python
def test_key_echo_service_dispatches_typed_speech_engine_notification() -> None:
    service = build_service_with_fake_speech()
    seen = []
    service.set_status_listener(seen.append)

    service.set_speech_engine("Pyttsx3")

    assert seen[-1] == SpeechEngineChanged("Pyttsx3")
```

Apply equivalent tests in `tests/unit/test_nvda_remote_app_service.py` and `tests/unit/test_access8graph_app_service.py`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_key_echo_app_service.py -k "speech_engine" -v`

Expected: FAIL because `SpeechEngineChanged` and `set_speech_engine()` do not exist.

- [ ] **Step 3: Rename event and controller methods**

In `src/application/events.py`, replace:

```python
@dataclass(frozen=True)
class SpeechBackendChanged:
    backend_id: str
```

with:

```python
@dataclass(frozen=True)
class SpeechEngineChanged:
    engine_id: str
```

In `src/apps/shared/speech_settings_controller.py`, expose:

```python
def get_engine_options(self) -> tuple[tuple[str, str], ...]:
    return self._speech.get_engine_options()

def get_selected_engine(self) -> str:
    return self._speech.get_selected_engine()

def set_engine(self, engine_id: str) -> None:
    self._speech.set_engine(engine_id)
    if self._on_engine_changed is not None:
        self._on_engine_changed(engine_id)
```

Rename constructor callback from `on_backend_changed` to `on_engine_changed`.

In each app service, replace methods:

```python
def get_speech_engine_options(self) -> tuple[tuple[str, str], ...]:
    return self._speech_settings.get_engine_options()

def get_selected_speech_engine(self) -> str:
    return self._speech_settings.get_selected_engine()

def set_speech_engine(self, engine_id: str) -> None:
    self._speech_settings.set_engine(engine_id)
    self._notify_status_listener(SpeechEngineChanged(engine_id))
```

- [ ] **Step 4: Update imports and tests**

Replace all test imports and references:

```python
SpeechBackendChanged
get_speech_backend_options
get_selected_speech_backend
set_speech_backend
```

with:

```python
SpeechEngineChanged
get_speech_engine_options
get_selected_speech_engine
set_speech_engine
```

- [ ] **Step 5: Run focused app tests**

Run: `pytest tests/unit/test_key_echo_app_service.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_access8graph_app_service.py tests/unit/test_speech_settings_controller.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/application/events.py src/apps tests/unit/test_key_echo_app_service.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_access8graph_app_service.py tests/unit/test_speech_settings_controller.py
git commit -m "refactor: rename speech settings API to engine"
```

## Task 7: Replace Text Fields With Sliders And Capability Disabling

**Files:**
- Modify: `src/ui/shared/speech_controls.py`
- Modify: `tests/unit/test_app_wx.py`

- [ ] **Step 1: Extend fake wx with Slider and EVT_SLIDER**

In `tests/unit/test_app_wx.py`, add:

```python
fake_wx.EVT_SLIDER = object()
```

Add this fake control beside `TextCtrl`:

```python
class Slider:
    def __init__(self, parent, value=0, minValue=0, maxValue=100):
        self.parent = parent
        self._value = value
        self.minValue = minValue
        self.maxValue = maxValue
        self.enabled = True
        self.bindings = {}
        self.line_size = 1
        self.page_size = 10

    def GetValue(self):
        return self._value

    def SetValue(self, value):
        self._value = value

    def Enable(self, enabled=True):
        self.enabled = enabled

    def Disable(self):
        self.enabled = False

    def Bind(self, event, handler):
        self.bindings[event] = handler

    def SetLineSize(self, size):
        self.line_size = size

    def SetPageSize(self, size):
        self.page_size = size

fake_wx.Slider = Slider
```

- [ ] **Step 2: Write failing UI tests**

Update the speech frame test to expect sliders:

```python
def test_speech_settings_frame_uses_sliders_and_engine_labels(monkeypatch):
    install_fake_wx(monkeypatch)

    class FakeController:
        def __init__(self):
            self.engine_id = "NvdaController"
            self.engine_calls = []
            self.available_voices = ()
            self.rate = 60
            self.pitch = 50
            self.volume = 90

        def get_speech_engine_options(self):
            return (("NvdaController", "Nvda Controller"), ("Pyttsx3", "Pyttsx3"))

        def get_selected_speech_engine(self):
            return self.engine_id

        def set_speech_engine(self, engine_id):
            self.engine_calls.append(engine_id)
            self.engine_id = engine_id

        def get_available_voices(self):
            return self.available_voices

        def get_selected_voice(self):
            return None

        def get_supported_numeric_settings(self):
            return (
                SpeechNumericSetting("rate", "Rate"),
                SpeechNumericSetting("pitch", "Pitch"),
                SpeechNumericSetting("volume", "Volume"),
            )

        def get_rate(self):
            return self.rate

        def set_rate(self, value):
            self.rate = value

        def get_pitch(self):
            return self.pitch

        def set_pitch(self, value):
            self.pitch = value

        def get_volume(self):
            return self.volume

        def set_volume(self, value):
            self.volume = value

    SpeechSettingsFrame = importlib.import_module("ui.shared.speech_settings_frame").SpeechSettingsFrame
    frame = SpeechSettingsFrame(controller=FakeController())

    assert frame.speech_engine_choice.GetString(0) == "Nvda Controller"
    assert frame.rate_slider.GetValue() == 60
    assert frame.pitch_slider.GetValue() == 50
    assert frame.volume_slider.GetValue() == 90
    assert frame.voice_choice.enabled is False
```

Add a disabled setting test:

```python
def test_speech_settings_frame_disables_unsupported_numeric_settings(monkeypatch):
    install_fake_wx(monkeypatch)

    controller = FakeController()
    controller.supported_numeric_settings = (SpeechNumericSetting("rate", "Rate"),)
    frame = SpeechSettingsFrame(controller=controller)

    assert frame.rate_slider.enabled is True
    assert frame.pitch_slider.enabled is False
    assert frame.pitch_slider.GetValue() == 50
    assert frame.volume_slider.enabled is False
    assert frame.volume_slider.GetValue() == 50

    frame.pitch_slider.SetValue(80)
    frame._on_pitch_change(None)

    assert controller.pitch_calls == []
```

- [ ] **Step 3: Run UI tests to verify they fail**

Run: `pytest tests/unit/test_app_wx.py -k "speech_settings_frame" -v`

Expected: FAIL because controls are still text fields and backend-named.

- [ ] **Step 4: Update `SpeechControlsMixin`**

In `src/ui/shared/speech_controls.py`, use engine naming and sliders:

```python
self._speech_engine_options = self._get_speech_engine_options()
self.speech_engine_choice = wx.Choice(
    panel,
    choices=[label for _engine_id, label in self._speech_engine_options],
)
self.rate_slider = wx.Slider(panel, value=50, minValue=0, maxValue=100)
self.pitch_slider = wx.Slider(panel, value=50, minValue=0, maxValue=100)
self.volume_slider = wx.Slider(panel, value=50, minValue=0, maxValue=100)
```

Bind slider events:

```python
self.speech_engine_choice.Bind(wx.EVT_CHOICE, self._on_speech_engine_change)
self.rate_slider.Bind(wx.EVT_SLIDER, self._on_rate_change)
self.pitch_slider.Bind(wx.EVT_SLIDER, self._on_pitch_change)
self.volume_slider.Bind(wx.EVT_SLIDER, self._on_volume_change)
```

Replace `_set_int_control_value()` with:

```python
def _set_slider_value(self, slider, setter_name: str, setting_id: str) -> None:
    if self.controller is None or not hasattr(self.controller, setter_name):
        return
    if setting_id not in self._supported_numeric_setting_ids():
        return
    getattr(self.controller, setter_name)(slider.GetValue())
```

Add:

```python
def _supported_numeric_setting_ids(self) -> set[str]:
    return {setting.id for setting in self._get_supported_numeric_settings()}
```

Sync sliders:

```python
def _sync_numeric_slider(self, slider, setting_id: str, value: int | None) -> None:
    settings = {setting.id: setting for setting in self._get_supported_numeric_settings()}
    setting = settings.get(setting_id)
    if setting is None:
        slider.SetValue(50)
        slider.Disable()
        return
    slider.SetLineSize(setting.step)
    slider.SetPageSize(setting.large_step)
    slider.SetValue(setting.default_percent if value is None else value)
    slider.Enable(True)
```

Voice disabling:

```python
if self._voice_options:
    self.voice_choice.Enable(True)
    self.voice_choice.SetSelection(self._voice_selection_for_current_value())
else:
    self.voice_choice.Disable()
    self.voice_choice.SetSelection(-1)
```

- [ ] **Step 5: Run UI tests**

Run: `pytest tests/unit/test_app_wx.py -k "speech_settings_frame or speech_engine" -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ui/shared/speech_controls.py tests/unit/test_app_wx.py
git commit -m "feat: use sliders for speech engine settings"
```

## Task 8: Add Speech Engine Config Store And Persistence Callbacks

**Files:**
- Modify: `src/application/config.py`
- Modify: `src/apps/shared/speech_settings_controller.py`
- Modify: `src/apps/nvda_remote/main.py`
- Test: `tests/unit/test_speech_backends.py`
- Test: `tests/unit/test_app_wx.py`

- [ ] **Step 1: Write config store tests**

Replace the old config store test in `tests/unit/test_speech_backends.py` with:

```python
from application.config import SpeechEngineConfigStore


def test_speech_engine_config_store_loads_and_saves_engine_id(tmp_path):
    config_path = tmp_path / "config.json"
    store = SpeechEngineConfigStore(config_path)

    assert store.load_engine_id(default_engine_id="NvdaController") == "NvdaController"

    store.save_engine_id("Pyttsx3")

    assert json.loads(config_path.read_text(encoding="utf-8")) == {
        "speech_engine": "Pyttsx3"
    }
    assert store.load_engine_id(default_engine_id="NvdaController") == "Pyttsx3"


def test_speech_engine_config_store_loads_and_saves_per_engine_settings(tmp_path):
    config_path = tmp_path / "config.json"
    store = SpeechEngineConfigStore(config_path)

    store.save_voice("Pyttsx3", "voice-1")
    store.save_numeric_setting("Pyttsx3", "rate", 120)
    store.save_numeric_setting("Pyttsx3", "volume", -20)

    assert store.load_voice("Pyttsx3") == "voice-1"
    assert store.load_numeric_setting("Pyttsx3", "rate") == 100
    assert store.load_numeric_setting("Pyttsx3", "volume") == 0
    assert store.load_numeric_setting("Pyttsx3", "pitch") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_speech_backends.py -k "config_store" -v`

Expected: FAIL because `SpeechEngineConfigStore` and per-engine setting methods do not exist.

- [ ] **Step 3: Replace config store**

Replace `src/application/config.py` with:

```python
import json
from pathlib import Path

from application.output.speech.settings import clamp_percent


class SpeechEngineConfigStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load_engine_id(self, *, default_engine_id: str) -> str:
        payload = self._read()
        engine_id = payload.get("speech_engine")
        if not isinstance(engine_id, str) or not engine_id:
            return default_engine_id
        return engine_id

    def save_engine_id(self, engine_id: str) -> None:
        payload = self._read()
        payload["speech_engine"] = engine_id
        self._write(payload)

    def load_voice(self, engine_id: str) -> str | None:
        value = self._engine_payload(engine_id).get("voice")
        return value if isinstance(value, str) and value else None

    def save_voice(self, engine_id: str, voice_id: str) -> None:
        payload = self._read()
        engine_payload = self._ensure_engine_payload(payload, engine_id)
        engine_payload["voice"] = voice_id
        self._write(payload)

    def load_numeric_setting(self, engine_id: str, setting_id: str) -> int | None:
        value = self._engine_payload(engine_id).get(setting_id)
        if not isinstance(value, int):
            return None
        return clamp_percent(value)

    def save_numeric_setting(self, engine_id: str, setting_id: str, value: int) -> None:
        payload = self._read()
        engine_payload = self._ensure_engine_payload(payload, engine_id)
        engine_payload[setting_id] = clamp_percent(value)
        self._write(payload)

    def _engine_payload(self, engine_id: str) -> dict[str, object]:
        speech_engines = self._read().get("speech_engines")
        if not isinstance(speech_engines, dict):
            return {}
        payload = speech_engines.get(engine_id)
        return payload if isinstance(payload, dict) else {}

    def _ensure_engine_payload(self, payload: dict[str, object], engine_id: str) -> dict[str, object]:
        speech_engines = payload.setdefault("speech_engines", {})
        if not isinstance(speech_engines, dict):
            speech_engines = {}
            payload["speech_engines"] = speech_engines
        engine_payload = speech_engines.setdefault(engine_id, {})
        if not isinstance(engine_payload, dict):
            engine_payload = {}
            speech_engines[engine_id] = engine_payload
        return engine_payload

    def _read(self) -> dict[str, object]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write(self, payload: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
```

- [ ] **Step 4: Add controller callbacks**

In `src/apps/shared/speech_settings_controller.py`, extend `__init__`:

```python
def __init__(
    self,
    *,
    speech: SpeechServiceProtocol,
    on_engine_changed: Callable[[str], None] | None = None,
    on_voice_changed: Callable[[str, str], None] | None = None,
    on_numeric_setting_changed: Callable[[str, str, int], None] | None = None,
) -> None:
    self._speech = speech
    self._on_engine_changed = on_engine_changed
    self._on_voice_changed = on_voice_changed
    self._on_numeric_setting_changed = on_numeric_setting_changed
```

After successful voice set:

```python
def set_voice(self, voice_id: str) -> None:
    self._speech.set_voice(voice_id)
    if self._on_voice_changed is not None:
        self._on_voice_changed(self.get_selected_engine(), voice_id)
```

For numeric setters:

```python
def set_rate(self, value: int) -> None:
    self._speech.set_rate(value)
    if self._on_numeric_setting_changed is not None:
        self._on_numeric_setting_changed(self.get_selected_engine(), "rate", value)
```

Repeat for `pitch` and `volume`.

- [ ] **Step 5: Wire NVDA Remote runtime persistence**

In `src/apps/nvda_remote/main.py`, import and use `SpeechEngineConfigStore`.

Load:

```python
config_store = SpeechEngineConfigStore(default_config_path())
default_engine_id = provider.default_speech_engine_id()
selected_engine_id = config_store.load_engine_id(default_engine_id=default_engine_id)
```

After `parts` are built, apply saved settings:

```python
def _apply_saved_speech_settings(speech: SpeechService, engine_id: str) -> None:
    voice_id = config_store.load_voice(engine_id)
    available_voice_ids = {voice_id for voice_id, _label in speech.list_voices()}
    if voice_id is not None and voice_id in available_voice_ids:
        speech.set_voice(voice_id)
    supported = {setting.id for setting in speech.get_supported_numeric_settings()}
    for setting_id, setter in (
        ("rate", speech.set_rate),
        ("pitch", speech.set_pitch),
        ("volume", speech.set_volume),
    ):
        value = config_store.load_numeric_setting(engine_id, setting_id)
        if value is not None and setting_id in supported:
            setter(value)
```

Call it for the selected engine:

```python
_apply_saved_speech_settings(parts.output.speech, parts.output.speech.get_selected_engine())
```

Wire callbacks into `NvdaRemoteAppService`:

```python
on_speech_engine_changed=config_store.save_engine_id,
on_voice_changed=config_store.save_voice,
on_numeric_setting_changed=config_store.save_numeric_setting,
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/unit/test_speech_backends.py -k "config_store" -v`

Expected: PASS.

Run: `pytest tests/unit/test_app_wx.py -k "config" -v`

Expected: PASS after updating fake config store method names.

- [ ] **Step 7: Commit**

```bash
git add src/application/config.py src/apps/shared/speech_settings_controller.py src/apps/nvda_remote/main.py tests/unit/test_speech_backends.py tests/unit/test_app_wx.py
git commit -m "feat: persist speech engine settings"
```

## Task 9: Complete UI/App Test Renames And Remove Old Backend Names

**Files:**
- Modify: all touched tests and source files still containing public backend terminology

- [ ] **Step 1: Search for remaining old public names**

Run:

```bash
rg -n "SpeechBackend|speech_backend|get_speech_backend|set_speech_backend|selected_backend|backend_options|backend_id|SpeechBackendChanged" src tests -S
```

Expected: Remaining matches are either test-local variables in files not yet updated or private transitional variables.

- [ ] **Step 2: Replace remaining public names**

Apply these replacements where they describe the speech engine domain:

```text
SpeechBackend -> SpeechEngine
speech_backend -> speech_engine
get_speech_backend_options -> get_speech_engine_options
get_selected_speech_backend -> get_selected_speech_engine
set_speech_backend -> set_speech_engine
selected_backend_id -> selected_engine_id
backend_options -> engine_options
backend_id -> engine_id
SpeechBackendChanged -> SpeechEngineChanged
```

Do not rename unrelated local variables for non-speech concepts.

- [ ] **Step 3: Ensure real engine ids are PascalCase**

Run:

```bash
rg -n '"nvda_controller"|"pyttsx3"' src tests -S
```

Expected: Real engine ids should be `"NvdaController"` and `"Pyttsx3"`. Lowercase strings may remain only in module names, import paths, or documentation references where they are not engine ids.

- [ ] **Step 4: Run broad unit tests**

Run:

```bash
pytest tests/unit/test_speech_backends.py tests/unit/test_speech_service.py tests/unit/test_output_service.py tests/unit/test_app_wx.py tests/unit/test_bootstrap_platform.py tests/unit/test_bootstrap_output.py tests/unit/test_bootstrap_app_runtime.py tests/unit/test_nvda_remote_app_service.py tests/unit/test_key_echo_app_service.py tests/unit/test_access8graph_app_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src tests
git commit -m "refactor: complete speech engine terminology migration"
```

## Task 10: Final Verification

**Files:**
- No source changes expected unless verification exposes a bug.

- [ ] **Step 1: Run the full test suite**

Run:

```bash
pytest tests/unit tests/integration -v
```

Expected: PASS.

- [ ] **Step 2: Inspect final diff**

Run:

```bash
git status --short
git log --oneline -8
```

Expected: working tree contains only intentional changes for this feature, ideally clean after commits.

- [ ] **Step 3: Manual smoke check on a machine with wx available**

Run:

```bash
PYTHONPATH=src python -m apps.nvda_remote.main
```

Expected:

- Speech settings window labels show `Speech Engine`.
- Engine choices show `Nvda Controller` and `Pyttsx3`.
- Rate, pitch, and volume are sliders from `0` to `100`.
- Empty voice list disables the voice choice.
- Unsupported numeric settings disable their sliders.
- Changing a slider persists a normalized value in config under `speech_engines.<engine_id>.<setting_id>`.

- [ ] **Step 4: Commit any verification fixes**

If verification required source or test changes:

```bash
git add src tests
git commit -m "fix: complete speech engine settings verification"
```

If no fixes were needed, do not create an empty commit.

## Self-Review

- Spec coverage: The plan covers driver-owned settings, normalized `0-100` values, speech engine terminology, fixed ids/labels, unsupported numeric slider disabling, voice dropdown disabling, per-engine persistence, and verification.
- Placeholder scan: No unfinished-marker placeholders or vague deferred-work instructions remain.
- Type consistency: The plan uses `SpeechEngineOption`, `SpeechEngineManager`, `SpeechNumericSetting`, `SpeechEngineChanged`, `get_supported_numeric_settings()`, `get_speech_engine_options()`, `get_selected_speech_engine()`, and `set_speech_engine()` consistently after their defining tasks.
