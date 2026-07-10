from dataclasses import dataclass
from enum import StrEnum


class AppKeyEventResult(StrEnum):
    UNHANDLED = "unhandled"
    HANDLED_CONTINUE = "handled_continue"
    HANDLED_STOP = "handled_stop"


@dataclass(frozen=True)
class KeyboardPipelineResult:
    send_to_system: bool
    app_result: AppKeyEventResult
