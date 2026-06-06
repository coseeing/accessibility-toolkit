from application.output_scheduler import OutputScheduler
from application.output_service import QueuedOutputService
from application.speech_backends import SpeechBackendOption
from application.speech_service import SpeechService
from interop.speech.speech_sequence import SpeechSequence


class FakeSpeechOutput:
    def __init__(self, name: str) -> None:
        self.name = name
        self.spoken: list[SpeechSequence] = []
        self.cancelled = 0
        self.paused: list[bool] = []
        self.voice: str | None = None
        self.rate: int | None = None
        self.pitch: int | None = None
        self.volume: int | None = None

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


def build_service() -> tuple[QueuedOutputService, list[FakeSpeechOutput], OutputScheduler]:
    created: list[FakeSpeechOutput] = []

    def factory(name: str):
        def create() -> FakeSpeechOutput:
            output = FakeSpeechOutput(name)
            created.append(output)
            return output

        return create

    scheduler = OutputScheduler()
    speech = SpeechService(
        backend_options=(
            SpeechBackendOption(
                backend_id="nvda_controller",
                label="NVDA Controller",
                factory=factory("nvda_controller"),
            ),
            SpeechBackendOption(
                backend_id="pyttsx3",
                label="pyttsx3",
                factory=factory("pyttsx3"),
            ),
        ),
        selected_backend_id="nvda_controller",
    )
    return QueuedOutputService(speech=speech, scheduler=scheduler), created, scheduler


def test_queued_output_service_proxies_speech_calls() -> None:
    service, created, _scheduler = build_service()

    speech = SpeechSequence(items=("hello",))
    service.speak(speech)
    service.pause(True)
    service.cancel()

    assert created[0].spoken == [speech]
    assert created[0].paused == [True]
    assert created[0].cancelled == 1
    service.shutdown()


def test_queued_output_service_switches_backend_via_speech_service() -> None:
    service, created, _scheduler = build_service()

    service.set_backend("pyttsx3")
    service.speak(SpeechSequence(items=("next",)))

    assert created[0].cancelled == 1
    assert created[1].spoken == [SpeechSequence(items=("next",))]
    assert service.get_selected_backend() == "pyttsx3"
    service.shutdown()


def test_queued_output_service_proxies_configuration_calls() -> None:
    service, created, _scheduler = build_service()

    service.set_voice("voice-1")
    service.set_rate(120)
    service.set_pitch(4)
    service.set_volume(80)

    assert service.list_voices() == (("voice-1", "Voice 1"),)
    assert service.get_voice() == "voice-1"
    assert service.get_rate() == 120
    assert service.get_pitch() == 4
    assert service.get_volume() == 80
    assert created[0].voice == "voice-1"
    service.shutdown()
