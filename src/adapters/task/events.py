from dataclasses import dataclass, field
from typing import Callable


@dataclass(slots=True)
class SpeechEventCallbacks:
    on_index_reached: Callable[[int | None], None] = field(
        default=lambda index: None
    )
    on_done_speaking: Callable[[], None] = field(default=lambda: None)
