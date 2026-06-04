from application.services import OutputManager
from remote_core.models.speech_sequence import SpeechSequence


class FakeSpeechOutput:
    def __init__(self):
        self.cancel_count = 0
        self.pauses = []
        self.spoken = []

    def speak(self, speech):
        self.spoken.append(speech)

    def cancel(self):
        self.cancel_count += 1

    def pause(self, is_paused: bool):
        self.pauses.append(is_paused)

    def list_voices(self):
        return ()

    def get_voice(self):
        return None

    def set_voice(self, voice_id: str):
        return None

    def get_rate(self):
        return None

    def set_rate(self, value: int):
        return None

    def get_pitch(self):
        return None

    def set_pitch(self, value: int):
        return None

    def get_volume(self):
        return None

    def set_volume(self, value: int):
        return None


class FakeClipboard:
    def __init__(self):
        self.text = ""

    def set_text(self, text: str) -> None:
        self.text = text

    def get_text(self) -> str:
        return self.text


def test_output_manager_routes_cancel_and_pause_to_speech_output():
    speech_output = FakeSpeechOutput()
    manager = OutputManager(speech_output=speech_output, clipboard=FakeClipboard())

    manager.handle_cancel()
    manager.handle_pause(True)
    manager.handle_pause(False)

    assert speech_output.cancel_count == 1
    assert speech_output.pauses == [True, False]


def test_output_manager_passes_sequence_to_backend():
    speech_output = FakeSpeechOutput()
    manager = OutputManager(speech_output=speech_output, clipboard=FakeClipboard())
    sequence = SpeechSequence(items=("hello",))

    manager.handle_speech(sequence)

    assert speech_output.spoken == [sequence]


def test_output_manager_replaces_speech_output_after_canceling_previous():
    first = FakeSpeechOutput()
    second = FakeSpeechOutput()
    manager = OutputManager(speech_output=first, clipboard=FakeClipboard())

    manager.set_speech_output(second)
    manager.handle_cancel()

    assert first.cancel_count == 1
    assert second.cancel_count == 1
