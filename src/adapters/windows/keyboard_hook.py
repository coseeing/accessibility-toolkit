from collections.abc import Callable
import ctypes
import sys
from ctypes import wintypes
from typing import Any

from adapters.inputs.base import KeyEventDecision
from remote_core.models.keys import KeyEvent


WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
LLKHF_EXTENDED = 0x01


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.c_ulong),
        ("scanCode", ctypes.c_ulong),
        ("flags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


_WINFUNCTYPE = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)
LowLevelKeyboardProc = _WINFUNCTYPE(
    ctypes.c_long,
    ctypes.c_int,
    ctypes.c_size_t,
    ctypes.c_size_t,
)


class WindowsKeyboardCapture:
    def __init__(
        self,
        *,
        user32: Any | None = None,
        kernel32: Any | None = None,
        is_windows: bool | None = None,
    ) -> None:
        self._listener: Callable[[KeyEvent], KeyEventDecision] | None = None
        self._running = False
        self._is_windows = sys.platform == "win32" if is_windows is None else is_windows
        self._user32 = user32
        self._kernel32 = kernel32
        self._hook_handle: int | None = None
        self._callback: Any | None = None

    @property
    def running(self) -> bool:
        return self._running

    def set_listener(self, listener: Callable[[KeyEvent], KeyEventDecision]) -> None:
        self._listener = listener

    def start(self) -> None:
        if self._running:
            return
        self._ensure_backend()
        module_handle = self._kernel32.GetModuleHandleW(None)
        self._callback = LowLevelKeyboardProc(self._handle_keyboard_event)
        hook_handle = self._user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._callback,
            module_handle,
            0,
        )
        if not hook_handle:
            self._callback = None
            raise RuntimeError("Failed to install Windows keyboard hook")
        self._hook_handle = hook_handle
        self._running = True

    def stop(self) -> None:
        if self._hook_handle is not None and self._user32 is not None:
            self._user32.UnhookWindowsHookEx(self._hook_handle)
            self._hook_handle = None
            self._callback = None
        self._running = False

    def _ensure_backend(self) -> None:
        if not self._is_windows and (self._user32 is None or self._kernel32 is None):
            raise RuntimeError("Windows keyboard hooks require Windows")
        if self._user32 is None:
            self._user32 = ctypes.windll.user32
        if self._kernel32 is None:
            self._kernel32 = ctypes.windll.kernel32
        self._configure_ctypes_prototypes()

    def _configure_ctypes_prototypes(self) -> None:
        try:
            self._user32.SetWindowsHookExW.argtypes = [
                ctypes.c_int,
                LowLevelKeyboardProc,
                wintypes.HANDLE,
                wintypes.DWORD,
            ]
            self._user32.SetWindowsHookExW.restype = wintypes.HANDLE
            self._user32.UnhookWindowsHookEx.argtypes = [wintypes.HANDLE]
            self._user32.UnhookWindowsHookEx.restype = wintypes.BOOL
            self._user32.CallNextHookEx.argtypes = [
                wintypes.HANDLE,
                ctypes.c_int,
                wintypes.WPARAM,
                wintypes.LPARAM,
            ]
            self._user32.CallNextHookEx.restype = ctypes.c_ssize_t
            self._kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
            self._kernel32.GetModuleHandleW.restype = wintypes.HANDLE
        except AttributeError:
            return

    def _handle_keyboard_event(self, n_code: int, w_param: int, l_param: int) -> int:
        if n_code >= 0 and w_param in (WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP):
            data = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            decision = self._emit_for_tests(
                vk=int(data.vkCode),
                scan=int(data.scanCode),
                extended=bool(data.flags & LLKHF_EXTENDED),
                pressed=w_param in (WM_KEYDOWN, WM_SYSKEYDOWN),
            )
            if decision in (
                KeyEventDecision.FORWARD_AND_SUPPRESS,
                KeyEventDecision.LOCAL_ONLY_SUPPRESS,
            ):
                return 1
        if self._user32 is None:
            return 0
        return int(self._user32.CallNextHookEx(self._hook_handle, n_code, w_param, l_param))

    def _emit_for_tests(
        self, vk: int, scan: int | None, extended: bool, pressed: bool
    ) -> KeyEventDecision:
        if self._listener is None:
            return KeyEventDecision.PASS_THROUGH
        return self._listener(
            KeyEvent(vk=vk, scan=scan, extended=extended, pressed=pressed)
        )
