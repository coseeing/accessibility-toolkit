from collections.abc import Callable

from application.state import ControlState, RuntimeState
from apps.nvda_remote.events import RemoteControlChanged


class NvdaRemoteControlModeUseCase:
    def __init__(
        self,
        *,
        state: RuntimeState,
        notify_error: Callable[[str], None],
        notify_status: Callable[[RemoteControlChanged], None],
    ) -> None:
        self._state = state
        self._notify_error = notify_error
        self._notify_status = notify_status

    def start_control(self) -> None:
        self._state.control_state = ControlState.CONTROLLING
        self._notify_status(RemoteControlChanged(ControlState.CONTROLLING.value))

    def stop_control(self) -> None:
        self._state.control_state = ControlState.CONNECTED
        self._notify_status(RemoteControlChanged(ControlState.CONNECTED.value))
