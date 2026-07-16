from __future__ import annotations

import logging
import subprocess
import sys
import threading
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

    def _play_macos(self, path: str) -> None:
        try:
            process = subprocess.Popen(
                ["afplay", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            self._logger.warning(
                "Failed to launch afplay",
                extra={"path": path},
                exc_info=True,
            )
            return
        threading.Thread(
            target=self._observe_macos_process,
            args=(process, path),
            daemon=True,
        ).start()

    def _observe_macos_process(self, process: subprocess.Popen, path: str) -> None:
        try:
            return_code = process.wait()
        except Exception:
            self._logger.warning(
                "Failed to observe afplay",
                extra={"path": path},
                exc_info=True,
            )
            return
        if return_code:
            self._logger.warning(
                "afplay exited with status %s",
                return_code,
                extra={"path": path},
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
