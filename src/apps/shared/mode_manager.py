from collections.abc import Callable
from typing import Any

from adapters.inputs.base import KeyEventDecision
from interop.key.key_event import KeyEvent


class ModeManager:
    def __init__(
        self,
        *,
        activation,
        notify_status: Callable[[dict[str, Any]], None],
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
        self._notify_status(
            {"kind": "mode", "mode_id": mode_id, "state": "active"}
        )
        return True

    def exit_active_mode(self) -> KeyEventDecision:
        if self.active_mode_id is None:
            return KeyEventDecision.PASS_THROUGH
        mode = self._modes[self.active_mode_id]
        mode_id = mode.mode_id
        if not self._activation.exit_active():
            return KeyEventDecision.SUPPRESS
        mode.exit()
        self._notify_status(
            {"kind": "mode", "mode_id": mode_id, "state": "idle"}
        )
        self.active_mode_id = None
        return KeyEventDecision.SUPPRESS

    def handle_key_event(self, event: KeyEvent) -> KeyEventDecision:
        if self.active_mode_id is None:
            return KeyEventDecision.PASS_THROUGH
        mode = self._modes[self.active_mode_id]
        if event.pressed and event.vk == mode.exit_hotkey:
            return self.exit_active_mode()
        return mode.handle_key_event(event)
