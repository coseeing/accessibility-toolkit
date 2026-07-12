from accessibility_toolkit.input.windows.hid_map import key_event_from_windows
from accessibility_toolkit.input.windows.hotkey import WindowsHotkeyCapture
from accessibility_toolkit.input.windows.keyboard_hook import WindowsKeyboardCapture
from accessibility_toolkit.input.windows.native_key_context import WindowsNativeKeyContext


WindowsKeyboardHook = WindowsKeyboardCapture


__all__ = [
    "WindowsHotkeyCapture",
    "WindowsKeyboardCapture",
    "WindowsKeyboardHook",
    "WindowsNativeKeyContext",
    "key_event_from_windows",
]
