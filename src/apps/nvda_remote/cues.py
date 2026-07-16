from __future__ import annotations

import logging
from pathlib import Path

from accessibility_toolkit.output import Capabilities
from accessibility_toolkit.output.speech import SpeechSequence


_logger = logging.getLogger(__name__)


class NvdaRemoteCues:
    def __init__(
        self,
        capabilities: Capabilities,
        *,
        cue_directory: Path | None = None,
    ) -> None:
        self._capabilities = capabilities
        self._cue_directory = cue_directory or Path(__file__).with_name("waves")

    def connected(self) -> None:
        self._play("connected.wav")

    def disconnected(self) -> None:
        self._play("disconnected.wav")
        self._speak("Disconnected")

    def controlling_remote(self) -> None:
        self._speak("Controlling remote computer")

    def controlling_local(self) -> None:
        self._speak("Controlling local computer")

    def _play(self, filename: str) -> None:
        wave = self._capabilities.wave
        if wave is None:
            return
        wave.play(str(self._cue_directory / filename))

    def _speak(self, message: str) -> None:
        try:
            self._capabilities.speech.speak(SpeechSequence(items=(message,)))
        except Exception:
            _logger.warning("Failed to speak NVDA Remote cue", exc_info=True)
