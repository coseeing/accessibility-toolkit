from __future__ import annotations

import logging
import math
import os
import struct
import subprocess
import sys
import tempfile
import threading
import wave
from dataclasses import dataclass
from io import BytesIO
from typing import Protocol

SAMPLE_RATE = 44100
BITS_PER_SAMPLE = 16
CHANNELS = 2
MAX_AMPLITUDE = 32767
MAX_TONE_HZ = 20000
MAX_TONE_LENGTH_MS = 5000


class WavePlaybackBackend(Protocol):
    def play(self, wav_data: bytes) -> None: ...


@dataclass(frozen=True)
class BeepParameters:
    hz: float
    length: int
    left: int = 50
    right: int = 50


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def normalize_beep_parameters(
    hz: float,
    length: int,
    left: int = 50,
    right: int = 50,
) -> BeepParameters:
    clamped_hz = max(0.0, float(hz))
    if math.isfinite(clamped_hz):
        clamped_hz = min(clamped_hz, MAX_TONE_HZ)
    else:
        clamped_hz = 0.0
    if isinstance(length, float) and not math.isfinite(length):
        length = 0
    if isinstance(left, float) and not math.isfinite(left):
        left = 0
    if isinstance(right, float) and not math.isfinite(right):
        right = 0
    return BeepParameters(
        hz=clamped_hz,
        length=_clamp_int(int(length), 0, MAX_TONE_LENGTH_MS),
        left=_clamp_int(int(left), 0, 100),
        right=_clamp_int(int(right), 0, 100),
    )


def generate_beep_wav(params: BeepParameters) -> bytes:
    sample_count = int(SAMPLE_RATE * params.length / 1000)
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(BITS_PER_SAMPLE // 8)
        wav_file.setframerate(SAMPLE_RATE)
        for index in range(sample_count):
            phase = 2.0 * math.pi * params.hz * index / SAMPLE_RATE
            sample = int(math.sin(phase) * MAX_AMPLITUDE)
            left_sample = int(sample * params.left / 100)
            right_sample = int(sample * params.right / 100)
            wav_file.writeframesraw(struct.pack("<hh", left_sample, right_sample))
    return buffer.getvalue()


class DefaultWavePlaybackBackend:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(__name__)

    def play(self, wav_data: bytes) -> None:
        if sys.platform == "win32":
            self._play_windows(wav_data)
            return
        if sys.platform == "darwin":
            self._play_macos(wav_data)
            return
        self._logger.warning("Tone output is not supported on this platform")

    def _play_windows(self, wav_data: bytes) -> None:
        import winsound

        winsound.PlaySound(wav_data, winsound.SND_MEMORY)

    def _play_macos(self, wav_data: bytes) -> None:
        fd, path = tempfile.mkstemp(suffix=".wav")
        with os.fdopen(fd, "wb") as file:
            file.write(wav_data)
        process = subprocess.Popen(
            ["afplay", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        def cleanup() -> None:
            process.wait()
            try:
                os.remove(path)
            except OSError:
                self._logger.debug("Failed to remove temporary tone file", exc_info=True)

        threading.Thread(target=cleanup, daemon=True).start()


class DefaultToneOutput:
    def __init__(
        self,
        *,
        playback: WavePlaybackBackend | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._logger = logger or logging.getLogger(__name__)
        self._playback = playback or DefaultWavePlaybackBackend(logger=self._logger)

    @classmethod
    def load_default(cls) -> "DefaultToneOutput":
        return cls()

    def beep(
        self,
        hz: float,
        length: int,
        left: int = 50,
        right: int = 50,
    ) -> None:
        try:
            params = normalize_beep_parameters(hz, length, left, right)
        except (TypeError, ValueError, OverflowError):
            self._logger.warning(
                "Invalid tone parameters",
                extra={"hz": hz, "length": length, "left": left, "right": right},
            )
            return
        if params.hz <= 0 or params.length <= 0:
            return
        try:
            self._playback.play(generate_beep_wav(params))
        except Exception:
            self._logger.warning("Failed to play tone", exc_info=True)
