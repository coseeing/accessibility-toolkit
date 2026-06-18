from collections.abc import Callable

from adapters.inputs.base import HotkeyCapture, InputCapture


class InputActivationUseCase:
    def __init__(
        self,
        *,
        input_capture: InputCapture,
        hotkey_capture: HotkeyCapture,
        is_active: Callable[[], bool],
        set_active: Callable[[bool], None],
        notify_error: Callable[[str], None],
    ) -> None:
        self._input_capture = input_capture
        self._hotkey_capture = hotkey_capture
        self._is_active = is_active
        self._set_active = set_active
        self._notify_error = notify_error

    def enter_active(self) -> bool:
        if self._is_active():
            return True
        hotkey_was_running = self._hotkey_capture.running
        try:
            if not self._input_capture.running:
                self._input_capture.start()
        except Exception as error:
            if hotkey_was_running and not self._hotkey_capture.running:
                try:
                    self._hotkey_capture.start()
                except Exception:
                    pass
            self._notify_error(str(error))
            return False
        if hotkey_was_running:
            self._hotkey_capture.stop()
        self._set_active(True)
        return True

    def exit_active(self) -> bool:
        if not self._is_active():
            return True
        try:
            if not self._hotkey_capture.running:
                self._hotkey_capture.start()
        except Exception as error:
            try:
                if not self._input_capture.running:
                    self._input_capture.start()
            except Exception:
                self._notify_error(str(error))
                return False
            self._notify_error(str(error))
            return False
        if self._input_capture.running:
            self._input_capture.stop()
        self._set_active(False)
        return True
