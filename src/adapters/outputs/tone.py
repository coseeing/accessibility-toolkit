import logging
from typing import Protocol


class ToneOutput(Protocol):
    def play(self, frequency: int, duration_ms: int) -> None: ...


class LoggingToneOutput:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(__name__)

    def play(self, frequency: int, duration_ms: int) -> None:
        self._logger.info(
            "tone output requested",
            extra={
                "frequency": frequency,
                "duration_ms": duration_ms,
            },
        )
