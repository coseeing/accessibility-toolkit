from dataclasses import dataclass
import logging
from typing import Any

from adapters.inputs.base import HotkeyCapture, InputCapture
from application.keyboard import KeyboardInputService
from application.output import Scheduler
from application.output import QueuedService
from application.output.speech import SpeechService
from apps.access8graph.service import Access8GraphAppService
from bootstrap.app_runtime import build_app_runtime_parts
from bootstrap.runtime import configure_logging


@dataclass(frozen=True)
class Access8GraphRuntime:
    input_capture: InputCapture
    hotkey_capture: HotkeyCapture
    tone_output: object
    scheduler: Scheduler
    speech: SpeechService
    speaker: QueuedService
    input_service: KeyboardInputService
    app_service: Access8GraphAppService
    app: Any


def build_runtime() -> Access8GraphRuntime:
    from ui.access8graph.app import Access8GraphApp

    parts = build_app_runtime_parts(
        hotkey_usage=Access8GraphAppService.enter_usage,
    )
    app_service = Access8GraphAppService(
        hotkey_capture=parts.hotkey_capture,
        input_capture=parts.input_capture,
        capabilities=parts.output.capabilities,
        main_thread_dispatch=getattr(Access8GraphApp, "dispatch", None),
    )
    input_service = KeyboardInputService(parts.input_capture, app_service)
    app_service.attach_input_service(input_service)
    app_service.bind()
    parts.hotkey_capture.start()
    app = Access8GraphApp(controller=app_service)
    return Access8GraphRuntime(
        input_capture=parts.input_capture,
        hotkey_capture=parts.hotkey_capture,
        tone_output=parts.tone_output,
        scheduler=parts.output.scheduler,
        speech=parts.output.speech,
        speaker=parts.output.speaker,
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
