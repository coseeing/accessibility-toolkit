from typing import Protocol

from adapters.outputs.interfaces import SpeechOutput
from remote_core.models.speech_sequence import SpeechSequence
from remote_core.protocol import RemoteMessageType
from remote_core.transport.base import Transport


class ClipboardService(Protocol):
    def set_text(self, text: str) -> None: ...

    def get_text(self) -> str: ...


class OutputManager:
    def __init__(self, speech_output: SpeechOutput, clipboard: ClipboardService) -> None:
        self.speech_output = speech_output
        self.clipboard = clipboard

    def set_speech_output(
        self,
        speech_output: SpeechOutput,
        *,
        cancel_current: bool = True,
    ) -> None:
        if cancel_current:
            self.speech_output.cancel()
        self.speech_output = speech_output

    def handle_speech(self, speech: SpeechSequence) -> None:
        self.speech_output.speak(speech)

    def handle_cancel(self) -> None:
        self.speech_output.cancel()

    def handle_pause(self, is_paused: bool) -> None:
        self.speech_output.pause(is_paused)

    def handle_clipboard(self, text: str) -> None:
        self.clipboard.set_text(text)

    def push_clipboard(self, transport: Transport) -> None:
        transport.send(
            RemoteMessageType.SET_CLIPBOARD_TEXT,
            text=self.clipboard.get_text(),
        )
