from dataclasses import dataclass
import logging
import os
from adapters.inputs.base import HotkeyCapture, InputCapture
from application.config import SpeechBackendConfigStore
from application.keyboard import KeyboardInputService
from application.output import Scheduler
from application.output import QueuedService
from application.output import ClipboardService
from application.output.speech import SpeechService
from apps.nvda_remote.service import NvdaRemoteAppService
from bootstrap.app_runtime import build_app_runtime_parts
from bootstrap.platform import PlatformProvider
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
    tone_output: object
    scheduler: Scheduler
    speech: SpeechService
    speaker: QueuedService
    input_service: KeyboardInputService
    app_service: NvdaRemoteAppService
    app: NvdaRemoteApp


def _use_windows_native_key_payload() -> bool:
    return os.getenv("NVDA_REMOTE_USE_WINDOWS_NATIVE_KEY_PAYLOAD", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def build_runtime() -> NvdaRemoteRuntime:
    config_store = SpeechBackendConfigStore(default_config_path())
    provider = PlatformProvider()
    default_bid = provider.default_speech_backend_id()
    selected_backend_id = config_store.load_backend_id(
        default_backend_id=default_bid
    )
    parts = build_app_runtime_parts(
        provider=provider,
        hotkey_usage=NvdaRemoteAppService.enter_usage,
        selected_backend_id=selected_backend_id,
        fallback_backend_id=default_bid,
        on_backend_fallback=config_store.save_backend_id,
        include_clipboard=True,
    )

    transport = RelayTransport(JSONSerializer())
    app_service = NvdaRemoteAppService(
        transport=transport,
        input_capture=parts.input_capture,
        hotkey_capture=parts.hotkey_capture,
        clipboard=parts.clipboard,
        capabilities=parts.output.capabilities,
        on_speech_backend_changed=config_store.save_backend_id,
        main_thread_dispatch=getattr(NvdaRemoteApp, "dispatch", None),
        use_windows_native_key_payload=_use_windows_native_key_payload(),
    )
    input_service = KeyboardInputService(parts.input_capture, app_service)
    app_service.bind()
    input_service.bind()
    app = NvdaRemoteApp(controller=app_service)
    return NvdaRemoteRuntime(
        config_store=config_store,
        transport=transport,
        input_capture=parts.input_capture,
        hotkey_capture=parts.hotkey_capture,
        clipboard=parts.clipboard,
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
        configure_logging(app_name="nvda_remote")
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
