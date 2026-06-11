from collections.abc import Callable

from adapters.inputs.base import HotkeyCapture, InputCapture
from application.state import ConnectionState, ControlState, RuntimeState


class NvdaRemoteControlModeUseCase:
    def __init__(
        self,
        *,
        state: RuntimeState,
        input_capture: InputCapture,
        hotkey_capture: HotkeyCapture,
        notify_error: Callable[[str], None],
        notify_status: Callable[[dict[str, str]], None],
    ) -> None:
        self._state = state
        self._input_capture = input_capture
        self._hotkey_capture = hotkey_capture
        self._notify_error = notify_error
        self._notify_status = notify_status

    def start_control(self) -> None:
        if self._hotkey_capture.running:
            self._hotkey_capture.stop()
        try:
            if not self._input_capture.running:
                self._input_capture.start()
        except Exception as error:
            if self._state.connection_state != ConnectionState.IDLE:
                try:
                    if not self._hotkey_capture.running:
                        self._hotkey_capture.start()
                except Exception:
                    pass
            self._notify_error(str(error))
            return
        self._state.control_state = ControlState.CONTROLLING
        self._notify_status({"kind": "control", "state": ControlState.CONTROLLING.value})

    def stop_control(self) -> None:
        if self._input_capture.running:
            self._input_capture.stop()
        self._state.control_state = ControlState.SUSPENDED
        if self._state.connection_state != ConnectionState.IDLE and not self._hotkey_capture.running:
            try:
                self._hotkey_capture.start()
            except Exception as error:
                self._notify_error(str(error))
        self._notify_status({"kind": "control", "state": ControlState.SUSPENDED.value})
