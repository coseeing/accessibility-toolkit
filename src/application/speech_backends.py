from dataclasses import dataclass
from typing import Callable

from adapters.outputs.interfaces import SpeechOutput


@dataclass(frozen=True)
class SpeechBackendOption:
    backend_id: str
    label: str
    factory: Callable[[], SpeechOutput]


class SpeechBackendManager:
    def __init__(
        self,
        *,
        backend_options: tuple[SpeechBackendOption, ...],
        selected_backend_id: str,
    ) -> None:
        if not backend_options:
            raise ValueError("At least one speech backend is required")
        self._options = backend_options
        self._options_by_id = {option.backend_id: option for option in backend_options}
        if selected_backend_id not in self._options_by_id:
            raise ValueError(f"Unknown speech backend: {selected_backend_id}")
        self._selected_backend_id = selected_backend_id
        self._current_output = self._create_output(selected_backend_id)

    @property
    def current_output(self) -> SpeechOutput:
        return self._current_output

    @property
    def selected_backend_id(self) -> str:
        return self._selected_backend_id

    def backend_choices(self) -> tuple[tuple[str, str], ...]:
        return tuple((option.backend_id, option.label) for option in self._options)

    def set_backend(self, backend_id: str) -> SpeechOutput:
        if backend_id not in self._options_by_id:
            raise ValueError(f"Unknown speech backend: {backend_id}")
        if backend_id == self._selected_backend_id:
            return self._current_output
        self._current_output.cancel()
        self._current_output = self._create_output(backend_id)
        self._selected_backend_id = backend_id
        return self._current_output

    def _create_output(self, backend_id: str) -> SpeechOutput:
        return self._options_by_id[backend_id].factory()
