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


class QuartzEventTapBackend:
    def create_event_tap(self, callback: Callable[[RawMacKeyEvent], KeyEventDecision]) -> Any:
        raise NotImplementedError

    def create_run_loop_source(self, tap: Any) -> Any:
        raise NotImplementedError

    def add_source(self, source: Any) -> None:
        raise NotImplementedError

    def enable_tap(self, tap: Any, enabled: bool) -> None:
        raise NotImplementedError

    def run_loop_run(self) -> None:
        raise NotImplementedError

    def run_loop_stop(self) -> None:
        raise NotImplementedError

    def release(self, value: Any) -> None:
        raise NotImplementedError


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
        self._suppressed_keyups: set[int] = set()
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

    def _has_active_registrations(self) -> bool:
        return self._keyboard_listener is not None or self._hotkey_handler is not None

    def start(self) -> None:
        if self._running:
            return
        if not self._permissions.is_trusted(prompt=False):
            raise RuntimeError("macOS accessibility permission is required")
        if not self._permissions.has_listen_event_access(prompt=False):
            raise RuntimeError("macOS input monitoring permission is required")
        try:
            self._tap = self._backend.create_event_tap(self.handle_raw_event)
            self._source = self._backend.create_run_loop_source(self._tap)
            self._backend.add_source(self._source)
            self._backend.enable_tap(self._tap, True)
        except Exception:
            self._release_startup_resources()
            raise
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
        if self._has_active_registrations():
            return
        self._backend.run_loop_stop()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join()
        if self._source is not None:
            self._backend.release(self._source)
        if self._tap is not None:
            self._backend.release(self._tap)
        self._suppressed_keyups.clear()
        self._source = None
        self._tap = None
        self._thread = None
        self._running = False

    def _release_startup_resources(self) -> None:
        if self._source is not None:
            self._backend.release(self._source)
            self._source = None
        if self._tap is not None:
            self._backend.release(self._tap)
            self._tap = None
        self._thread = None
        self._running = False

    def handle_raw_event(self, event: RawMacKeyEvent) -> KeyEventDecision:
        if not event.pressed and event.key_code in self._suppressed_keyups:
            self._suppressed_keyups.discard(event.key_code)
            return KeyEventDecision.SUPPRESS
        if self._hotkey_handler is not None and self._hotkey_handler(event):
            if event.pressed:
                self._suppressed_keyups.add(event.key_code)
            return KeyEventDecision.SUPPRESS
        if self._keyboard_listener is None:
            return KeyEventDecision.PASS_THROUGH
        return self._keyboard_listener(event)

    def handle_tap_disabled(self) -> None:
        if self._tap is None:
            return
        self._backend.enable_tap(self._tap, True)
