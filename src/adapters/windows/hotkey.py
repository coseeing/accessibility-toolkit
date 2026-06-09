import ctypes
import sys
import threading
from ctypes import wintypes
from typing import Any


WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
F11_VK = 0x7A
HOTKEY_ID = 1


class WindowsHotkeyCapture:
    def __init__(
        self,
        *,
        user32: Any | None = None,
        kernel32: Any | None = None,
        is_windows: bool | None = None,
        vk: int = F11_VK,
    ) -> None:
        self._handler = None
        self._running = False
        self._is_windows = sys.platform == "win32" if is_windows is None else is_windows
        self._user32 = user32
        self._kernel32 = kernel32
        self._thread: threading.Thread | None = None
        self._ready: threading.Event | None = None
        self._thread_id: int | None = None
        self._vk = vk

    @property
    def running(self) -> bool:
        return self._running

    def set_handler(self, handler) -> None:
        self._handler = handler

    def start(self) -> None:
        if self._running:
            return
        self._ensure_backend()
        ready = threading.Event()
        self._ready = ready
        self._thread = threading.Thread(target=self._message_loop, daemon=True)
        self._thread.start()
        ready.wait()
        if not self._running:
            raise RuntimeError(
                "Failed to register F11 hotkey — may already be in use by another app"
            )

    def stop(self) -> None:
        if not self._running:
            return
        if self._thread_id is not None and self._user32 is not None:
            self._user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=1)
        self._thread = None
        self._thread_id = None
        self._ready = None
        self._running = False

    def _ensure_backend(self) -> None:
        if not self._is_windows and (self._user32 is None or self._kernel32 is None):
            raise RuntimeError("Windows hotkeys require Windows")
        if self._user32 is None:
            self._user32 = ctypes.windll.user32
        if self._kernel32 is None:
            self._kernel32 = ctypes.windll.kernel32
        self._configure_ctypes_prototypes()

    def _configure_ctypes_prototypes(self) -> None:
        try:
            self._user32.RegisterHotKey.argtypes = [
                wintypes.HWND,
                ctypes.c_int,
                wintypes.UINT,
                wintypes.UINT,
            ]
            self._user32.RegisterHotKey.restype = wintypes.BOOL
            self._user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
            self._user32.UnregisterHotKey.restype = wintypes.BOOL
            self._user32.PostThreadMessageW.argtypes = [
                wintypes.DWORD,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            ]
            self._user32.PostThreadMessageW.restype = wintypes.BOOL
            self._user32.GetMessageW.argtypes = [
                ctypes.POINTER(wintypes.MSG),
                wintypes.HWND,
                wintypes.UINT,
                wintypes.UINT,
            ]
            self._user32.GetMessageW.restype = wintypes.BOOL
            self._kernel32.GetCurrentThreadId.restype = wintypes.DWORD
        except AttributeError:
            return

    def _message_loop(self) -> None:
        ready = self._ready
        self._ready = None
        try:
            self._thread_id = int(self._kernel32.GetCurrentThreadId())
            if not self._user32.RegisterHotKey(None, HOTKEY_ID, 0, self._vk):
                self._running = False
                return
            self._running = True
        finally:
            if ready is not None:
                ready.set()
        if not self._running:
            return
        try:
            msg = wintypes.MSG()
            while self._user32.GetMessageW(ctypes.byref(msg), None, 0, 0):
                if int(msg.message) == WM_HOTKEY and int(msg.wParam) == HOTKEY_ID:
                    self._emit_for_tests()
        finally:
            self._user32.UnregisterHotKey(None, HOTKEY_ID)

    def _emit_for_tests(self) -> None:
        if self._handler is not None:
            self._handler()
