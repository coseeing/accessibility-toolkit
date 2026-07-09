from collections.abc import Callable
import ctypes
import sys
from ctypes import wintypes
from typing import Any


CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002


class WindowsClipboardService:
    def __init__(
        self,
        reader: Callable[[], str] | None = None,
        writer: Callable[[str], None] | None = None,
        *,
        backend: Any | None = None,
        is_windows: bool | None = None,
    ) -> None:
        self._backend = backend
        self._is_windows = sys.platform == "win32" if is_windows is None else is_windows
        self._reader = reader
        self._writer = writer

    def set_text(self, text: str) -> None:
        if self._writer is not None:
            self._writer(text)
            return
        self._get_backend().set_text(text)

    def get_text(self) -> str:
        if self._reader is not None:
            return self._reader()
        return self._get_backend().get_text()

    def _get_backend(self) -> Any:
        if self._backend is not None:
            return self._backend
        if not self._is_windows:
            raise RuntimeError("Windows clipboard requires Windows")
        self._backend = _CtypesWindowsClipboardBackend()
        return self._backend


class _CtypesWindowsClipboardBackend:
    def __init__(self) -> None:
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32
        self._configure_ctypes_prototypes()

    def _configure_ctypes_prototypes(self) -> None:
        self._user32.OpenClipboard.argtypes = [wintypes.HWND]
        self._user32.OpenClipboard.restype = wintypes.BOOL
        self._user32.CloseClipboard.argtypes = []
        self._user32.CloseClipboard.restype = wintypes.BOOL
        self._user32.EmptyClipboard.argtypes = []
        self._user32.EmptyClipboard.restype = wintypes.BOOL
        self._user32.GetClipboardData.argtypes = [wintypes.UINT]
        self._user32.GetClipboardData.restype = wintypes.HANDLE
        self._user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        self._user32.SetClipboardData.restype = wintypes.HANDLE
        self._kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        self._kernel32.GlobalAlloc.restype = wintypes.HANDLE
        self._kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
        self._kernel32.GlobalLock.restype = ctypes.c_void_p
        self._kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
        self._kernel32.GlobalUnlock.restype = wintypes.BOOL

    def get_text(self) -> str:
        if not self._user32.OpenClipboard(None):
            raise RuntimeError("Failed to open Windows clipboard")
        try:
            handle = self._user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return ""
            pointer = self._kernel32.GlobalLock(handle)
            if not pointer:
                return ""
            try:
                return ctypes.wstring_at(pointer)
            finally:
                self._kernel32.GlobalUnlock(handle)
        finally:
            self._user32.CloseClipboard()

    def set_text(self, text: str) -> None:
        if not self._user32.OpenClipboard(None):
            raise RuntimeError("Failed to open Windows clipboard")
        try:
            if not self._user32.EmptyClipboard():
                raise RuntimeError("Failed to empty Windows clipboard")
            data = text + "\0"
            byte_count = len(data.encode("utf-16-le"))
            handle = self._kernel32.GlobalAlloc(GMEM_MOVEABLE, byte_count)
            if not handle:
                raise RuntimeError("Failed to allocate Windows clipboard memory")
            pointer = self._kernel32.GlobalLock(handle)
            if not pointer:
                raise RuntimeError("Failed to lock Windows clipboard memory")
            try:
                ctypes.memmove(pointer, data.encode("utf-16-le"), byte_count)
            finally:
                self._kernel32.GlobalUnlock(handle)
            if not self._user32.SetClipboardData(CF_UNICODETEXT, handle):
                raise RuntimeError("Failed to set Windows clipboard data")
        finally:
            self._user32.CloseClipboard()
