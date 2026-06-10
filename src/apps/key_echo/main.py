from dataclasses import dataclass
from typing import Any

from application.keyboard import KeyboardInputService
from application.output_capabilities import OutputCapabilities
from application.output_scheduler import OutputScheduler
from application.output_service import QueuedOutputService
from application.speech_service import SpeechService
from apps.key_echo.service import KeyEchoAppService
from bootstrap.platform import (
    create_input_capture,
    default_speech_backend_options,
)


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
    from ui.echo.app import EchoApp

    capture = create_input_capture()
    output_scheduler = OutputScheduler()
    speech_service = SpeechService(
        backend_options=default_speech_backend_options(output_scheduler),
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
