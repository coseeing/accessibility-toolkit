import logging
from adapters.outputs.interfaces import ToneOutput


class LoggingToneOutput:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(__name__)

    def beep(
        self,
        hz: int,
        length: int,
        left: int = 50,
        right: int = 50,
    ) -> None:
        self._logger.info(
            "tone output requested",
            extra={
                "hz": hz,
                "length": length,
                "left": left,
                "right": right,
            },
        )
