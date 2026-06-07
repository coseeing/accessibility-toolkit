from collections.abc import Callable
from dataclasses import dataclass
import threading
from typing import Any

from adapters.inputs.base import KeyEventDecision


@dataclass(frozen=True, slots=True)
class RawMacKeyEvent:
    key_code: int
    pressed: bool
    is_repeat: bool


RawListener = Callable[[RawMacKeyEvent], KeyEventDecision]
HotkeyHandler = Callable[[RawMacKeyEvent], bool]


class MacOSEventTapManager:
    def __init__(
        self,
        *,
        permissions: Any,
        backend: Any,
        start_thread: bool = True,
    ) -> None:
        self._permissions = permissions
        self._backend = backend
        self._start_thread = start_thread
        self._keyboard_listener: RawListener | None = None
        self._hotkey_handler: HotkeyHandler | None = None
        self._running = False
        self._tap: Any | None = None
        self._source: Any | None = None
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._running

    def set_keyboard_listener(self, listener: RawListener | None) -> None:
        self._keyboard_listener = listener

    def set_hotkey_handler(self, handler: HotkeyHandler | None) -> None:
        self._hotkey_handler = handler

    def start(self) -> None:
        if self._running:
            return
        if not self._permissions.is_trusted(prompt=False):
            raise RuntimeError("macOS accessibility permission is required")
        self._tap = self._backend.create_event_tap(self.handle_raw_event)
        self._source = self._backend.create_run_loop_source(self._tap)
        self._backend.add_source(self._source)
        self._backend.enable_tap(self._tap, True)
        self._running = True
        if self._start_thread:
            self._thread = threading.Thread(
                target=self._backend.run_loop_run,
                name="macos-event-tap",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        if not self._running:
            return
        self._backend.run_loop_stop()
        if self._thread is not None:
            self._thread.join()
        if self._source is not None:
            self._backend.release(self._source)
        if self._tap is not None:
            self._backend.release(self._tap)
        self._source = None
        self._tap = None
        self._thread = None
        self._running = False

    def handle_raw_event(self, event: RawMacKeyEvent) -> KeyEventDecision:
        if self._hotkey_handler is not None and self._hotkey_handler(event):
            return KeyEventDecision.SUPPRESS
        if self._keyboard_listener is None:
            return KeyEventDecision.PASS_THROUGH
        return self._keyboard_listener(event)
