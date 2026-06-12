from typing import Protocol

from adapters.inputs.base import KeyEventDecision
from interop.key.key_event import KeyEvent


class ActivationMode(Protocol):
    mode_id: str
    enter_hotkey: object
    exit_hotkey: int

    def can_enter(self) -> bool: ...
    def enter(self) -> bool: ...
    def exit(self) -> bool: ...
    def handle_key_event(self, event: KeyEvent) -> KeyEventDecision: ...
