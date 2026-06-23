from application.output import Capabilities
from apps.access8graph.output import Access8GraphFlowOutput
from interop.speech.speech_commands import BreakCommand
from interop.speech.speech_sequence import SpeechSequence


class FakeSpeech:
    def __init__(self) -> None:
        self.calls = []

    def speak(self, sequence: SpeechSequence) -> None:
        self.calls.append(("speak", sequence))

    def cancel(self) -> None:
        self.calls.append(("cancel", None))

    def pause(self, is_paused: bool) -> None:
        self.calls.append(("pause", is_paused))

    def get_backend_options(self):
        return ()

    def get_selected_backend(self):
        return "default"

    def set_backend(self, backend_id):
        self.calls.append(("set_backend", backend_id))

    def list_voices(self):
        return ()

    def get_voice(self):
        return None

    def set_voice(self, voice_id):
        self.calls.append(("set_voice", voice_id))

    def get_rate(self):
        return None

    def set_rate(self, value):
        self.calls.append(("set_rate", value))

    def get_pitch(self):
        return None

    def set_pitch(self, value):
        self.calls.append(("set_pitch", value))

    def get_volume(self):
        return None

    def set_volume(self, value):
        self.calls.append(("set_volume", value))

    def shutdown(self):
        self.calls.append(("shutdown", None))


class FakeTone:
    def __init__(self) -> None:
        self.calls = []

    def beep(self, frequency: int, duration: int) -> None:
        self.calls.append((frequency, duration))


def test_output_speaks_non_empty_items_with_breaks_between_them() -> None:
    speech = FakeSpeech()
    output = Access8GraphFlowOutput(Capabilities(speech=speech))

    output.speak(["", "功能選單開啟", "方向探索", "", "3 之 1"])

    assert speech.calls == [
        ("speak", SpeechSequence(items=(
            "功能選單開啟",
            BreakCommand(time=1),
            "方向探索",
            BreakCommand(time=1),
            "3 之 1",
        ))),
    ]


def test_output_does_not_speak_when_all_items_are_empty() -> None:
    speech = FakeSpeech()
    output = Access8GraphFlowOutput(Capabilities(speech=speech))

    output.speak(["", None, ""])

    assert speech.calls == []


def test_output_cancels_speech() -> None:
    speech = FakeSpeech()
    output = Access8GraphFlowOutput(Capabilities(speech=speech))

    output.cancel_speech()

    assert speech.calls == [("cancel", None)]


def test_output_beep_failure_uses_tone_when_available() -> None:
    speech = FakeSpeech()
    tone = FakeTone()
    output = Access8GraphFlowOutput(Capabilities(speech=speech, tone=tone))

    output.beep_failure()

    assert tone.calls == [(100, 100)]


def test_output_beep_failure_is_noop_without_tone() -> None:
    speech = FakeSpeech()
    output = Access8GraphFlowOutput(Capabilities(speech=speech))

    output.beep_failure()

    assert speech.calls == []
