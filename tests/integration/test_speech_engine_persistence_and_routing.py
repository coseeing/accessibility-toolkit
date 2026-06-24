import json
from typing import Callable

import pytest

from application.config import SpeechEngineConfigStore
from application.output.speech import SpeechEngineOption, SpeechService, SpeechNumericSetting
from interop.speech.speech_sequence import SpeechSequence


class RecordingSpeechOutput:
    """A minimal speech engine driver that owns normalized numeric settings."""

    _SUPPORTED = (
        SpeechNumericSetting(id="rate", label="Rate"),
        SpeechNumericSetting(id="pitch", label="Pitch"),
        SpeechNumericSetting(id="volume", label="Volume"),
    )

    def __init__(self, name: str, voices: tuple[tuple[str, str], ...]) -> None:
        self.name = name
        self._voices = voices
        self._voice_id: str | None = voices[0][0] if voices else None
        self._rate = 50
        self._pitch = 50
        self._volume = 50
        self.cancel_calls = 0
        self.spoken: list[SpeechSequence] = []

    def speak(self, sequence: SpeechSequence) -> None:
        self.spoken.append(sequence)

    def cancel(self) -> None:
        self.cancel_calls += 1

    def pause(self, is_paused: bool) -> None:
        return None

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return self._voices

    def get_voice(self) -> str | None:
        return self._voice_id

    def set_voice(self, voice_id: str) -> None:
        self._voice_id = voice_id

    def get_supported_numeric_settings(self) -> tuple[SpeechNumericSetting, ...]:
        return self._SUPPORTED

    def get_rate(self) -> int | None:
        return self._rate

    def set_rate(self, value: int) -> None:
        self._rate = max(0, min(100, int(value)))

    def get_pitch(self) -> int | None:
        return self._pitch

    def set_pitch(self, value: int) -> None:
        self._pitch = max(0, min(100, int(value)))

    def get_volume(self) -> int | None:
        return self._volume

    def set_volume(self, value: int) -> None:
        self._volume = max(0, min(100, int(value)))


def _build_engines() -> tuple[dict[str, RecordingSpeechOutput], tuple[SpeechEngineOption, ...]]:
    """Return (engine objects by id, engine options) sharing the same outputs."""
    pyttsx3 = RecordingSpeechOutput("Pyttsx3", (("voice-1", "Voice One"),))
    nvda = RecordingSpeechOutput("NvdaController", ())
    outputs = {"Pyttsx3": pyttsx3, "NvdaController": nvda}
    options = (
        SpeechEngineOption(
            engine_id="NvdaController",
            label="Nvda Controller",
            factory=lambda: nvda,
        ),
        SpeechEngineOption(
            engine_id="Pyttsx3",
            label="Pyttsx3",
            factory=lambda: pyttsx3,
        ),
    )
    return outputs, options


def _apply_saved_settings(
    speech: SpeechService,
    store: SpeechEngineConfigStore,
    engine_id: str,
) -> None:
    """Mirror apps/nvda_remote/main._apply_saved_speech_settings."""
    voice_id = store.load_voice(engine_id)
    if voice_id is not None and voice_id in {vid for vid, _ in speech.list_voices()}:
        speech.set_voice(voice_id)
    supported = {setting.id for setting in speech.get_supported_numeric_settings()}
    for setting_id, setter in (
        ("rate", speech.set_rate),
        ("pitch", speech.set_pitch),
        ("volume", speech.set_volume),
    ):
        value = store.load_numeric_setting(engine_id, setting_id)
        if value is not None and setting_id in supported:
            setter(value)


def test_persisted_engine_and_normalized_values_are_restored_on_restart(tmp_path):
    outputs, options = _build_engines()
    config_path = tmp_path / "client-config.json"
    store = SpeechEngineConfigStore(config_path)
    store.save_engine_id("Pyttsx3")
    store.save_voice("Pyttsx3", "voice-1")
    store.save_numeric_setting("Pyttsx3", "rate", 73)
    store.save_numeric_setting("Pyttsx3", "pitch", 21)
    store.save_numeric_setting("Pyttsx3", "volume", 88)

    # Simulate a restart: load the persisted id, build the service, then apply.
    selected = store.load_engine_id(default_engine_id="NvdaController")
    speech = SpeechService(engine_options=options, selected_engine_id=selected)
    _apply_saved_settings(speech, store, selected)

    assert speech.get_selected_engine() == "Pyttsx3"
    assert outputs["Pyttsx3"].cancel_calls == 0  # selected engine not canceled
    assert speech.get_voice() == "voice-1"
    assert speech.get_rate() == 73
    assert speech.get_pitch() == 21
    assert speech.get_volume() == 88
    # Config only ever stores normalized percentages, never raw values.
    assert json.loads(config_path.read_text(encoding="utf-8"))["speech_engines"][
        "Pyttsx3"
    ] == {"voice": "voice-1", "rate": 73, "pitch": 21, "volume": 88}


def test_per_engine_settings_are_applied_independently_after_switch(tmp_path):
    outputs, options = _build_engines()
    store = SpeechEngineConfigStore(tmp_path / "client-config.json")
    store.save_numeric_setting("Pyttsx3", "rate", 73)
    store.save_numeric_setting("Pyttsx3", "volume", 88)
    store.save_numeric_setting("NvdaController", "rate", 30)
    store.save_numeric_setting("NvdaController", "pitch", 40)

    speech = SpeechService(engine_options=options, selected_engine_id="NvdaController")
    _apply_saved_settings(speech, store, speech.get_selected_engine())

    # NvdaController receives its own saved values; Pyttsx3 stays at defaults.
    assert outputs["NvdaController"].get_rate() == 30
    assert outputs["NvdaController"].get_pitch() == 40
    assert outputs["Pyttsx3"].get_rate() == 50
    assert outputs["Pyttsx3"].get_volume() == 50
    assert outputs["NvdaController"].cancel_calls == 0

    speech.set_engine("Pyttsx3")
    _apply_saved_settings(speech, store, speech.get_selected_engine())

    # After switching, the previous engine was canceled exactly once and Pyttsx3
    # now reflects its own per-engine persisted values, not the global ones.
    assert outputs["NvdaController"].cancel_calls == 1
    assert speech.get_selected_engine() == "Pyttsx3"
    assert speech.get_rate() == 73
    assert speech.get_volume() == 88
    # Pitch was never persisted for Pyttsx3, so it remains the driver default.
    assert speech.get_pitch() == 50


def test_incoming_speech_sequences_route_through_selected_engine_unchanged():
    outputs, options = _build_engines()
    speech = SpeechService(engine_options=options, selected_engine_id="NvdaController")

    first = SpeechSequence(items=("hello", "world"))
    speech.speak(first)

    speech.set_engine("Pyttsx3")
    second = SpeechSequence(items=("after", "switch"))
    speech.speak(second)

    # Each engine received exactly the sequence addressed to it, unchanged.
    assert outputs["NvdaController"].spoken == [first]
    assert outputs["Pyttsx3"].spoken == [second]
    # NvdaController was canceled when switching away from it.
    assert outputs["NvdaController"].cancel_calls == 1
    assert outputs["Pyttsx3"].cancel_calls == 0


def _factory_raises() -> Callable[[], RecordingSpeechOutput]:
    def factory() -> RecordingSpeechOutput:
        raise RuntimeError("engine unavailable")

    return factory


def test_engine_switch_failure_keeps_current_engine_active():
    pyttsx3 = RecordingSpeechOutput("Pyttsx3", ())
    options = (
        SpeechEngineOption(
            engine_id="Pyttsx3",
            label="Pyttsx3",
            factory=lambda: pyttsx3,
        ),
        SpeechEngineOption(
            engine_id="Broken",
            label="Broken",
            factory=_factory_raises(),
        ),
    )
    speech = SpeechService(engine_options=options, selected_engine_id="Pyttsx3")

    with pytest.raises(RuntimeError, match="engine unavailable"):
        speech.set_engine("Broken")

    # The current engine remains active, selected, and able to speak afterwards.
    assert speech.get_selected_engine() == "Pyttsx3"
    assert pyttsx3.cancel_calls == 0
    sequence = SpeechSequence(items=("recovered",))
    speech.speak(sequence)
    assert pyttsx3.spoken == [sequence]