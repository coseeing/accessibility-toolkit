import ctypes
import subprocess
import sys
import types
from pathlib import Path

import pytest

from accessibility_toolkit.output.windows.clipboard import WindowsClipboardService
from accessibility_toolkit.input.windows.keyboard_hook import WindowsKeyboardCapture
from accessibility_toolkit.output.speech.windows.nvda_controller import (
    VENDORED_X64_DLL,
    NvdaControllerSpeechOutput,
)
from accessibility_toolkit.input import HID, KeyEvent
from accessibility_toolkit.input import CapturedKeyEvent
from accessibility_toolkit.input.windows.native_key_context import WindowsNativeKeyContext
from accessibility_toolkit.input import AppKeyEventResult, KeyboardPipelineResult


WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_QUIT = 0x0012
LLKHF_EXTENDED = 0x01
VK_NUMLOCK = 0x90


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
        self.key_state = 0

    def SetWindowsHookExW(self, hook_id, callback, instance, thread_id):
        self.installed.append((hook_id, callback, instance, thread_id))
        return self.hook_handle

    def UnhookWindowsHookEx(self, handle):
        self.unhooked.append(handle)
        return 1

    def CallNextHookEx(self, hook, n_code, w_param, l_param):
        return 0

    def GetKeyState(self, vk_code):
        assert vk_code == VK_NUMLOCK
        return self.key_state


class FakeKeyboardUser32WithoutKeyState:
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


def _passthrough(seen):
    def record(event):
        seen.append(event)
        return KeyboardPipelineResult(send_to_system=True, app_result=AppKeyEventResult.UNHANDLED)
    return record


def _suppress(seen):
    def record(event):
        seen.append(event)
        return KeyboardPipelineResult(send_to_system=False, app_result=AppKeyEventResult.UNHANDLED)
    return record


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
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]
    key_data = FakeKbdLlHookStruct(vkCode=0x09, scanCode=15, flags=0)

    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.TAB, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x09, scan_code=15, extended=False),
            num_lock_on=False,
        ),
    ]


def test_windows_keyboard_hook_callback_emits_num_lock_state():
    user32 = FakeKeyboardUser32()
    user32.key_state = 1
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]
    key_data = FakeKbdLlHookStruct(vkCode=0x09, scanCode=15, flags=0)

    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.TAB, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x09, scan_code=15, extended=False),
            num_lock_on=True,
        ),
    ]


def test_windows_keyboard_hook_callback_emits_none_num_lock_state_when_get_key_state_is_unavailable():
    user32 = FakeKeyboardUser32WithoutKeyState()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]
    key_data = FakeKbdLlHookStruct(vkCode=0x09, scanCode=15, flags=0)

    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.TAB, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x09, scan_code=15, extended=False),
            num_lock_on=None,
        ),
    ]


def test_windows_keyboard_hook_emits_num_lock_key_event_state():
    user32 = FakeKeyboardUser32()
    user32.key_state = 1
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]
    key_data = FakeKbdLlHookStruct(vkCode=VK_NUMLOCK, scanCode=69, flags=LLKHF_EXTENDED)

    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.NUM_LOCK, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=VK_NUMLOCK, scan_code=69, extended=True),
            num_lock_on=True,
        ),
    ]


def test_windows_keyboard_hook_emits_hid_for_digit_and_letter():
    user32 = FakeKeyboardUser32()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]

    key_data = FakeKbdLlHookStruct(vkCode=0x43, scanCode=46, flags=0)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))
    key_data = FakeKbdLlHookStruct(vkCode=0x31, scanCode=2, flags=0)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.C, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x43, scan_code=46, extended=False),
            num_lock_on=False,
        ),
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.DIGIT_1, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x31, scan_code=2, extended=False),
            num_lock_on=False,
        ),
    ]


def test_windows_keyboard_hook_emits_hid_for_backspace():
    user32 = FakeKeyboardUser32()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]
    key_data = FakeKbdLlHookStruct(vkCode=0x08, scanCode=14, flags=0)

    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.BACKSPACE, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x08, scan_code=14, extended=False),
            num_lock_on=False,
        ),
    ]


def test_windows_keyboard_hook_emits_hid_for_minus_equals():
    user32 = FakeKeyboardUser32()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]

    key_data = FakeKbdLlHookStruct(vkCode=0xBD, scanCode=12, flags=0)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.MINUS, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0xBD, scan_code=12, extended=False),
            num_lock_on=False,
        ),
    ]


def test_windows_keyboard_hook_emits_hid_for_left_meta_with_extended():
    user32 = FakeKeyboardUser32()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]
    key_data = FakeKbdLlHookStruct(vkCode=0x5B, scanCode=91, flags=LLKHF_EXTENDED)

    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.LEFT_META, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x5B, scan_code=91, extended=True),
            num_lock_on=False,
        ),
    ]


def test_windows_keyboard_hook_emits_hid_for_right_shift():
    user32 = FakeKeyboardUser32()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]
    key_data = FakeKbdLlHookStruct(vkCode=0xA1, scanCode=54, flags=0)

    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.RIGHT_SHIFT, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0xA1, scan_code=54, extended=False),
            num_lock_on=False,
        ),
    ]


@pytest.mark.parametrize(
    ("vk_code", "scan_code", "flags", "usage"),
    [
        (0xA0, 42, 0, HID.LEFT_SHIFT),
        (0xA0, 42, LLKHF_EXTENDED, HID.LEFT_SHIFT),
        (0xA1, 54, 0, HID.RIGHT_SHIFT),
        (0xA1, 54, LLKHF_EXTENDED, HID.RIGHT_SHIFT),
    ],
)
def test_windows_keyboard_hook_accepts_shift_keys_with_and_without_extended_flag(
    vk_code,
    scan_code,
    flags,
    usage,
):
    user32 = FakeKeyboardUser32()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]
    key_data = FakeKbdLlHookStruct(vkCode=vk_code, scanCode=scan_code, flags=flags)

    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=vk_code, scan_code=scan_code, extended=bool(flags & LLKHF_EXTENDED)),
            num_lock_on=False,
        ),
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

    from accessibility_toolkit.output.speech.windows import nvda_controller as module

    output = None
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(module, "VENDORED_X64_DLL", vendored_path)
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

    from accessibility_toolkit.output.speech.windows import nvda_controller as module

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(module, "VENDORED_X64_DLL", vendored_path)
    try:
        output = NvdaControllerSpeechOutput.load_default(loader=fail, is_windows=True)
    finally:
        monkeypatch.undo()

    assert loaded == [str(vendored_path)]
    assert output.available is False
    assert output.controller is None
    assert output.loaded_from is None


def test_nvda_controller_isolated_import_does_not_load_runtime():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import accessibility_toolkit.output.speech.windows.nvda_controller; "
                "assert not any(name == 'accessibility_toolkit.runtime' or "
                "name.startswith('accessibility_toolkit.runtime.') "
                "for name in sys.modules)"
            ),
        ],
        check=False,
        capture_output=True,
        cwd=Path(__file__).resolve().parents[2] / "src",
        text=True,
    )

    assert result.returncode == 0, result.stderr


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
    from accessibility_toolkit.input.windows.hotkey import WindowsHotkeyCapture

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
    from accessibility_toolkit.input.windows.hotkey import WindowsHotkeyCapture

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
    from accessibility_toolkit.input.windows.hotkey import WindowsHotkeyCapture

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
    from accessibility_toolkit.input.windows.hotkey import WindowsHotkeyCapture

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


def test_windows_keyboard_hook_emits_hid_for_semicolon_and_quote():
    user32 = FakeKeyboardUser32()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]

    key_data1 = FakeKbdLlHookStruct(vkCode=0xBA, scanCode=39, flags=0)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data1))
    key_data2 = FakeKbdLlHookStruct(vkCode=0xDE, scanCode=40, flags=0)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data2))

    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.SEMICOLON, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0xBA, scan_code=39, extended=False),
            num_lock_on=False,
        ),
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.QUOTE, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0xDE, scan_code=40, extended=False),
            num_lock_on=False,
        ),
    ]


def test_windows_keyboard_hook_emits_hid_for_insert_delete_and_page_down():
    user32 = FakeKeyboardUser32()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]

    key_data1 = FakeKbdLlHookStruct(vkCode=0x2D, scanCode=82, flags=LLKHF_EXTENDED)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data1))
    key_data2 = FakeKbdLlHookStruct(vkCode=0x2E, scanCode=83, flags=LLKHF_EXTENDED)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data2))
    key_data3 = FakeKbdLlHookStruct(vkCode=0x22, scanCode=81, flags=LLKHF_EXTENDED)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data3))

    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.INSERT, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x2D, scan_code=82, extended=True),
            num_lock_on=False,
        ),
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.DELETE, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x2E, scan_code=83, extended=True),
            num_lock_on=False,
        ),
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.PAGE_DOWN, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x22, scan_code=81, extended=True),
            num_lock_on=False,
        ),
    ]


def test_windows_keyboard_hook_distinguishes_numpad_from_main_cluster_keys():
    user32 = FakeKeyboardUser32()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]

    key_data1 = FakeKbdLlHookStruct(vkCode=0x61, scanCode=79, flags=0)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data1))
    key_data2 = FakeKbdLlHookStruct(vkCode=0x6F, scanCode=53, flags=LLKHF_EXTENDED)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data2))
    key_data3 = FakeKbdLlHookStruct(vkCode=0x6E, scanCode=83, flags=0)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data3))

    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_1, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x61, scan_code=79, extended=False),
            num_lock_on=False,
        ),
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_DIVIDE, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x6F, scan_code=53, extended=True),
            num_lock_on=False,
        ),
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_DECIMAL, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x6E, scan_code=83, extended=False),
            num_lock_on=False,
        ),
    ]


def test_windows_keyboard_hook_emits_hid_for_non_us_backslash_when_available():
    user32 = FakeKeyboardUser32()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]

    key_data = FakeKbdLlHookStruct(vkCode=0xE2, scanCode=86, flags=0)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.NON_US_BACKSLASH, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0xE2, scan_code=86, extended=False),
            num_lock_on=False,
        ),
    ]


def test_windows_keyboard_hook_emits_hid_for_keypad_equals():
    user32 = FakeKeyboardUser32()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]

    key_data = FakeKbdLlHookStruct(vkCode=0xBB, scanCode=89, flags=0)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_EQUALS, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0xBB, scan_code=89, extended=False),
            num_lock_on=False,
        ),
    ]


def test_windows_keyboard_hook_emits_hid_for_print_screen_scroll_lock_pause_num_lock_and_application():
    user32 = FakeKeyboardUser32()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]

    key_data = FakeKbdLlHookStruct(vkCode=0x2C, scanCode=55, flags=LLKHF_EXTENDED)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))
    key_data = FakeKbdLlHookStruct(vkCode=0x91, scanCode=70, flags=0)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))
    key_data = FakeKbdLlHookStruct(vkCode=0x13, scanCode=69, flags=0)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))
    key_data = FakeKbdLlHookStruct(vkCode=VK_NUMLOCK, scanCode=69, flags=LLKHF_EXTENDED)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))
    key_data = FakeKbdLlHookStruct(vkCode=0x5D, scanCode=93, flags=LLKHF_EXTENDED)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.PRINT_SCREEN, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x2C, scan_code=55, extended=True),
            num_lock_on=False,
        ),
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.SCROLL_LOCK, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x91, scan_code=70, extended=False),
            num_lock_on=False,
        ),
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.PAUSE, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x13, scan_code=69, extended=False),
            num_lock_on=False,
        ),
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.NUM_LOCK, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=VK_NUMLOCK, scan_code=69, extended=True),
            num_lock_on=False,
        ),
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.APPLICATION, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0x5D, scan_code=93, extended=True),
            num_lock_on=False,
        ),
    ]


def test_windows_keyboard_hook_emits_hid_for_common_jis_keys_when_available():
    user32 = FakeKeyboardUser32()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]

    key_data = FakeKbdLlHookStruct(vkCode=0xC0, scanCode=125, flags=0)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))
    key_data = FakeKbdLlHookStruct(vkCode=0xE2, scanCode=115, flags=0)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))
    key_data = FakeKbdLlHookStruct(vkCode=0xF3, scanCode=121, flags=0)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))
    key_data = FakeKbdLlHookStruct(vkCode=0xF4, scanCode=123, flags=0)
    callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert seen == [
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.NON_US_HASH, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0xC0, scan_code=125, extended=False),
            num_lock_on=False,
        ),
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.INTERNATIONAL1, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0xE2, scan_code=115, extended=False),
            num_lock_on=False,
        ),
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.INTERNATIONAL4, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0xF3, scan_code=121, extended=False),
            num_lock_on=False,
        ),
        CapturedKeyEvent(
            key_event=KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.INTERNATIONAL5, pressed=True),
            native_context=WindowsNativeKeyContext(vk_code=0xF4, scan_code=123, extended=False),
            num_lock_on=False,
        ),
    ]


def test_windows_hook_suppresses_when_send_to_system_is_false():
    user32 = FakeKeyboardUser32()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    capture.set_listener(lambda e: KeyboardPipelineResult(send_to_system=False, app_result=AppKeyEventResult.UNHANDLED))
    capture.start()
    callback = user32.installed[0][1]
    key_data = FakeKbdLlHookStruct(vkCode=0x09, scanCode=15, flags=0)

    result = callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert result == 1


def test_windows_hook_passes_through_when_send_to_system_is_true():
    user32 = FakeKeyboardUser32()
    capture = WindowsKeyboardCapture(
        user32=user32,
        kernel32=FakeKeyboardKernel32(),
        is_windows=True,
    )
    seen = []
    capture.set_listener(_passthrough(seen))
    capture.start()
    callback = user32.installed[0][1]
    key_data = FakeKbdLlHookStruct(vkCode=0x09, scanCode=15, flags=0)

    result = callback(0, WM_KEYDOWN, ctypes.addressof(key_data))

    assert result == 0
    assert len(seen) == 1


def test_windows_key_event_from_windows_maps_international3_via_vkcode_fallback():
    from accessibility_toolkit.input.windows.hid_map import key_event_from_windows
    assert key_event_from_windows(
        vk_code=0xF2,
        scan_code=0,
        extended=False,
        pressed=True,
    ) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.INTERNATIONAL3,
        pressed=True,
    )


def test_key_event_from_windows_falls_back_to_vk_when_scan_unknown():
    from accessibility_toolkit.input.windows.hid_map import key_event_from_windows

    # Scan code unrecognised (hardware-specific) → VK fallback
    event = key_event_from_windows(vk_code=0x23, scan_code=99999, extended=True, pressed=True)
    assert event is not None
    assert event == KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.END, pressed=True)

    # Standard scan code → scan code path takes priority
    event2 = key_event_from_windows(vk_code=0x23, scan_code=79, extended=True, pressed=True)
    assert event2 == KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.END, pressed=True)

    # Num lock ON numpad 1 via VK fallback
    event3 = key_event_from_windows(vk_code=0x61, scan_code=99999, extended=False, pressed=True)
    assert event3 == KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.KEYPAD_1, pressed=True)


@pytest.mark.parametrize(
    ("vk_code", "expected_usage"),
    [
        (0x60, HID.KEYPAD_0),
        (0x61, HID.KEYPAD_1),
        (0x62, HID.KEYPAD_2),
        (0x63, HID.KEYPAD_3),
        (0x64, HID.KEYPAD_4),
        (0x65, HID.KEYPAD_5),
        (0x66, HID.KEYPAD_6),
        (0x67, HID.KEYPAD_7),
        (0x68, HID.KEYPAD_8),
        (0x69, HID.KEYPAD_9),
        (0x23, HID.END),
        (0x24, HID.HOME),
        (0x25, HID.LEFT),
        (0x26, HID.UP),
        (0x27, HID.RIGHT),
        (0x28, HID.DOWN),
        (0x2D, HID.INSERT),
        (0x2E, HID.DELETE),
    ],
)
def test_key_event_from_windows_uses_vk_fallback_for_keypad_and_navigation_group(vk_code, expected_usage):
    from accessibility_toolkit.input.windows.hid_map import key_event_from_windows

    event = key_event_from_windows(
        vk_code=vk_code,
        scan_code=99999,
        extended=True,
        pressed=True,
    )

    assert event == KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=expected_usage, pressed=True)


def test_key_event_from_windows_prefers_standard_scan_code_over_vk_fallback():
    from accessibility_toolkit.input.windows.hid_map import key_event_from_windows

    event = key_event_from_windows(vk_code=0x23, scan_code=79, extended=True, pressed=True)

    assert event == KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.END, pressed=True)


@pytest.mark.parametrize(
    ("vk_code", "scan_code", "extended", "expected_usage"),
    [
        (0x23, 79, False, HID.KEYPAD_1),
        (0x28, 80, False, HID.KEYPAD_2),
        (0x22, 81, False, HID.KEYPAD_3),
        (0x25, 75, False, HID.KEYPAD_4),
        (0x27, 77, False, HID.KEYPAD_6),
        (0x24, 71, False, HID.KEYPAD_7),
        (0x26, 72, False, HID.KEYPAD_8),
        (0x21, 73, False, HID.KEYPAD_9),
        (0x2E, 83, False, HID.KEYPAD_DECIMAL),
        (0x62, 80, False, HID.KEYPAD_2),
    ],
)
def test_key_event_from_windows_preserves_keypad_origin_for_numlock_off_navigation_vks(
    vk_code,
    scan_code,
    extended,
    expected_usage,
):
    from accessibility_toolkit.input.windows.hid_map import key_event_from_windows

    event = key_event_from_windows(
        vk_code=vk_code,
        scan_code=scan_code,
        extended=extended,
        pressed=True,
    )

    assert event == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=expected_usage,
        pressed=True,
    )
