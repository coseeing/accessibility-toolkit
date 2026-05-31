from typing import Any

from remote_core.models.speech import NormalizedSpeech


class NvdaControllerSpeechOutput:
    def __init__(self, controller: Any | None) -> None:
        self.controller = controller
        self.available = controller is not None

    def speak(self, speech: NormalizedSpeech) -> None:
        if not self.available:
            return
        text = " ".join(
            str(segment.value)
            for segment in speech.segments
            if segment.kind == "text" and segment.value
        )
        if text:
            self.controller.speakText(text)

    def cancel(self) -> None:
        if self.available:
            self.controller.cancelSpeech()

    def pause(self, is_paused: bool) -> None:
        return None
