from dataclasses import dataclass
import logging
import os
from adapters.inputs.base import HotkeyCapture, InputCapture
from application.config import SpeechEngineConfigStore
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
    config_store: SpeechEngineConfigStore
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
    config_store = SpeechEngineConfigStore(default_config_path())
    provider = PlatformProvider()
    default_engine_id = provider.default_speech_engine_id()
    selected_engine_id = config_store.load_engine_id(
        default_engine_id=default_engine_id
    )
    parts = build_app_runtime_parts(
        provider=provider,
        hotkey_usage=NvdaRemoteAppService.enter_usage,
        selected_engine_id=selected_engine_id,
        fallback_engine_id=default_engine_id,
        on_engine_fallback=config_store.save_engine_id,
        include_clipboard=True,
    )

    def _apply_saved_speech_settings(speech: SpeechService, engine_id: str) -> None:
        voice_id = config_store.load_voice(engine_id)
        available_voice_ids = {voice for voice, _label in speech.list_voices()}
        if voice_id is not None and voice_id in available_voice_ids:
            speech.set_voice(voice_id)
        supported_settings = {
            setting.id for setting in speech.get_supported_numeric_settings()
        }
        for setting_id, setter in (
            ("rate", speech.set_rate),
            ("pitch", speech.set_pitch),
            ("volume", speech.set_volume),
        ):
            value = config_store.load_numeric_setting(engine_id, setting_id)
            if value is not None and setting_id in supported_settings:
                setter(value)

    selected_runtime_engine_id = parts.output.speech.get_selected_engine()
    _apply_saved_speech_settings(parts.output.speech, selected_runtime_engine_id)

    def _on_speech_engine_changed(engine_id: str) -> None:
        config_store.save_engine_id(engine_id)
        _apply_saved_speech_settings(parts.output.speech, engine_id)

    transport = RelayTransport(JSONSerializer())
    app_service = NvdaRemoteAppService(
        transport=transport,
        input_capture=parts.input_capture,
        hotkey_capture=parts.hotkey_capture,
        clipboard=parts.clipboard,
        capabilities=parts.output.capabilities,
        on_speech_engine_changed=_on_speech_engine_changed,
        on_voice_changed=config_store.save_voice,
        on_numeric_setting_changed=config_store.save_numeric_setting,
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
