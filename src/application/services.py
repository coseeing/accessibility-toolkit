from typing import Protocol

from adapters.outputs.interfaces import SpeechOutput, ToneOutput
from interop.speech.speech_sequence import SpeechSequence
from interop.protocol.messages import RemoteMessageType
from interop.protocol.transport.base import Transport


class ClipboardService(Protocol):
    def set_text(self, text: str) -> None: ...

    def get_text(self) -> str: ...


class OutputManager:
    def __init__(
        self,
        speech_output: SpeechOutput,
        clipboard: ClipboardService,
        tone_output: ToneOutput | None = None,
    ) -> None:
        self.speech_output = speech_output
        self.clipboard = clipboard
        self.tone_output = tone_output

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

    def handle_tone(
        self,
        hz: float,
        length: int,
        left: int = 50,
        right: int = 50,
    ) -> None:
        if self.tone_output is None:
            return
        self.tone_output.beep(hz, length, left, right)

    def handle_clipboard(self, text: str) -> None:
        self.clipboard.set_text(text)

    def push_clipboard(self, transport: Transport) -> None:
        transport.send(
            RemoteMessageType.SET_CLIPBOARD_TEXT,
            text=self.clipboard.get_text(),
        )
