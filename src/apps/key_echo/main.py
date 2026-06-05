from dataclasses import dataclass
import ctypes
import sys
from ctypes import wintypes

from adapters.outputs.drivers.pyttsx3 import Pyttsx3SpeechOutput
from adapters.windows.keyboard_hook import WindowsKeyboardCapture
from application.keyboard import KeyboardInputService
from application.output_capabilities import OutputCapabilities
from application.speech_service import SpeechService
from apps.key_echo.service import KeyEchoAppService


@dataclass(frozen=True)
class KeyEchoRuntime:
    capture: WindowsKeyboardCapture
    speech_service: SpeechService
    input_service: KeyboardInputService
    app_service: KeyEchoAppService


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt_x", ctypes.c_long),
        ("pt_y", ctypes.c_long),
        ("lPrivate", wintypes.DWORD),
    ]


def _pump_windows_messages() -> None:
    if sys.platform != "win32":
        raise RuntimeError("Key echo message pump requires Windows")

    user32 = ctypes.windll.user32
    message = MSG()
    get_message = user32.GetMessageW
    translate_message = user32.TranslateMessage
    dispatch_message = user32.DispatchMessageW

    while True:
        result = int(get_message(ctypes.byref(message), None, 0, 0))
        if result == -1:
            raise RuntimeError("Windows message pump failed")
        if result == 0:
            return
        translate_message(ctypes.byref(message))
        dispatch_message(ctypes.byref(message))


def build_runtime() -> KeyEchoRuntime:
    capture = WindowsKeyboardCapture()
    speech_service = SpeechService.single_backend(Pyttsx3SpeechOutput.load_default())
    app_service = KeyEchoAppService(outputs=OutputCapabilities(speech=speech_service))
    input_service = KeyboardInputService(capture, app_service)
    return KeyEchoRuntime(
        capture=capture,
        speech_service=speech_service,
        input_service=input_service,
        app_service=app_service,
    )


def main() -> int:
    runtime = build_runtime()
    runtime.input_service.start()
    try:
        _pump_windows_messages()
    except KeyboardInterrupt:
        pass
    finally:
        runtime.input_service.stop()
    return 0
