import pytest

from application.output import Capabilities
from application.output.speech import SpeechEngineOption, SpeechNumericSetting, SpeechService
from interop.speech.speech_sequence import SpeechSequence


class FakeSpeechOutput:
    def __init__(self, name: str) -> None:
        self.name = name
        self.spoken: list[SpeechSequence] = []
        self.cancelled = 0
        self.paused: list[bool] = []
        self.voice: str | None = None
        self.rate = 100
        self.pitch = 100
        self.volume = 100
        self.supported_numeric_settings = (
            SpeechNumericSetting(id="rate", label="Rate"),
            SpeechNumericSetting(id="pitch", label="Pitch"),
            SpeechNumericSetting(id="volume", label="Volume"),
        )

    def speak(self, sequence: SpeechSequence) -> None:
        self.spoken.append(sequence)

    def cancel(self) -> None:
        self.cancelled += 1

    def pause(self, is_paused: bool) -> None:
        self.paused.append(is_paused)

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return (("voice-1", "Voice 1"),)

    def get_voice(self) -> str | None:
        return self.voice

    def set_voice(self, voice_id: str) -> None:
        self.voice = voice_id

    def get_rate(self) -> int | None:
        return self.rate

    def set_rate(self, value: int) -> None:
        self.rate = value

    def get_pitch(self) -> int | None:
        return self.pitch

    def set_pitch(self, value: int) -> None:
        self.pitch = value

    def get_volume(self) -> int | None:
        return self.volume

    def set_volume(self, value: int) -> None:
        self.volume = value

    def get_supported_numeric_settings(self):
        return self.supported_numeric_settings


def test_speech_service_switches_engines_and_routes_calls() -> None:
    created: list[FakeSpeechOutput] = []

    def build(name: str):
        def factory() -> FakeSpeechOutput:
            output = FakeSpeechOutput(name)
            created.append(output)
            return output

        return factory

    service = SpeechService(
        engine_options=(
            SpeechEngineOption(
                engine_id="NvdaController",
                label="Nvda Controller",
                factory=build("nvda"),
            ),
            SpeechEngineOption(
                engine_id="Pyttsx3",
                label="Pyttsx3",
                factory=build("pyttsx3"),
            ),
        ),
        selected_engine_id="NvdaController",
    )

    speech = SpeechSequence(items=("hello",))
    service.speak(speech)
    service.pause(True)
    service.set_voice("voice-1")
    service.set_rate(80)
    service.set_pitch(70)
    service.set_volume(60)

    assert service.get_engine_options() == (
        ("NvdaController", "Nvda Controller"),
        ("Pyttsx3", "Pyttsx3"),
    )
    assert service.get_selected_engine() == "NvdaController"
    assert created[0].spoken == [speech]
    assert created[0].paused == [True]
    assert created[0].get_voice() == "voice-1"
    assert created[0].get_rate() == 80
    assert created[0].get_pitch() == 70
    assert created[0].get_volume() == 60

    service.set_engine("Pyttsx3")
    service.cancel()
    service.speak(SpeechSequence(items=("world",)))

    assert service.get_selected_engine() == "Pyttsx3"
    assert created[0].cancelled == 1
    assert created[1].cancelled == 1
    assert created[1].spoken == [SpeechSequence(items=("world",))]
    assert service.list_voices() == (("voice-1", "Voice 1"),)


def test_output_capabilities_exposes_shared_outputs() -> None:
    speech = FakeSpeechOutput("nvda")

    capabilities = Capabilities(speech=SpeechService.single_backend(speech))

    assert capabilities.speech.get_selected_engine() == "default"
    assert capabilities.tone is None
    assert capabilities.braille is None


def test_speech_service_rejects_unknown_engine_id() -> None:
    service = SpeechService(
        engine_options=(
            SpeechEngineOption(
                engine_id="NvdaController",
                label="Nvda Controller",
                factory=lambda: FakeSpeechOutput("nvda"),
            ),
        ),
        selected_engine_id="NvdaController",
    )

    with pytest.raises(ValueError, match="Unknown speech engine"):
        service.set_engine("missing")


def test_speech_service_exposes_supported_numeric_settings() -> None:
    service = SpeechService(
        engine_options=(
            SpeechEngineOption(
                engine_id="NvdaController",
                label="Nvda Controller",
                factory=lambda: FakeSpeechOutput("nvda"),
            ),
        ),
        selected_engine_id="NvdaController",
    )

    assert service.get_supported_numeric_settings() == (
        SpeechNumericSetting(id="rate", label="Rate"),
        SpeechNumericSetting(id="pitch", label="Pitch"),
        SpeechNumericSetting(id="volume", label="Volume"),
    )
