import ctypes
import sys
from typing import Any

from remote_core.models.speech import NormalizedSpeech


NVDA_CONTROLLER_DLL = "nvdaControllerClient64.dll"


class NvdaControllerSpeechOutput:
    def __init__(self, controller: Any | None) -> None:
        self.controller = controller
        self.available = controller is not None

    @classmethod
    def load_default(
        cls,
        *,
        loader: Any | None = None,
        is_windows: bool | None = None,
    ) -> "NvdaControllerSpeechOutput":
        running_windows = sys.platform == "win32" if is_windows is None else is_windows
        if not running_windows:
            return cls(controller=None)
        if loader is None:
            loader = ctypes.WinDLL
        try:
            return cls(controller=loader(NVDA_CONTROLLER_DLL))
        except OSError:
            return cls(controller=None)

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
