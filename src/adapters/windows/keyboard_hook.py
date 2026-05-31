from collections.abc import Callable

from remote_core.models.keys import KeyEvent


class WindowsKeyboardCapture:
    def __init__(self):
        self._listener: Callable[[KeyEvent], None] | None = None
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def set_listener(self, listener: Callable[[KeyEvent], None]) -> None:
        self._listener = listener

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    # Replace _emit_for_tests with LowLevelKeyboardProc-backed callbacks once the
    # Windows hook integration is verified manually in Task 8.
    def _emit_for_tests(
        self, vk: int, scan: int | None, extended: bool, pressed: bool
    ) -> None:
        if self._listener is None:
            return
        self._listener(KeyEvent(vk=vk, scan=scan, extended=extended, pressed=pressed))
