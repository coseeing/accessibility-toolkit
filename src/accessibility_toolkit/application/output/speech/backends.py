from dataclasses import dataclass
from typing import Callable

from accessibility_toolkit.adapters.outputs.interfaces import SpeechOutput


@dataclass(frozen=True)
class SpeechEngineOption:
    engine_id: str
    label: str
    factory: Callable[[], SpeechOutput]


class SpeechEngineManager:
    def __init__(
        self,
        *,
        engine_options: tuple[SpeechEngineOption, ...],
        selected_engine_id: str,
    ) -> None:
        if not engine_options:
            raise ValueError("At least one speech engine is required")
        self._options = engine_options
        self._options_by_id = {option.engine_id: option for option in engine_options}
        if selected_engine_id not in self._options_by_id:
            raise ValueError(f"Unknown speech engine: {selected_engine_id}")
        self._selected_engine_id = selected_engine_id
        self._current_output = self._create_output(selected_engine_id)

    @property
    def current_output(self) -> SpeechOutput:
        return self._current_output

    @property
    def selected_engine_id(self) -> str:
        return self._selected_engine_id

    def engine_choices(self) -> tuple[tuple[str, str], ...]:
        return tuple((option.engine_id, option.label) for option in self._options)

    def set_engine(self, engine_id: str) -> SpeechOutput:
        if engine_id not in self._options_by_id:
            raise ValueError(f"Unknown speech engine: {engine_id}")
        if engine_id == self._selected_engine_id:
            return self._current_output
        # Build the new engine first so that a factory failure leaves the
        # currently active engine intact and reported as selected. This keeps
        # the contract from spec "Error Handling": on a failed engine switch the
        # previous engine stays active and the UI can restore its selection.
        new_output = self._create_output(engine_id)
        previous_output = self._current_output
        previous_output.cancel()
        self._current_output = new_output
        self._selected_engine_id = engine_id
        return self._current_output

    def _create_output(self, engine_id: str) -> SpeechOutput:
        return self._options_by_id[engine_id].factory()
