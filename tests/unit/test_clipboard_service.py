from adapters.windows.clipboard import WindowsClipboardService
from adapters.windows.nvda_controller import NvdaControllerSpeechOutput
from remote_core.models.speech_commands import BreakCommand
from remote_core.models.speech_sequence import SpeechSequence


def test_windows_clipboard_service_round_trip(monkeypatch):
    store = {"text": ""}
    service = WindowsClipboardService(
        reader=lambda: store["text"],
        writer=lambda value: store.__setitem__("text", value),
    )
    service.set_text("hello")
    assert service.get_text() == "hello"


def test_nvda_speech_output_gracefully_degrades_when_unavailable():
    output = NvdaControllerSpeechOutput(controller=None)
    speech = SpeechSequence(items=("hello",))
    output.speak(speech)
    assert output.available is False


def test_nvda_speech_output_speaks_joined_text_segments_only():
    class Controller:
        def __init__(self):
            self.spoken: list[tuple[str, int, int, bool]] = []

        def nvdaController_speakSsml(
            self,
            ssml: str,
            symbol_level: int,
            priority: int,
            asynchronous: bool,
        ) -> None:
            self.spoken.append((ssml, symbol_level, priority, asynchronous))

    controller = Controller()
    output = NvdaControllerSpeechOutput(controller=controller)
    speech = SpeechSequence(items=("hello", BreakCommand(time=100), "world"))

    output.speak(speech)

    assert output.available is True
    assert controller.spoken == [
        ('<speak>hello<break time="100ms"/>world</speak>', 0, 0, True)
    ]


def test_nvda_speech_output_skips_empty_speech_but_emits_break_only_ssml():
    class Controller:
        def __init__(self):
            self.spoken: list[tuple[str, int, int, bool]] = []

        def nvdaController_speakSsml(
            self,
            ssml: str,
            symbol_level: int,
            priority: int,
            asynchronous: bool,
        ) -> None:
            self.spoken.append((ssml, symbol_level, priority, asynchronous))

    controller = Controller()
    output = NvdaControllerSpeechOutput(controller=controller)

    output.speak(SpeechSequence(items=()))
    output.speak(SpeechSequence(items=(BreakCommand(time=100),)))

    assert controller.spoken == [
        ('<speak><break time="100ms"/></speak>', 0, 0, True)
    ]


def test_nvda_speech_output_cancel_only_when_available():
    class Controller:
        def __init__(self):
            self.cancel_count = 0

        def nvdaController_cancelSpeech(self) -> None:
            self.cancel_count += 1

        def nvdaController_speakSsml(
            self,
            ssml: str,
            symbol_level: int,
            priority: int,
            asynchronous: bool,
        ) -> None:
            return None

    controller = Controller()
    NvdaControllerSpeechOutput(controller=controller).cancel()
    NvdaControllerSpeechOutput(controller=None).cancel()

    assert controller.cancel_count == 1
