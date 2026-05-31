from typing import Protocol

from adapters.outputs.speech import SpeechOutput
from remote_core.models.speech import NormalizedSpeech
from remote_core.protocol import RemoteMessageType
from remote_core.transport.base import Transport


class ClipboardService(Protocol):
    def set_text(self, text: str) -> None: ...

    def get_text(self) -> str: ...


class OutputManager:
    def __init__(self, speech_output: SpeechOutput, clipboard: ClipboardService) -> None:
        self.speech_output = speech_output
        self.clipboard = clipboard

    def handle_speech(self, speech: NormalizedSpeech) -> None:
        self.speech_output.speak(speech)

    def handle_clipboard(self, text: str) -> None:
        self.clipboard.set_text(text)

    def push_clipboard(self, transport: Transport) -> None:
        transport.send(
            RemoteMessageType.SET_CLIPBOARD_TEXT,
            text=self.clipboard.get_text(),
        )
