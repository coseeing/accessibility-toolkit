from dataclasses import dataclass
import logging
from typing import Any

from adapters.inputs.base import HotkeyCapture, InputCapture
from application.config import SpeechEngineConfigStore
from application.keyboard import KeyboardInputService
from application.output import Scheduler
from application.output import QueuedService
from application.output.speech import SpeechService
from apps.key_echo.service import KeyEchoAppService
from bootstrap.app_runtime import build_app_runtime_parts
from bootstrap.runtime import configure_logging, default_config_path


@dataclass(frozen=True)
class KeyEchoRuntime:
    config_store: SpeechEngineConfigStore
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

    config_store = SpeechEngineConfigStore(default_config_path())
    parts = build_app_runtime_parts(
        hotkey_usage=KeyEchoAppService.enter_usage,
        selected_engine_id="Pyttsx3",
        fallback_engine_id="Pyttsx3",
        include_tone=False,
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

    _apply_saved_speech_settings(parts.output.speech, "Pyttsx3")

    def _on_speech_engine_changed(engine_id: str) -> None:
        config_store.save_engine_id(engine_id)
        _apply_saved_speech_settings(parts.output.speech, engine_id)

    app_service = KeyEchoAppService(
        hotkey_capture=parts.hotkey_capture,
        input_capture=parts.input_capture,
        capabilities=parts.output.capabilities,
        on_speech_engine_changed=_on_speech_engine_changed,
        on_voice_changed=config_store.save_voice,
        on_numeric_setting_changed=config_store.save_numeric_setting,
        main_thread_dispatch=getattr(EchoApp, "dispatch", None),
    )
    input_service = KeyboardInputService(parts.input_capture, app_service)
    app_service.attach_input_service(input_service)
    app_service.bind()
    parts.hotkey_capture.start()
    app = EchoApp(controller=app_service)
    return KeyEchoRuntime(
        config_store=config_store,
        input_capture=parts.input_capture,
        hotkey_capture=parts.hotkey_capture,
        scheduler=parts.output.scheduler,
        speech=parts.output.speech,
        speaker=parts.output.speaker,
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
