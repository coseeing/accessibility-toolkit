from collections.abc import Callable
import ctypes
import logging
import sys
from ctypes import wintypes
from typing import Any

from adapters.inputs.base import KeyEventDecision
from adapters.inputs.captured_event import CapturedKeyEvent
from adapters.windows.hid_map import key_event_from_windows
from adapters.windows.native_key_context import WindowsNativeKeyContext
from interop.key.key_event import KeyEvent


WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
LLKHF_EXTENDED = 0x01

_logger = logging.getLogger(__name__)


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
        self._listener: Callable[[CapturedKeyEvent], KeyEventDecision] | None = None
        self._running = False
        self._is_windows = sys.platform == "win32" if is_windows is None else is_windows
        self._user32 = user32
        self._kernel32 = kernel32
        self._hook_handle: int | None = None
        self._callback: Any | None = None

    @property
    def running(self) -> bool:
        return self._running

    def set_listener(self, listener: Callable[[CapturedKeyEvent], KeyEventDecision]) -> None:
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
            vk_code = int(data.vkCode)
            scan_code = int(data.scanCode)
            extended = bool(data.flags & LLKHF_EXTENDED)
            pressed = w_param in (WM_KEYDOWN, WM_SYSKEYDOWN)
            event = key_event_from_windows(
                vk_code=vk_code,
                scan_code=scan_code,
                extended=extended,
                pressed=pressed,
            )
            _logger.debug(
                "Windows hook raw vk=0x%02X scan=%d extended=%s pressed=%s mapped=%s",
                vk_code,
                scan_code,
                extended,
                pressed,
                (
                    f"0x{event.usage_page:02X}:0x{event.usage:02X}"
                    if event is not None
                    else "None"
                ),
            )
            decision = self._emit_for_tests(event, vk_code, scan_code, extended)
            if decision == KeyEventDecision.SUPPRESS:
                return 1
        if self._user32 is None:
            return 0
        return int(self._user32.CallNextHookEx(self._hook_handle, n_code, w_param, l_param))

    def _emit_for_tests(self, event: KeyEvent | None, vk_code: int, scan_code: int, extended: bool) -> KeyEventDecision:
        if event is None or self._listener is None:
            return KeyEventDecision.PASS_THROUGH
        return self._listener(
            CapturedKeyEvent(
                key_event=event,
                native_context=WindowsNativeKeyContext(
                    vk_code=vk_code,
                    scan_code=scan_code,
                    extended=extended,
                ),
            )
        )
