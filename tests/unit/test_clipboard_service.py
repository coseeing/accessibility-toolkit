from adapters.windows.clipboard import WindowsClipboardService
from adapters.windows.nvda_controller import NvdaControllerSpeechOutput
from remote_core.models.speech import NormalizedSpeech, SpeechSegment


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
    speech = NormalizedSpeech((SpeechSegment(kind="text", value="hello"),))
    output.speak(speech)
    assert output.available is False


def test_nvda_speech_output_speaks_joined_text_segments_only():
    class Controller:
        def __init__(self):
            self.spoken: list[str] = []

        def speakText(self, text: str) -> None:
            self.spoken.append(text)

    controller = Controller()
    output = NvdaControllerSpeechOutput(controller=controller)
    speech = NormalizedSpeech(
        (
            SpeechSegment(kind="text", value="hello"),
            SpeechSegment(kind="break", value=100),
            SpeechSegment(kind="text", value="world"),
        )
    )

    output.speak(speech)

    assert output.available is True
    assert controller.spoken == ["hello world"]


def test_nvda_speech_output_ignores_empty_or_non_text_speech():
    class Controller:
        def __init__(self):
            self.spoken: list[str] = []

        def speakText(self, text: str) -> None:
            self.spoken.append(text)

    controller = Controller()
    output = NvdaControllerSpeechOutput(controller=controller)

    output.speak(NormalizedSpeech(()))
    output.speak(NormalizedSpeech((SpeechSegment(kind="break", value=100),)))

    assert controller.spoken == []


def test_nvda_speech_output_cancel_only_when_available():
    class Controller:
        def __init__(self):
            self.cancel_count = 0

        def cancelSpeech(self) -> None:
            self.cancel_count += 1

    controller = Controller()
    NvdaControllerSpeechOutput(controller=controller).cancel()
    NvdaControllerSpeechOutput(controller=None).cancel()

    assert controller.cancel_count == 1
