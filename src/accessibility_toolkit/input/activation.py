from collections.abc import Callable
import logging

from accessibility_toolkit.input.capture import HotkeyCapture, InputCapture

_logger = logging.getLogger(__name__)


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
            _logger.debug("InputActivation.enter_active skipped because mode is already active")
            return True
        hotkey_was_running = self._hotkey_capture.running
        _logger.debug(
            "InputActivation.enter_active begin input_running=%s hotkey_running=%s",
            self._input_capture.running,
            hotkey_was_running,
        )
        try:
            if not self._input_capture.running:
                self._input_capture.start()
                _logger.debug("InputActivation.enter_active input capture started")
                _logger.debug("InputActivation.enter_active input capture start returned")
        except Exception as error:
            _logger.debug(
                "InputActivation.enter_active input capture start failed: %s",
                error,
            )
            if hotkey_was_running and not self._hotkey_capture.running:
                try:
                    self._hotkey_capture.start()
                    _logger.debug(
                        "InputActivation.enter_active restored hotkey capture after failure"
                    )
                except Exception:
                    _logger.debug(
                        "InputActivation.enter_active failed to restore hotkey capture",
                        exc_info=True,
                    )
                    pass
            self._notify_error(str(error))
            return False
        if hotkey_was_running:
            _logger.debug(
                "InputActivation.enter_active stopping hotkey capture after handoff"
            )
            self._hotkey_capture.stop()
        self._set_active(True)
        _logger.debug("InputActivation.enter_active completed")
        return True

    def exit_active(self) -> bool:
        if not self._is_active():
            _logger.debug("InputActivation.exit_active skipped because mode is already inactive")
            return True
        _logger.debug(
            "InputActivation.exit_active begin input_running=%s hotkey_running=%s",
            self._input_capture.running,
            self._hotkey_capture.running,
        )
        try:
            if not self._hotkey_capture.running:
                self._hotkey_capture.start()
                _logger.debug("InputActivation.exit_active hotkey capture started")
        except Exception as error:
            _logger.debug(
                "InputActivation.exit_active hotkey capture start failed: %s",
                error,
            )
            try:
                if not self._input_capture.running:
                    self._input_capture.start()
                    _logger.debug(
                        "InputActivation.exit_active restored input capture after failure"
                    )
            except Exception:
                self._notify_error(str(error))
                return False
            self._notify_error(str(error))
            return False
        if self._input_capture.running:
            _logger.debug(
                "InputActivation.exit_active stopping input capture after handoff"
            )
            self._input_capture.stop()
            _logger.debug("InputActivation.exit_active input capture stop returned")
        self._set_active(False)
        _logger.debug("InputActivation.exit_active completed")
        return True
