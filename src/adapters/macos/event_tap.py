from collections.abc import Callable
from dataclasses import dataclass
import logging
import threading
from typing import Any

from application.input.results import AppKeyEventResult, KeyboardPipelineResult

_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RawMacKeyEvent:
    key_code: int
    pressed: bool
    is_repeat: bool


RawListener = Callable[[RawMacKeyEvent], KeyboardPipelineResult]
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
        _logger.debug(
            "MacOSEventTapManager.set_keyboard_listener active=%s hotkey_registered=%s",
            listener is not None,
            self._hotkey_handler is not None,
        )

    def set_hotkey_handler(self, handler: HotkeyHandler | None) -> None:
        self._hotkey_handler = handler
        _logger.debug(
            "MacOSEventTapManager.set_hotkey_handler active=%s keyboard_registered=%s",
            handler is not None,
            self._keyboard_listener is not None,
        )

    def _has_active_registrations(self) -> bool:
        return self._keyboard_listener is not None or self._hotkey_handler is not None

    def start(self) -> None:
        if self._running:
            _logger.debug("MacOSEventTapManager.start skipped because tap is already running")
            return
        _logger.debug(
            "MacOSEventTapManager.start begin keyboard_registered=%s hotkey_registered=%s",
            self._keyboard_listener is not None,
            self._hotkey_handler is not None,
        )
        if not self._permissions.is_trusted(prompt=False) and not self._permissions.is_trusted(
            prompt=True
        ):
            raise RuntimeError("macOS accessibility permission is required")
        if not self._permissions.has_listen_event_access(
            prompt=False
        ) and not self._permissions.has_listen_event_access(prompt=True):
            raise RuntimeError("macOS input monitoring permission is required")
        try:
            self._tap = self._backend.create_event_tap(self.handle_raw_event)
        except Exception:
            self._release_startup_resources()
            raise
        if self._start_thread:
            ready = threading.Event()
            self._backend.set_ready_event(ready)
            self._thread = threading.Thread(
                target=self._backend.attach_and_run,
                args=(self._tap,),
                name="macos-event-tap",
                daemon=True,
            )
            self._thread.start()
            if not ready.wait(timeout=30):
                self._thread = None
                self._backend.set_ready_event(None)
                self._release_startup_resources()
                raise RuntimeError(
                    "Event tap bootstrap timed out — the background thread did "
                    "not start within 30 seconds"
                )
            startup_error = self._backend.pop_startup_error()
            if startup_error is not None:
                self._thread = None
                self._backend.set_ready_event(None)
                self._backend.release_thread_source()
                self._release_startup_resources()
                raise RuntimeError(
                    "Event tap bootstrap failed"
                ) from startup_error
        else:
            self._source = self._backend.create_run_loop_source(self._tap)
            self._backend.add_source(self._source)
            self._backend.enable_tap(self._tap, True)
        self._running = True
        _logger.debug("MacOSEventTapManager.start completed")

    def stop(self) -> None:
        if not self._running:
            _logger.debug("MacOSEventTapManager.stop skipped because tap is not running")
            return
        if self._has_active_registrations():
            _logger.debug(
                "MacOSEventTapManager.stop skipped because registrations remain keyboard_registered=%s hotkey_registered=%s",
                self._keyboard_listener is not None,
                self._hotkey_handler is not None,
            )
            return
        _logger.debug("MacOSEventTapManager.stop begin")
        self._backend.run_loop_stop()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join()
        if self._source is not None:
            self._backend.release(self._source)
        if self._start_thread:
            self._backend.release_thread_source()
        if self._tap is not None:
            self._backend.release(self._tap)
        self._suppressed_keyups.clear()
        self._source = None
        self._tap = None
        self._thread = None
        self._running = False
        _logger.debug("MacOSEventTapManager.stop completed")

    def _release_startup_resources(self) -> None:
        if self._source is not None:
            self._backend.release(self._source)
            self._source = None
        if self._tap is not None:
            self._backend.release(self._tap)
            self._tap = None
        self._thread = None
        self._running = False

    def handle_raw_event(self, event: RawMacKeyEvent) -> KeyboardPipelineResult:
        if not event.pressed and event.key_code in self._suppressed_keyups:
            self._suppressed_keyups.discard(event.key_code)
            return KeyboardPipelineResult(send_to_system=False, app_result=AppKeyEventResult.HANDLED_STOP)
        if self._hotkey_handler is not None and self._hotkey_handler(event):
            if event.pressed:
                self._suppressed_keyups.add(event.key_code)
            return KeyboardPipelineResult(send_to_system=False, app_result=AppKeyEventResult.HANDLED_STOP)
        if self._keyboard_listener is None:
            return KeyboardPipelineResult(send_to_system=True, app_result=AppKeyEventResult.UNHANDLED)
        return self._keyboard_listener(event)

    def handle_tap_disabled(self) -> None:
        if self._tap is None:
            return
        self._backend.enable_tap(self._tap, True)


class QuartzEventTapBackend:
    def __init__(self, quartz: Any = None) -> None:
        if quartz is not None:
            self._Quartz = quartz
        else:
            try:
                import Quartz
                self._Quartz = Quartz
            except ImportError:
                self._Quartz = None
        self._run_loop: Any = None
        self._source: Any = None
        self._modifier_pressed: dict[int, bool] = {}
        self._ready: threading.Event | None = None
        self._startup_error: Exception | None = None

    def _require_quartz(self) -> Any:
        if self._Quartz is None:
            raise RuntimeError("Quartz/PyObjC is not available on this platform")
        return self._Quartz

    def _require_tap(self, tap: Any) -> Any:
        if tap is None:
            raise RuntimeError("Failed to create Quartz event tap")
        return tap

    def set_ready_event(self, ready: threading.Event | None) -> None:
        self._ready = ready

    def create_event_tap(self, callback: Callable[[RawMacKeyEvent], KeyboardPipelineResult]) -> Any:
        Q = self._require_quartz()

        _MODIFIER_KEY_CODES = frozenset({54, 55, 56, 57, 58, 59, 60, 61, 62})
        _CODE_TO_FLAG: dict[int, int] = {
            54: Q.kCGEventFlagMaskCommand,
            55: Q.kCGEventFlagMaskCommand,
            56: Q.kCGEventFlagMaskShift,
            57: Q.kCGEventFlagMaskAlphaShift,
            58: Q.kCGEventFlagMaskAlternate,
            59: Q.kCGEventFlagMaskControl,
            60: Q.kCGEventFlagMaskShift,
            61: Q.kCGEventFlagMaskAlternate,
            62: Q.kCGEventFlagMaskControl,
        }

        current_flags = Q.CGEventSourceFlagsState(Q.kCGEventSourceStateHIDSystemState)
        self._modifier_pressed.clear()
        for code in _MODIFIER_KEY_CODES:
            flag = _CODE_TO_FLAG.get(code)
            if flag is not None and (current_flags & flag):
                self._modifier_pressed[code] = True

        def cg_callback(proxy: Any, event_type: int, event: Any, refcon: Any) -> Any:
            key_code = int(Q.CGEventGetIntegerValueField(event, Q.kCGKeyboardEventKeycode))
            if event_type == Q.kCGEventFlagsChanged:
                if key_code not in _MODIFIER_KEY_CODES:
                    return event
                if key_code == 57:
                    flags = Q.CGEventGetFlags(event)
                    pressed = bool(flags & Q.kCGEventFlagMaskAlphaShift)
                else:
                    was_pressed = self._modifier_pressed.get(key_code, False)
                    pressed = not was_pressed
                self._modifier_pressed[key_code] = pressed
                raw = RawMacKeyEvent(key_code=key_code, pressed=pressed, is_repeat=False)
            elif event_type == Q.kCGEventKeyDown:
                auto_repeat = Q.CGEventGetIntegerValueField(event, Q.kCGKeyboardEventAutorepeat)
                raw = RawMacKeyEvent(key_code=key_code, pressed=True, is_repeat=auto_repeat != 0)
            elif event_type == Q.kCGEventKeyUp:
                raw = RawMacKeyEvent(key_code=key_code, pressed=False, is_repeat=False)
            else:
                return event
            result = callback(raw)
            if not result.send_to_system:
                return None
            return event

        mask = (
            Q.CGEventMaskBit(Q.kCGEventKeyDown)
            | Q.CGEventMaskBit(Q.kCGEventKeyUp)
            | Q.CGEventMaskBit(Q.kCGEventFlagsChanged)
        )
        tap = Q.CGEventTapCreate(
            Q.kCGSessionEventTap,
            Q.kCGHeadInsertEventTap,
            Q.kCGEventTapOptionDefault,
            mask,
            cg_callback,
            None,
        )
        return self._require_tap(tap)

    def attach_and_run(self, tap: Any) -> None:
        try:
            Q = self._require_quartz()
            self._run_loop = Q.CFRunLoopGetCurrent()
            try:
                self._source = Q.CFMachPortCreateRunLoopSource(None, tap, 0)
                Q.CFRunLoopAddSource(self._run_loop, self._source, Q.kCFRunLoopDefaultMode)
                Q.CGEventTapEnable(tap, True)
            except Exception as exc:
                self._startup_error = exc
                if self._source is not None:
                    Q.CFRelease(self._source)
                    self._source = None
                raise
        except Exception as exc:
            self._startup_error = exc
            if self._ready is not None:
                self._ready.set()
            return
        if self._ready is not None:
            self._ready.set()
        try:
            Q.CFRunLoopRun()
        finally:
            if self._source is not None:
                Q.CFRelease(self._source)
                self._source = None

    def pop_startup_error(self) -> Exception | None:
        exc = self._startup_error
        self._startup_error = None
        return exc

    def release_thread_source(self) -> None:
        if self._source is None:
            return
        Q = self._Quartz
        if Q is not None:
            Q.CFRelease(self._source)
        self._source = None

    def create_run_loop_source(self, tap: Any) -> Any:
        Q = self._require_quartz()
        return Q.CFMachPortCreateRunLoopSource(None, tap, 0)

    def add_source(self, source: Any) -> None:
        Q = self._require_quartz()
        Q.CFRunLoopAddSource(Q.CFRunLoopGetCurrent(), source, Q.kCFRunLoopDefaultMode)

    def enable_tap(self, tap: Any, enabled: bool) -> None:
        Q = self._require_quartz()
        Q.CGEventTapEnable(tap, enabled)

    def run_loop_run(self) -> None:
        Q = self._require_quartz()
        self._run_loop = Q.CFRunLoopGetCurrent()
        Q.CFRunLoopRun()

    def run_loop_stop(self) -> None:
        if self._run_loop is None:
            return
        Q = self._require_quartz()
        Q.CFRunLoopStop(self._run_loop)

    def release(self, obj: Any) -> None:
        Q = self._require_quartz()
        Q.CFRelease(obj)
