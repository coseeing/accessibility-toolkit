import logging
import threading
import time
from typing import Any

from application.output import Scheduler
from interop.speech.speech_commands import (
    BreakCommand,
    PitchCommand,
    RateCommand,
    VolumeCommand,
)
from interop.speech.speech_sequence import SpeechSequence


logger = logging.getLogger(__name__)

_RUN_AND_WAIT = "run_and_wait"
_EXTERNAL_LOOP = "external_loop"
_AUTO = "auto"


class Pyttsx3SpeechOutput:
    def __init__(
        self,
        engine: Any | None = None,
        *,
        engine_factory: Any | None = None,
        recreate_engine_per_utterance: bool = False,
        scheduler: Scheduler | None = None,
        task_manager: Scheduler | None = None,
    ) -> None:
        self._engine = engine
        self._engine_factory = engine_factory
        self._recreate_engine_per_utterance = recreate_engine_per_utterance
        self._scheduler = scheduler or task_manager or Scheduler()
        self._active_engine: Any | None = None
        self._lock = threading.Lock()
        self._cancel_requested = False
        self._utterance_counter = 0
        self._voice_id: str | None = None
        self._rate = 100
        self._pitch = 0
        self._volume = 100

    @classmethod
    def load_default(
        cls,
        *,
        engine_factory: Any | None = None,
        scheduler: Scheduler | None = None,
    ) -> "Pyttsx3SpeechOutput":
        if engine_factory is None:
            from pyttsx3.engine import Engine

            engine_factory = lambda: Engine(driverName=None, debug=False)
        logger.debug("Configured pyttsx3 speech engine factory")
        return cls(
            engine=None,
            engine_factory=engine_factory,
            recreate_engine_per_utterance=True,
            scheduler=scheduler,
        )

    def speak(self, sequence: SpeechSequence) -> None:
        logger.debug("pyttsx3 speak requested: items=%d", len(sequence.items))
        for item in sequence.items:
            if isinstance(item, str) and item:
                with self._lock:
                    self._utterance_counter += 1
                    utterance_id = self._utterance_counter
                logger.debug(
                    "pyttsx3 enqueue utterance utterance_id=%s text=%r",
                    utterance_id,
                    item,
                )
                self._scheduler.add_speak_task(
                    self,
                    lambda text=item, _utterance_id=utterance_id: self._speak_text(text, _utterance_id),
                )
                continue
            if isinstance(item, BreakCommand):
                self._scheduler.add_break_task(self, item.time / 1000.0)
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
        with self._lock:
            active_engine = self._active_engine
            cancel_requested = self._cancel_requested
        logger.debug(
            "pyttsx3 cancel requested active_engine=%s cancel_requested=%s",
            active_engine is not None,
            cancel_requested,
        )
        self._scheduler.cancel_all()
        with self._lock:
            self._cancel_requested = True
        logger.debug("pyttsx3 stop requested")

    def stop(self) -> None:
        with self._lock:
            active_engine = self._active_engine
        logger.debug(
            "pyttsx3 stop invoked on speech thread active_engine=%s",
            active_engine is not None,
        )
        if active_engine is not None:
            active_engine.stop()

    def pause(self, is_paused: bool) -> None:
        logger.debug("pyttsx3 pause requested: is_paused=%s", is_paused)
        return None

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        engine = self._acquire_engine()
        try:
            voices = getattr(engine, "getProperty", lambda _name: [])("voices")
        except Exception as error:
            fallback_voices = self._list_voices_from_engine_fallback(engine)
            if fallback_voices:
                logger.debug(
                    "pyttsx3 voice enumeration fell back to raw SAPI tokens: %s",
                    error,
                )
                return fallback_voices
            logger.warning(
                "pyttsx3 voice enumeration failed and no fallback voices were available: %s",
                error,
            )
            return ()
        available: list[tuple[str, str]] = []
        for voice in voices:
            voice_id = getattr(voice, "id", None)
            voice_name = getattr(voice, "name", None)
            if not isinstance(voice_id, str) or not voice_id:
                continue
            if not isinstance(voice_name, str) or not voice_name:
                voice_name = voice_id
            available.append((voice_id, voice_name))
        return tuple(available)

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

    def _speak_text(self, text: str, utterance_id: int) -> None:
        engine = self._acquire_engine()
        with self._lock:
            self._active_engine = engine
            self._cancel_requested = False
        logger.debug(
            "pyttsx3 utterance begin utterance_id=%s text=%r engine_id=%s",
            utterance_id,
            text,
            id(engine),
        )
        try:
            if self._voice_id is not None:
                engine.setProperty("voice", self._voice_id)
            engine.setProperty("rate", self._rate)
            try:
                engine.setProperty("pitch", self._pitch)
            except Exception:
                logger.debug("pyttsx3 engine does not support pitch property")
            engine.setProperty("volume", self._volume / 100.0)
            engine.say(text)
            logger.debug(
                "pyttsx3 utterance submitted utterance_id=%s engine_id=%s",
                utterance_id,
                id(engine),
            )
            self._run_until_done(engine, utterance_id)
        finally:
            with self._lock:
                if self._active_engine is engine:
                    self._active_engine = None
                if self._recreate_engine_per_utterance:
                    self._engine = None
            logger.debug(
                "pyttsx3 utterance end utterance_id=%s engine_id=%s",
                utterance_id,
                id(engine),
            )
            self._scheduler.notify_done()

    def _acquire_engine(self) -> Any:
        with self._lock:
            if self._engine is not None:
                return self._engine
            if self._engine_factory is None:
                raise RuntimeError("pyttsx3 engine is not configured")
            self._engine = self._engine_factory()
            logger.debug("Initialized pyttsx3 speech engine")
            return self._engine

    def _run_until_done(self, engine: Any, utterance_id: int) -> None:
        execution_strategy = self._driver_execution_strategy(engine)
        start_loop = getattr(engine, "startLoop", None)
        iterate = getattr(engine, "iterate", None)
        is_busy = getattr(engine, "isBusy", None)
        end_loop = getattr(engine, "endLoop", None)
        if (
            execution_strategy == _RUN_AND_WAIT
            or (
                execution_strategy == _AUTO
                and (
                    not callable(start_loop)
                    or not callable(iterate)
                    or not callable(is_busy)
                    or not callable(end_loop)
                )
            )
        ):
            logger.debug(
                "pyttsx3 utterance runAndWait path utterance_id=%s engine_id=%s",
                utterance_id,
                id(engine),
            )
            engine.runAndWait()
            return

        logger.debug(
            "pyttsx3 utterance external loop begin utterance_id=%s engine_id=%s",
            utterance_id,
            id(engine),
        )
        start_loop(False)
        try:
            while True:
                with self._lock:
                    cancel_requested = self._cancel_requested
                if cancel_requested:
                    logger.debug(
                        "pyttsx3 utterance stop during loop utterance_id=%s engine_id=%s",
                        utterance_id,
                        id(engine),
                    )
                    engine.stop()
                iterate()
                if not is_busy():
                    logger.debug(
                        "pyttsx3 utterance external loop not busy utterance_id=%s engine_id=%s",
                        utterance_id,
                        id(engine),
                    )
                    break
                time.sleep(0.001)
        finally:
            end_loop()
            logger.debug(
                "pyttsx3 utterance external loop end utterance_id=%s engine_id=%s",
                utterance_id,
                id(engine),
            )

    @staticmethod
    def _driver_execution_strategy(engine: Any) -> str:
        driver_name = getattr(engine, "driver_name", None)
        if isinstance(driver_name, str):
            normalized_driver_name = driver_name.lower()
            if normalized_driver_name == "nsss":
                return _EXTERNAL_LOOP
            if normalized_driver_name == "sapi5":
                return _RUN_AND_WAIT

        proxy = getattr(engine, "proxy", None)
        module = getattr(proxy, "_module", None)
        module_name = getattr(module, "__name__", None)
        if isinstance(module_name, str):
            if module_name.endswith(".nsss"):
                return _EXTERNAL_LOOP
            if module_name.endswith(".sapi5"):
                return _RUN_AND_WAIT

        return _AUTO

    @staticmethod
    def _list_voices_from_engine_fallback(engine: Any) -> tuple[tuple[str, str], ...]:
        try:
            proxy = getattr(engine, "proxy", None)
            driver = getattr(proxy, "_driver", None)
            tts = getattr(driver, "_tts", None)
            get_voices = getattr(tts, "GetVoices", None)
            if get_voices is None:
                return ()
            available: list[tuple[str, str]] = []
            for token in get_voices():
                voice_id = getattr(token, "Id", None)
                if not isinstance(voice_id, str) or not voice_id:
                    continue
                try:
                    voice_name = token.GetDescription()
                except Exception:
                    voice_name = voice_id
                if not isinstance(voice_name, str) or not voice_name:
                    voice_name = voice_id
                available.append((voice_id, voice_name))
            return tuple(available)
        except Exception:
            logger.debug("pyttsx3 fallback voice enumeration failed", exc_info=True)
            return ()
