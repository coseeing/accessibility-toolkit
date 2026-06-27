import logging
from enum import Enum

from application.output.scheduler import Scheduler
from application.output.speech.service import SpeechService
from interop.speech.speech_sequence import SpeechSequence

_logger = logging.getLogger(__name__)


class Mode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


class QueuedService:
    def __init__(self, *, speech: SpeechService) -> None:
        self._speech = speech
        self._mode = Mode.PARALLEL
        self._shared_scheduler = Scheduler()

    def set_mode(self, mode: Mode) -> None:
        self._mode = mode

    def get_mode(self) -> Mode:
        return self._mode

    def speak(self, sequence: SpeechSequence) -> None:
        _logger.debug(
            "QueuedService.speak mode=%s items=%d",
            self._mode.value,
            len(sequence.items),
        )
        # SEQUENTIAL mode relies on speech.speak() being synchronous with
        # respect to enqueuing: it must finish adding all chunks/SSML into
        # the engine's own Scheduler before returning. Both pyttsx3
        # and nvda_controller engines satisfy this contract because their
        # speak() implementations schedule into a local scheduler synchronously.
        if self._mode == Mode.SEQUENTIAL:
            self._shared_scheduler.schedule(self, lambda: self._speech.speak(sequence))
        else:
            self._speech.speak(sequence)

    def cancel(self) -> None:
        _logger.debug("QueuedService.cancel mode=%s", self._mode.value)
        self._shared_scheduler.cancel_all()
        self._speech.cancel()

    def pause(self, is_paused: bool) -> None:
        self._speech.pause(is_paused)

    def get_engine_options(self) -> tuple[tuple[str, str], ...]:
        return self._speech.get_engine_options()

    def get_selected_engine(self) -> str:
        return self._speech.get_selected_engine()

    def set_engine(self, engine_id: str) -> None:
        self._speech.set_engine(engine_id)

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return self._speech.list_voices()

    def get_voice(self) -> str | None:
        return self._speech.get_voice()

    def set_voice(self, voice_id: str) -> None:
        self._speech.set_voice(voice_id)

    def get_rate(self) -> int | None:
        return self._speech.get_rate()

    def set_rate(self, value: int) -> None:
        self._speech.set_rate(value)

    def get_pitch(self) -> int | None:
        return self._speech.get_pitch()

    def set_pitch(self, value: int) -> None:
        self._speech.set_pitch(value)

    def get_volume(self) -> int | None:
        return self._speech.get_volume()

    def set_volume(self, value: int) -> None:
        self._speech.set_volume(value)

    def get_supported_numeric_settings(self):
        return self._speech.get_supported_numeric_settings()

    def shutdown(self) -> None:
        self.cancel()
        self._speech.shutdown()
        self._shared_scheduler.shutdown()
