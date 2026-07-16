from collections.abc import Callable

from apps.nvda_remote.state import ConnectionState, ControlState, RuntimeState
from apps.nvda_remote.events import RemoteConnectionChanged


class RemoteConnectionUseCase:
    def __init__(
        self,
        *,
        state: RuntimeState,
        exit_active,
        ensure_hotkey_started,
        stop_capture,
        stop_hotkey,
        notify,
        on_connected: Callable[[], None] = lambda: None,
        on_disconnected: Callable[[], None] = lambda: None,
    ) -> None:
        self._state = state
        self._exit_active = exit_active
        self._ensure_hotkey_started = ensure_hotkey_started
        self._stop_capture = stop_capture
        self._stop_hotkey = stop_hotkey
        self._notify = notify
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected

    def handle_connected(self) -> None:
        if self._state.connection_state == ConnectionState.CONNECTED:
            return
        self._state.connection_state = ConnectionState.CONNECTED
        if self._state.control_state != ControlState.CONTROLLING:
            self._state.control_state = ControlState.CONNECTED
            self._exit_active()
            self._ensure_hotkey_started()
        self._on_connected()
        self._notify(RemoteConnectionChanged("connected"))

    def handle_disconnected(self) -> None:
        if self._state.connection_state == ConnectionState.IDLE:
            return
        was_connected = self._state.connection_state == ConnectionState.CONNECTED
        self._stop_capture()
        self._stop_hotkey()
        self._state.connection_state = ConnectionState.IDLE
        self._state.control_state = ControlState.IDLE
        if was_connected:
            self._on_disconnected()
        self._notify(RemoteConnectionChanged("idle"))
