import ctypes
import sys
import types
from pathlib import Path

import pytest

from adapters.windows.clipboard import WindowsClipboardService
from adapters.windows.keyboard_hook import WindowsKeyboardCapture
from adapters.windows.nvda_controller import (
    VENDORED_X64_DLL,
    NvdaControllerSpeechOutput,
)
from adapters.windows.hotkey import WindowsKeyPressHotkeyCapture
from interop.key import HID, KeyEvent
from adapters.inputs.base import KeyEventDecision


WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_QUIT = 0x0012
LLKHF_EXTENDED = 0x01


class FakeKbdLlHookStruct(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.c_ulong),
        ("scanCode", ctypes.c_ulong),
        ("flags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class FakeKeyboardUser32:
    def __init__(self, hook_handle=123):
        self.hook_handle = hook_handle
        self.installed = []
        self.unhooked = []

    def SetWindowsHookExW(self, hook_id, callback, instance, thread_id):
        self.installed.append((hook_id, callback, instance, thread_id))
        return self.hook_handle

    def UnhookWindowsHookEx(self, handle):
        self.unhooked.append(handle)
        return 1

    def CallNextHookEx(self, hook, n_code, w_param, l_param):
        return 0


class FakeKeyboardKernel32:
    def GetModuleHandleW(self, name):
        assert name is None
        return 456


def test_windows_keyboard_capture_installs_and_unhooks_low_level_hook():
    user32 = FakeKeyboardUser32()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )

    capture.start()
    capture.stop()

    assert capture.running is False
    assert user32.installed[0][0] == 13
    assert user32.installed[0][2] == 456
    assert user32.installed[0][3] == 0
    assert user32.unhooked == [123]


def test_windows_keyboard_hook_callback_emits_hid_key_event():
    user32 = FakeKeyboardUser32()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(seen.append)
    capture.start()
    callback = user32.installed[0][1]
    key_data = FakeKbdLlHookStruct(vkCode=0x09, scanCode=15, flags=0)

    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert seen == [
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.TAB, pressed=True),
    ]


def test_windows_keyboard_capture_start_failure_is_clear():
    user32 = FakeKeyboardUser32(hook_handle=0)
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )

    with pytest.raises(RuntimeError, match="Failed to install Windows keyboard hook"):
        capture.start()


def test_windows_keyboard_capture_requires_windows_without_injected_backend():
    capture = WindowsKeyboardCapture(is_windows=False)

    with pytest.raises(RuntimeError, match="Windows keyboard hooks require Windows"):
        capture.start()


class FakeClipboardBackend:
    def __init__(self):
        self.text = ""

    def get_text(self):
        return self.text

    def set_text(self, text):
        self.text = text


def test_windows_clipboard_service_uses_injected_backend_by_default_path():
    backend = FakeClipboardBackend()
    service = WindowsClipboardService(backend=backend)

    service.set_text("hello")

    assert service.get_text() == "hello"


def test_windows_clipboard_default_requires_windows_on_non_windows():
    service = WindowsClipboardService(is_windows=False)

    with pytest.raises(RuntimeError, match="Windows clipboard requires Windows"):
        service.get_text()


def test_nvda_controller_load_default_uses_loader_and_marks_available():
    class FakeDll:
        def __init__(self):
            self.spoken = []

        def nvdaController_speakSsml(
            self,
            ssml,
            symbol_level,
            priority,
            asynchronous,
        ):
            self.spoken.append((ssml, symbol_level, priority, asynchronous))

    dll = FakeDll()
    loaded = []
    vendored_path = Path("/tmp/nvdaControllerClient.dll")

    def fake_loader(name):
        loaded.append(name)
        return dll

    from adapters.windows import nvda_controller as module

    output = None
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(module, "resource_path", lambda relative_path: vendored_path)
    try:
        output = NvdaControllerSpeechOutput.load_default(loader=fake_loader, is_windows=True)
    finally:
        monkeypatch.undo()

    assert loaded == [str(vendored_path)]
    assert output.available is True
    assert output.controller is dll
    assert output.loaded_from == str(vendored_path)


def test_nvda_controller_load_default_does_not_fallback_when_vendored_path_fails():
    loaded = []
    vendored_path = Path("/tmp/nvdaControllerClient.dll")

    def fail(name):
        loaded.append(name)
        raise OSError("missing")

    from adapters.windows import nvda_controller as module

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(module, "resource_path", lambda relative_path: vendored_path)
    try:
        output = NvdaControllerSpeechOutput.load_default(loader=fail, is_windows=True)
    finally:
        monkeypatch.undo()

    assert loaded == [str(vendored_path)]
    assert output.available is False
    assert output.controller is None
    assert output.loaded_from is None


def test_main_uses_nvda_controller_loader(monkeypatch):
    fake_main_module = types.ModuleType("apps.nvda_remote.main")
    called = {}

    def fake_main():
        called["ran"] = True
        return 0

    fake_main_module.main = fake_main
    sys.modules.pop("ui.main", None)
    monkeypatch.setitem(sys.modules, "apps.nvda_remote.main", fake_main_module)
    import ui.main as main_module

    assert main_module.main() == 0


class FakeHotkeyUser32:
    def __init__(self, register_result=True):
        self.register_result = register_result
        self.registered = []
        self.unregistered = []
        self.posted = []
        self._quitting = False

    def RegisterHotKey(self, hwnd, hotkey_id, mods, vk):
        self.registered.append((hwnd, hotkey_id, mods, vk))
        return self.register_result

    def UnregisterHotKey(self, hwnd, hotkey_id):
        self.unregistered.append((hwnd, hotkey_id))
        return True

    def PostThreadMessageW(self, thread_id, msg, wparam, lparam):
        self.posted.append((thread_id, msg, wparam, lparam))
        if msg == WM_QUIT:
            self._quitting = True
        return True

    def GetMessageW(self, msg_ptr, hwnd, filter_min, filter_max):
        if self._quitting:
            return False
        import time
        time.sleep(0.01)
        if self._quitting:
            return False
        return True


class FakeHotkeyKernel32:
    def __init__(self):
        self._tid = 9999

    def GetCurrentThreadId(self):
        return self._tid


def test_windows_hotkey_capture_starts_and_registers():
    from adapters.windows.hotkey import WindowsHotkeyCapture

    user32 = FakeHotkeyUser32(register_result=True)
    kernel32 = FakeHotkeyKernel32()
    capture = WindowsHotkeyCapture(
        user32=user32,
        kernel32=kernel32,
        is_windows=True,
    )

    capture.start()
    assert capture.running is True
    assert len(user32.registered) == 1
    assert user32.registered[0][1] == 1  # hotkey_id
    assert user32.registered[0][3] == 0x7A  # F11 vk

    capture.stop()
    assert capture.running is False
    assert len(user32.unregistered) == 1


def test_windows_hotkey_capture_raises_on_register_failure():
    from adapters.windows.hotkey import WindowsHotkeyCapture

    user32 = FakeHotkeyUser32(register_result=False)
    kernel32 = FakeHotkeyKernel32()
    capture = WindowsHotkeyCapture(
        user32=user32,
        kernel32=kernel32,
        is_windows=True,
    )

    with pytest.raises(RuntimeError, match="Failed to register F11 hotkey"):
        capture.start()

    assert capture.running is False
    assert user32.unregistered == []


def test_windows_hotkey_capture_starts_does_not_double_start():
    from adapters.windows.hotkey import WindowsHotkeyCapture

    user32 = FakeHotkeyUser32(register_result=True)
    kernel32 = FakeHotkeyKernel32()
    capture = WindowsHotkeyCapture(
        user32=user32,
        kernel32=kernel32,
        is_windows=True,
    )

    capture.start()
    capture.start()  # should be no-op

    assert capture.running is True
    assert len(user32.registered) == 1


def test_windows_hotkey_capture_stop_does_not_double_stop():
    from adapters.windows.hotkey import WindowsHotkeyCapture

    user32 = FakeHotkeyUser32(register_result=True)
    kernel32 = FakeHotkeyKernel32()
    capture = WindowsHotkeyCapture(
        user32=user32,
        kernel32=kernel32,
        is_windows=True,
    )

    capture.start()
    capture.stop()
    capture.stop()  # should be no-op

    assert capture.running is False
    assert len(user32.unregistered) == 1


class FakeKeyboardCaptureForHotkey:
    def __init__(self):
        self.listener = None
        self.start_calls = 0
        self.stop_calls = 0

    @property
    def running(self):
        return self.start_calls > self.stop_calls

    def set_listener(self, listener):
        self.listener = listener

    def start(self):
        self.start_calls += 1

    def stop(self):
        self.stop_calls += 1


def test_windows_keypress_hotkey_capture_triggers_handler_on_matching_keydown():
    keyboard = FakeKeyboardCaptureForHotkey()
    seen = []
    capture = WindowsKeyPressHotkeyCapture(
        keyboard_capture=keyboard,
        vk=0x0D,
    )
    capture.set_handler(lambda: seen.append("enter"))

    capture.start()
    decision = keyboard.listener(
        KeyEvent(vk=0x0D, scan=28, extended=False, pressed=True)
    )

    assert decision == KeyEventDecision.SUPPRESS
    assert seen == ["enter"]


def test_windows_keypress_hotkey_capture_ignores_non_matching_keys():
    keyboard = FakeKeyboardCaptureForHotkey()
    seen = []
    capture = WindowsKeyPressHotkeyCapture(
        keyboard_capture=keyboard,
        vk=0x0D,
    )
    capture.set_handler(lambda: seen.append("enter"))

    capture.start()
    decision = keyboard.listener(
        KeyEvent(vk=0x41, scan=30, extended=False, pressed=True)
    )

    assert decision == KeyEventDecision.PASS_THROUGH
    assert seen == []
