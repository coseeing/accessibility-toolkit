from typing import Protocol

from application.input.results import AppKeyEventResult
from interop.key.key_event import KeyEvent


class ActivationMode(Protocol):
    mode_id: str
    enter_usage: int
    exit_usage: int

    def can_enter(self) -> bool: ...
    def enter(self) -> bool: ...
    def exit(self) -> bool: ...
    def handle_key_event(self, event: KeyEvent) -> AppKeyEventResult: ...
