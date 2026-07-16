from collections.abc import Callable

from apps.nvda_remote.state import ControlState, RuntimeState
from apps.nvda_remote.events import RemoteControlChanged


class NvdaRemoteControlModeUseCase:
    def __init__(
        self,
        *,
        state: RuntimeState,
        notify_error: Callable[[str], None],
        notify_status: Callable[[RemoteControlChanged], None],
        on_started: Callable[[], None] = lambda: None,
        on_stopped: Callable[[], None] = lambda: None,
    ) -> None:
        self._state = state
        self._notify_error = notify_error
        self._notify_status = notify_status
        self._on_started = on_started
        self._on_stopped = on_stopped

    def start_control(self) -> None:
        if self._state.control_state != ControlState.CONNECTED:
            return
        self._state.control_state = ControlState.CONTROLLING
        self._on_started()
        self._notify_status(RemoteControlChanged(ControlState.CONTROLLING.value))

    def stop_control(self) -> None:
        if self._state.control_state != ControlState.CONTROLLING:
            return
        self._state.control_state = ControlState.CONNECTED
        self._on_stopped()
        self._notify_status(RemoteControlChanged(ControlState.CONNECTED.value))
