from __future__ import annotations

import logging
import subprocess
import sys
from typing import Protocol


class WavePlaybackBackend(Protocol):
    def play(self, path: str) -> None: ...


class DefaultWavePlaybackBackend:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(__name__)

    def play(self, path: str) -> None:
        if sys.platform == "win32":
            self._play_windows(path)
            return
        if sys.platform == "darwin":
            self._play_macos(path)
            return
        self._logger.warning("Wave output is not supported on this platform")

    @staticmethod
    def _play_windows(path: str) -> None:
        import winsound

        winsound.PlaySound(
            path,
            winsound.SND_FILENAME
            | winsound.SND_ASYNC
            | winsound.SND_NODEFAULT,
        )

    @staticmethod
    def _play_macos(path: str) -> None:
        subprocess.Popen(
            ["afplay", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


class DefaultWaveOutput:
    def __init__(
        self,
        *,
        playback: WavePlaybackBackend | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._logger = logger or logging.getLogger(__name__)
        self._playback = playback or DefaultWavePlaybackBackend(logger=self._logger)

    @classmethod
    def load_default(cls) -> "DefaultWaveOutput":
        return cls()

    def play(self, path: str) -> None:
        try:
            self._playback.play(path)
        except Exception:
            self._logger.warning(
                "Failed to play wave file",
                extra={"path": path},
                exc_info=True,
            )


class LoggingWaveOutput:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(__name__)

    def play(self, path: str) -> None:
        self._logger.info("wave output requested", extra={"path": path})
