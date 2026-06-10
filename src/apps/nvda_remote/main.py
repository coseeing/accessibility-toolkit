from dataclasses import dataclass
import logging
from typing import Any

from adapters.inputs.base import HotkeyCapture, InputCapture
from application.config import SpeechBackendConfigStore
from application.keyboard import KeyboardInputService
from application.output_scheduler import OutputScheduler
from application.output_service import QueuedOutputService
from application.services import ClipboardService
from application.speech_service import SpeechService
from apps.nvda_remote.service import NvdaRemoteAppService
from bootstrap.platform import (
    create_input_capture,
    create_hotkey_capture,
    create_clipboard_service,
    default_speech_backend_options,
    default_speech_backend_id,
)
from bootstrap.runtime import configure_logging, default_config_path
from interop.protocol.serializer import JSONSerializer
from interop.protocol.transport.relay import RelayTransport
from ui.nvda_remote.app import NvdaRemoteApp


@dataclass(frozen=True)
class NvdaRemoteRuntime:
    config_store: SpeechBackendConfigStore
    transport: RelayTransport
    input_capture: InputCapture
    hotkey_capture: HotkeyCapture
    clipboard: ClipboardService
    output_scheduler: OutputScheduler
    speech_service: SpeechService
    output_service: QueuedOutputService
    input_service: KeyboardInputService
    app_service: NvdaRemoteAppService
    app: Any


def build_runtime() -> NvdaRemoteRuntime:
    config_store = SpeechBackendConfigStore(default_config_path())
    output_scheduler = OutputScheduler()
    backend_options = default_speech_backend_options(output_scheduler)
    default_bid = default_speech_backend_id()
    selected_backend_id = config_store.load_backend_id(
        default_backend_id=default_bid
    )
    try:
        speech_service = SpeechService(
            backend_options=backend_options,
            selected_backend_id=selected_backend_id,
        )
    except ValueError:
        logging.getLogger(__name__).warning(
            "Unknown configured speech backend %r; falling back to %s",
            selected_backend_id,
            default_bid,
        )
        speech_service = SpeechService(
            backend_options=backend_options,
            selected_backend_id=default_bid,
        )
        config_store.save_backend_id(default_bid)

    transport = RelayTransport(JSONSerializer())
    input_capture = create_input_capture()
    hotkey_capture = create_hotkey_capture()
    clipboard = create_clipboard_service()
    app_service = NvdaRemoteAppService(
        transport=transport,
        input_capture=input_capture,
        hotkey_capture=hotkey_capture,
        clipboard=clipboard,
        speech=QueuedOutputService(speech=speech_service, scheduler=output_scheduler),
        on_speech_backend_changed=config_store.save_backend_id,
        main_thread_dispatch=getattr(NvdaRemoteApp, "dispatch", None),
    )
    input_service = KeyboardInputService(input_capture, app_service)
    app_service.bind()
    input_service.bind()
    app = NvdaRemoteApp(controller=app_service)
    return NvdaRemoteRuntime(
        config_store=config_store,
        transport=transport,
        input_capture=input_capture,
        hotkey_capture=hotkey_capture,
        clipboard=clipboard,
        output_scheduler=output_scheduler,
        speech_service=speech_service,
        output_service=app_service.speech,
        input_service=input_service,
        app_service=app_service,
        app=app,
    )


def main() -> int:
    try:
        configure_logging(app_name="nvda-remote-client")
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
