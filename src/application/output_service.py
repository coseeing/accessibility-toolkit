import logging
from enum import Enum
from typing import Protocol, runtime_checkable

from application.output_scheduler import OutputScheduler
from application.speech_service import SpeechService
from interop.speech.speech_sequence import SpeechSequence

_logger = logging.getLogger(__name__)


class OutputMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


@runtime_checkable
class SpeechOutputService(Protocol):
    def speak(self, sequence: SpeechSequence) -> None: ...
    def cancel(self) -> None: ...
    def pause(self, is_paused: bool) -> None: ...
    def get_backend_options(self) -> tuple[tuple[str, str], ...]: ...
    def get_selected_backend(self) -> str: ...
    def set_backend(self, backend_id: str) -> None: ...
    def list_voices(self) -> tuple[tuple[str, str], ...]: ...
    def get_voice(self) -> str | None: ...
    def set_voice(self, voice_id: str) -> None: ...
    def get_rate(self) -> int | None: ...
    def set_rate(self, value: int) -> None: ...
    def get_pitch(self) -> int | None: ...
    def set_pitch(self, value: int) -> None: ...
    def get_volume(self) -> int | None: ...
    def set_volume(self, value: int) -> None: ...
    def shutdown(self) -> None: ...


class QueuedOutputService:
    def __init__(self, *, speech: SpeechService) -> None:
        self._speech = speech
        self._mode = OutputMode.PARALLEL
        self._shared_scheduler = OutputScheduler()

    def set_mode(self, mode: OutputMode) -> None:
        self._mode = mode

    def get_mode(self) -> OutputMode:
        return self._mode

    def speak(self, sequence: SpeechSequence) -> None:
        _logger.debug(
            "QueuedOutputService.speak mode=%s items=%d",
            self._mode.value,
            len(sequence.items),
        )
        # SEQUENTIAL mode relies on speech.speak() being synchronous with
        # respect to enqueuing: it must finish adding all chunks/SSML into
        # the backend's own OutputScheduler before returning.  Both pyttsx3
        # and nvda_controller backends satisfy this contract because their
        # speak() implementations schedule into a local scheduler synchronously.
        if self._mode == OutputMode.SEQUENTIAL:
            self._shared_scheduler.schedule(self, lambda: self._speech.speak(sequence))
        else:
            self._speech.speak(sequence)

    def cancel(self) -> None:
        _logger.debug("QueuedOutputService.cancel mode=%s", self._mode.value)
        self._shared_scheduler.cancel_all()
        self._speech.cancel()

    def pause(self, is_paused: bool) -> None:
        self._speech.pause(is_paused)

    def get_backend_options(self) -> tuple[tuple[str, str], ...]:
        return self._speech.get_backend_options()

    def get_selected_backend(self) -> str:
        return self._speech.get_selected_backend()

    def set_backend(self, backend_id: str) -> None:
        self._speech.set_backend(backend_id)

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

    def shutdown(self) -> None:
        self.cancel()
        self._speech.shutdown()
        self._shared_scheduler.shutdown()
