import ctypes
import sys
import types

import pytest

from adapters.windows.clipboard import WindowsClipboardService
from adapters.windows.keyboard_hook import WindowsKeyboardCapture
from adapters.windows.nvda_controller import NvdaControllerSpeechOutput
from remote_core.models.keys import KeyEvent


WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
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


def test_windows_keyboard_hook_callback_emits_normalized_key_event():
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
    key_data = FakeKbdLlHookStruct(vkCode=9, scanCode=15, flags=LLKHF_EXTENDED)

    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))
    key_data.flags = 0
    callback(0, WM_KEYUP, ctypes.addressof(key_data))

    assert seen == [
        KeyEvent(vk=9, scan=15, extended=True, pressed=True),
        KeyEvent(vk=9, scan=15, extended=False, pressed=False),
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

        def speakText(self, text):
            self.spoken.append(text)

    dll = FakeDll()

    output = NvdaControllerSpeechOutput.load_default(loader=lambda _name: dll, is_windows=True)

    assert output.available is True
    assert output.controller is dll


def test_nvda_controller_load_default_failure_returns_unavailable():
    def fail(_name):
        raise OSError("missing")

    output = NvdaControllerSpeechOutput.load_default(loader=fail, is_windows=True)

    assert output.available is False
    assert output.controller is None


def test_main_uses_nvda_controller_loader(monkeypatch):
    fake_app_module = types.ModuleType("app_wx.app")
    created = {}

    class FakeApp:
        def __init__(self, controller):
            created["controller"] = controller

        def MainLoop(self):
            return 0

    fake_app_module.NvdaRemoteApp = FakeApp
    monkeypatch.setitem(sys.modules, "app_wx.app", fake_app_module)

    import app_wx.main as main_module

    speech_output = object()
    monkeypatch.setattr(
        main_module.NvdaControllerSpeechOutput,
        "load_default",
        staticmethod(lambda: speech_output),
    )

    assert main_module.main() == 0
    assert created["controller"].output_manager.speech_output is speech_output
