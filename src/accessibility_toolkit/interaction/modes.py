from collections.abc import Callable
from typing import Any, Protocol

from accessibility_toolkit.events import ModeChanged
from accessibility_toolkit.input import AppKeyEventResult
from accessibility_toolkit.input.events import KeyEvent


class ActivationMode(Protocol):
    mode_id: str
    enter_usage: int
    exit_usage: int

    def can_enter(self) -> bool: ...
    def enter(self) -> bool: ...
    def exit(self) -> bool: ...
    def handle_key_event(self, event: KeyEvent) -> AppKeyEventResult: ...


class ModeManager:
    def __init__(
        self,
        *,
        activation,
        notify_status: Callable[[ModeChanged], None],
    ) -> None:
        self._activation = activation
        self._notify_status = notify_status
        self._modes: dict[str, Any] = {}
        self.active_mode_id: str | None = None

    def register(self, mode) -> None:
        self._modes[mode.mode_id] = mode

    def activate_mode(self, mode_id: str) -> bool:
        if self.active_mode_id is not None:
            return False
        mode = self._modes.get(mode_id)
        if mode is None:
            return False
        if not mode.can_enter():
            return False
        if not self._activation.enter_active():
            return False
        if not mode.enter():
            self._activation.exit_active()
            return False
        self.active_mode_id = mode_id
        self._notify_status(ModeChanged(mode_id, active=True))
        return True

    def exit_active_mode(self) -> AppKeyEventResult:
        if self.active_mode_id is None:
            return AppKeyEventResult.UNHANDLED
        mode = self._modes[self.active_mode_id]
        mode_id = mode.mode_id
        if not self._activation.exit_active():
            return AppKeyEventResult.HANDLED_STOP
        mode.exit()
        self._notify_status(ModeChanged(mode_id, active=False))
        self.active_mode_id = None
        return AppKeyEventResult.HANDLED_STOP

    def handle_key_event(self, event: KeyEvent) -> AppKeyEventResult:
        if self.active_mode_id is None:
            return AppKeyEventResult.UNHANDLED
        mode = self._modes[self.active_mode_id]
        if event.pressed and event.usage == mode.exit_usage:
            return self.exit_active_mode()
        return mode.handle_key_event(event)
