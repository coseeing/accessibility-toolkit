from dataclasses import dataclass
from typing import Any

from adapters.inputs.base import HotkeyCapture, InputCapture
from application.keyboard import KeyboardInputService
from application.output_capabilities import OutputCapabilities
from application.output_scheduler import OutputScheduler
from application.output_service import QueuedOutputService
from application.speech_service import SpeechService
from apps.key_echo.facade import KeyEchoAppFacade
from bootstrap.platform import (
    create_hotkey_capture,
    create_input_capture,
    default_speech_backend_options,
)


@dataclass(frozen=True)
class KeyEchoRuntime:
    input_capture: InputCapture
    hotkey_capture: HotkeyCapture
    output_scheduler: OutputScheduler
    speech_service: SpeechService
    output_service: QueuedOutputService
    input_service: KeyboardInputService
    app_service: KeyEchoAppFacade
    app: Any


def build_runtime() -> KeyEchoRuntime:
    from ui.echo.app import EchoApp

    input_capture = create_input_capture()
    hotkey_capture = create_hotkey_capture()
    output_scheduler = OutputScheduler()
    speech_service = SpeechService(
        backend_options=default_speech_backend_options(output_scheduler),
        selected_backend_id="pyttsx3",
    )
    output_service = QueuedOutputService(
        speech=speech_service,
        scheduler=output_scheduler,
    )
    app_service = KeyEchoAppFacade(
        hotkey_capture=hotkey_capture,
        outputs=OutputCapabilities(speech=output_service),
    )
    input_service = KeyboardInputService(input_capture, app_service)
    app_service.attach_input_service(input_service)
    app_service.bind()
    hotkey_capture.start()
    app = EchoApp(controller=app_service)
    return KeyEchoRuntime(
        input_capture=input_capture,
        hotkey_capture=hotkey_capture,
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
