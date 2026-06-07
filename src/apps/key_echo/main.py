from dataclasses import dataclass
import importlib
import sys
from typing import Any

from adapters.outputs.drivers.pyttsx3 import Pyttsx3SpeechOutput
from application.keyboard import KeyboardInputService
from application.output_capabilities import OutputCapabilities
from application.output_scheduler import OutputScheduler
from application.output_service import QueuedOutputService
from application.speech_backends import SpeechBackendOption
from application.speech_service import SpeechService
from apps.key_echo.service import KeyEchoAppService

WindowsKeyboardCapture = None
NvdaControllerSpeechOutput = None


@dataclass(frozen=True)
class KeyEchoRuntime:
    capture: Any
    output_scheduler: OutputScheduler
    speech_service: SpeechService
    output_service: QueuedOutputService
    input_service: KeyboardInputService
    app_service: KeyEchoAppService
    app: Any


def build_runtime() -> KeyEchoRuntime:
    if sys.platform != "win32":
        raise RuntimeError("key_echo is currently supported only on Windows")

    from ui.echo.app import EchoApp

    capture = _get_windows_keyboard_capture_class()()
    output_scheduler = OutputScheduler()
    speech_service = SpeechService(
        backend_options=_default_backend_options(output_scheduler),
        selected_backend_id="pyttsx3",
    )
    output_service = QueuedOutputService(
        speech=speech_service,
        scheduler=output_scheduler,
    )
    app_service = KeyEchoAppService(
        outputs=OutputCapabilities(speech=output_service),
    )
    input_service = KeyboardInputService(capture, app_service)
    input_service.bind()
    app_service.attach_input_service(input_service)
    app = EchoApp(controller=app_service)
    return KeyEchoRuntime(
        capture=capture,
        output_scheduler=output_scheduler,
        speech_service=speech_service,
        output_service=output_service,
        input_service=input_service,
        app_service=app_service,
        app=app,
    )


def _default_backend_options(
    output_scheduler: OutputScheduler,
) -> tuple[SpeechBackendOption, ...]:
    return (
        SpeechBackendOption(
            backend_id="pyttsx3",
            label="pyttsx3",
            factory=lambda: Pyttsx3SpeechOutput.load_default(
                scheduler=output_scheduler
            ),
        ),
        SpeechBackendOption(
            backend_id="nvda_controller",
            label="NVDA Controller",
            factory=lambda: _get_nvda_controller_speech_output_class().load_default(
                scheduler=output_scheduler
            ),
        ),
    )


def _get_windows_keyboard_capture_class() -> Any:
    global WindowsKeyboardCapture
    if WindowsKeyboardCapture is None:
        module = importlib.import_module("adapters.windows.keyboard_hook")
        WindowsKeyboardCapture = module.WindowsKeyboardCapture
    return WindowsKeyboardCapture


def _get_nvda_controller_speech_output_class() -> Any:
    global NvdaControllerSpeechOutput
    if NvdaControllerSpeechOutput is None:
        module = importlib.import_module("adapters.windows.nvda_controller")
        NvdaControllerSpeechOutput = module.NvdaControllerSpeechOutput
    return NvdaControllerSpeechOutput


def main() -> int:
    runtime = build_runtime()
    return runtime.app.MainLoop()


if __name__ == "__main__":
    raise SystemExit(main())
