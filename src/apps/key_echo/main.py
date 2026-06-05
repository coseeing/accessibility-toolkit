from dataclasses import dataclass

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
    return 0
