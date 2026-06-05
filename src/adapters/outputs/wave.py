import logging
from adapters.outputs.interfaces import WaveOutput


class LoggingWaveOutput:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(__name__)

    def play(self, path: str) -> None:
        self._logger.info("wave output requested", extra={"path": path})
