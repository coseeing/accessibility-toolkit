from typing import TYPE_CHECKING

from adapters.outputs.interfaces import SpeechOutput
from application.output.speech.backends import (
    SpeechBackendOption,
    SpeechEngineManager,
    SpeechEngineOption,
)
from application.output.speech.settings import SpeechNumericSetting
from interop.speech.speech_sequence import SpeechSequence

if TYPE_CHECKING:
    from application.output.scheduler import Scheduler


class SpeechService:
    def __init__(
        self,
        *,
        engine_options: tuple[SpeechEngineOption, ...] | None = None,
        selected_engine_id: str | None = None,
        backend_options: tuple[SpeechBackendOption, ...] | None = None,
        selected_backend_id: str | None = None,
        scheduler: "Scheduler | None" = None,
    ) -> None:
        resolved_engine_options = (
            engine_options if engine_options is not None else backend_options
        )
        resolved_selected_engine_id = (
            selected_engine_id
            if selected_engine_id is not None
            else selected_backend_id
        )
        if resolved_engine_options is None:
            raise ValueError("speech engine options are required")
        if resolved_selected_engine_id is None:
            raise ValueError("selected speech engine id is required")
        self._engine_manager = SpeechEngineManager(
            engine_options=resolved_engine_options,
            selected_engine_id=resolved_selected_engine_id,
        )
        self._scheduler = scheduler

    @classmethod
    def single_backend(cls, output: SpeechOutput) -> "SpeechService":
        return cls(
            engine_options=(
                SpeechEngineOption(
                    engine_id="default",
                    label="Default",
                    factory=lambda: output,
                ),
            ),
            selected_engine_id="default",
        )

    def speak(self, sequence: SpeechSequence) -> None:
        self._engine_manager.current_output.speak(sequence)

    def cancel(self) -> None:
        self._engine_manager.current_output.cancel()

    def pause(self, is_paused: bool) -> None:
        self._engine_manager.current_output.pause(is_paused)

    def get_engine_options(self) -> tuple[tuple[str, str], ...]:
        return self._engine_manager.engine_choices()

    def get_selected_engine(self) -> str:
        return self._engine_manager.selected_engine_id

    def set_engine(self, engine_id: str) -> None:
        self._engine_manager.set_engine(engine_id)

    def get_backend_options(self) -> tuple[tuple[str, str], ...]:
        return self._engine_manager.backend_choices()

    def get_selected_backend(self) -> str:
        return self._engine_manager.selected_backend_id

    def set_backend(self, backend_id: str) -> None:
        self._engine_manager.set_backend(backend_id)

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return self._engine_manager.current_output.list_voices()

    def get_voice(self) -> str | None:
        return self._engine_manager.current_output.get_voice()

    def set_voice(self, voice_id: str) -> None:
        self._engine_manager.current_output.set_voice(voice_id)

    def get_rate(self) -> int | None:
        return self._engine_manager.current_output.get_rate()

    def set_rate(self, value: int) -> None:
        self._engine_manager.current_output.set_rate(value)

    def get_pitch(self) -> int | None:
        return self._engine_manager.current_output.get_pitch()

    def set_pitch(self, value: int) -> None:
        self._engine_manager.current_output.set_pitch(value)

    def get_volume(self) -> int | None:
        return self._engine_manager.current_output.get_volume()

    def set_volume(self, value: int) -> None:
        self._engine_manager.current_output.set_volume(value)

    def get_supported_numeric_settings(self) -> tuple[SpeechNumericSetting, ...]:
        return self._engine_manager.current_output.get_supported_numeric_settings()

    def shutdown(self) -> None:
        self.cancel()
        if self._scheduler is not None:
            self._scheduler.shutdown()
