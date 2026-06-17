from dataclasses import dataclass
import logging
from typing import Any

from adapters.inputs.base import HotkeyCapture, InputCapture
from application.keyboard import KeyboardInputService
from application.output_capabilities import OutputCapabilities
from application.output_scheduler import OutputScheduler
from application.output_service import QueuedOutputService
from application.speech_service import SpeechService
from apps.access8graph.service import Access8GraphAppService
from bootstrap.platform import (
    create_hotkey_capture,
    create_input_capture,
    create_tone_output,
    default_speech_backend_id,
    default_speech_backend_options,
)
from bootstrap.runtime import configure_logging


@dataclass(frozen=True)
class Access8GraphRuntime:
    input_capture: InputCapture
    hotkey_capture: HotkeyCapture
    tone_output: object
    speech_scheduler: OutputScheduler
    speech_service: SpeechService
    output_service: QueuedOutputService
    input_service: KeyboardInputService
    app_service: Access8GraphAppService
    app: Any


def build_runtime() -> Access8GraphRuntime:
    from ui.access8graph.app import Access8GraphApp

    input_capture = create_input_capture()
    hotkey_capture = create_hotkey_capture(Access8GraphAppService.enter_usage)
    tone_output = create_tone_output()
    speech_scheduler = OutputScheduler()
    speech_service = SpeechService(
        backend_options=default_speech_backend_options(speech_scheduler),
        selected_backend_id=default_speech_backend_id(),
        scheduler=speech_scheduler,
    )
    output_service = QueuedOutputService(speech=speech_service)
    app_service = Access8GraphAppService(
        hotkey_capture=hotkey_capture,
        input_capture=input_capture,
        outputs=OutputCapabilities(speech=output_service, tone=tone_output),
        main_thread_dispatch=getattr(Access8GraphApp, "dispatch", None),
    )
    input_service = KeyboardInputService(input_capture, app_service)
    app_service.attach_input_service(input_service)
    app_service.bind()
    hotkey_capture.start()
    app = Access8GraphApp(controller=app_service)
    return Access8GraphRuntime(
        input_capture=input_capture,
        hotkey_capture=hotkey_capture,
        tone_output=tone_output,
        speech_scheduler=speech_scheduler,
        speech_service=speech_service,
        output_service=output_service,
        input_service=input_service,
        app_service=app_service,
        app=app,
    )


def main() -> int:
    try:
        configure_logging(app_name="access8graph")
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
