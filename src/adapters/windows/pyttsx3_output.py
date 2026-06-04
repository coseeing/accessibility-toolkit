import logging
import threading
from typing import Any

from adapters.worldvoice_task.task_manager import TaskManager
from remote_core.models.speech_commands import (
    BreakCommand,
    PitchCommand,
    RateCommand,
    VolumeCommand,
)
from remote_core.models.speech_sequence import SpeechSequence


logger = logging.getLogger(__name__)


class Pyttsx3SpeechOutput:
    def __init__(
        self,
        engine: Any | None = None,
        *,
        engine_factory: Any | None = None,
        recreate_engine_per_utterance: bool = False,
        task_manager: TaskManager | None = None,
    ) -> None:
        self._engine = engine
        self._engine_factory = engine_factory
        self._recreate_engine_per_utterance = recreate_engine_per_utterance
        self._task_manager = task_manager or TaskManager()
        self._active_engine: Any | None = None
        self._lock = threading.Lock()
        self._voice_id: str | None = None
        self._rate = 100
        self._pitch = 0
        self._volume = 100

    @classmethod
    def load_default(
        cls,
        *,
        engine_factory: Any | None = None,
    ) -> "Pyttsx3SpeechOutput":
        if engine_factory is None:
            from pyttsx3.engine import Engine

            engine_factory = lambda: Engine(driverName=None, debug=False)
        logger.debug("Configured pyttsx3 speech engine factory")
        return cls(
            engine=None,
            engine_factory=engine_factory,
            recreate_engine_per_utterance=True,
        )

    def speak(self, sequence: SpeechSequence) -> None:
        logger.debug("pyttsx3 speak requested: items=%d", len(sequence.items))
        for item in sequence.items:
            if isinstance(item, str) and item:
                self._task_manager.add_speak_task(
                    self,
                    lambda text=item: self._speak_text(text),
                )
                continue
            if isinstance(item, BreakCommand):
                self._task_manager.add_break_task(self, item.time / 1000.0)
                continue
            if isinstance(item, PitchCommand):
                self._pitch = item.offset
                continue
            if isinstance(item, RateCommand):
                self._rate = int(item.multiplier * 100)
                continue
            if isinstance(item, VolumeCommand):
                self._volume = int(item.multiplier * 100)

    def cancel(self) -> None:
        self._task_manager.cancel()
        with self._lock:
            active_engine = self._active_engine
            if self._recreate_engine_per_utterance:
                self._engine = None
        if active_engine is not None:
            active_engine.stop()
        logger.debug("pyttsx3 stop requested")

    def pause(self, is_paused: bool) -> None:
        logger.debug("pyttsx3 pause requested: is_paused=%s", is_paused)
        return None

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        engine = self._acquire_engine()
        voices = getattr(engine, "getProperty", lambda _name: [])("voices")
        return tuple((voice.id, voice.name) for voice in voices)

    def get_voice(self) -> str | None:
        return self._voice_id

    def set_voice(self, voice_id: str) -> None:
        self._voice_id = voice_id

    def get_rate(self) -> int | None:
        return self._rate

    def set_rate(self, value: int) -> None:
        self._rate = value

    def get_pitch(self) -> int | None:
        return self._pitch

    def set_pitch(self, value: int) -> None:
        self._pitch = value

    def get_volume(self) -> int | None:
        return self._volume

    def set_volume(self, value: int) -> None:
        self._volume = value

    def _speak_text(self, text: str) -> None:
        engine = self._acquire_engine()
        with self._lock:
            self._active_engine = engine
        try:
            if self._voice_id is not None:
                engine.setProperty("voice", self._voice_id)
            engine.setProperty("rate", self._rate)
            engine.setProperty("volume", self._volume / 100.0)
            engine.say(text)
            engine.runAndWait()
        finally:
            with self._lock:
                if self._active_engine is engine:
                    self._active_engine = None
                if self._recreate_engine_per_utterance:
                    self._engine = None

    def _acquire_engine(self) -> Any:
        with self._lock:
            if self._engine is not None:
                return self._engine
            if self._engine_factory is None:
                raise RuntimeError("pyttsx3 engine is not configured")
            self._engine = self._engine_factory()
            logger.debug("Initialized pyttsx3 speech engine")
            return self._engine
