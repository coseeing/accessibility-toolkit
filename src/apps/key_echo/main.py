from dataclasses import dataclass
import logging
from typing import Any

from adapters.inputs.base import HotkeyCapture, InputCapture
from application.keyboard import KeyboardInputService
from application.output import Capabilities
from application.output import Scheduler
from application.output import QueuedService
from application.output.speech import SpeechService
from apps.key_echo.service import KeyEchoAppService
from bootstrap.runtime import configure_logging
from bootstrap.platform import (
    create_hotkey_capture,
    create_input_capture,
    default_speech_backend_options,
)


@dataclass(frozen=True)
class KeyEchoRuntime:
    input_capture: InputCapture
    hotkey_capture: HotkeyCapture
    scheduler: Scheduler
    speech: SpeechService
    speaker: QueuedService
    input_service: KeyboardInputService
    app_service: KeyEchoAppService
    app: Any


def build_runtime() -> KeyEchoRuntime:
    from ui.echo.app import EchoApp

    input_capture = create_input_capture()
    hotkey_capture = create_hotkey_capture(KeyEchoAppService.enter_usage)
    scheduler = Scheduler()
    speech = SpeechService(
        backend_options=default_speech_backend_options(scheduler),
        selected_backend_id="pyttsx3",
        scheduler=scheduler,
    )
    speaker = QueuedService(
        speech=speech,
    )
    app_service = KeyEchoAppService(
        hotkey_capture=hotkey_capture,
        input_capture=input_capture,
        capabilities=Capabilities(speech=speaker),
        main_thread_dispatch=getattr(EchoApp, "dispatch", None),
    )
    input_service = KeyboardInputService(input_capture, app_service)
    app_service.attach_input_service(input_service)
    app_service.bind()
    hotkey_capture.start()
    app = EchoApp(controller=app_service)
    return KeyEchoRuntime(
        input_capture=input_capture,
        hotkey_capture=hotkey_capture,
        scheduler=scheduler,
        speech=speech,
        speaker=speaker,
        input_service=input_service,
        app_service=app_service,
        app=app,
    )


def main() -> int:
    try:
        configure_logging(app_name="key_echo")
    except OSError:
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            )
        logging.getLogger(__name__).warning(
            "Logging initialization failed; continuing without file logging",
            exc_info=True,
        )
    runtime = build_runtime()
    return runtime.app.MainLoop()


if __name__ == "__main__":
    raise SystemExit(main())
