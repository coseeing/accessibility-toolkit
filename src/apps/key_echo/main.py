from dataclasses import dataclass
from typing import Any

from adapters.outputs.drivers.pyttsx3 import Pyttsx3SpeechOutput
from adapters.windows.keyboard_hook import WindowsKeyboardCapture
from adapters.windows.nvda_controller import NvdaControllerSpeechOutput
from application.keyboard import KeyboardInputService
from application.output_capabilities import OutputCapabilities
from application.output_scheduler import OutputScheduler
from application.output_service import QueuedOutputService
from application.speech_backends import SpeechBackendOption
from application.speech_service import SpeechService
from apps.key_echo.service import KeyEchoAppService


@dataclass(frozen=True)
class KeyEchoRuntime:
    capture: WindowsKeyboardCapture
    output_scheduler: OutputScheduler
    speech_service: SpeechService
    output_service: QueuedOutputService
    input_service: KeyboardInputService
    app_service: KeyEchoAppService
    app: Any


def build_runtime() -> KeyEchoRuntime:
    from ui.echo.app import EchoApp

    capture = WindowsKeyboardCapture()
    output_scheduler = OutputScheduler()
    speech_service = SpeechService(
        backend_options=(
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
                factory=lambda: NvdaControllerSpeechOutput.load_default(
                    scheduler=output_scheduler
                ),
            ),
        ),
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


def main() -> int:
    runtime = build_runtime()
    return runtime.app.MainLoop()


if __name__ == "__main__":
    raise SystemExit(main())
