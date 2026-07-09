from dataclasses import dataclass
import logging
from typing import Any

from accessibility_toolkit.adapters.inputs.base import HotkeyCapture, InputCapture
from accessibility_toolkit.adapters.config.json_speech_settings import JsonSpeechSettingsStore
from accessibility_toolkit.application.input import KeyboardInputService
from accessibility_toolkit.application.output import Scheduler
from accessibility_toolkit.application.output import QueuedService
from accessibility_toolkit.application.output.speech import SpeechService
from apps.key_echo.service import KeyEchoAppService
from accessibility_toolkit.application_support.speech_runtime_settings import SpeechRuntimeSettingsCoordinator
from accessibility_toolkit.application_support.speech_settings_facade import SpeechSettingsFacade
from accessibility_toolkit.runtime.runtime_parts import build_app_runtime_parts
from accessibility_toolkit.runtime.environment import configure_logging, default_config_path


@dataclass(frozen=True)
class KeyEchoRuntime:
    config_store: JsonSpeechSettingsStore
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

    config_store = JsonSpeechSettingsStore(default_config_path())
    coordinator = SpeechRuntimeSettingsCoordinator(config_store=config_store)
    parts = build_app_runtime_parts(
        hotkey_usage=KeyEchoAppService.enter_usage,
        selected_engine_id="Pyttsx3",
        fallback_engine_id="Pyttsx3",
        include_tone=False,
    )
    coordinator.apply_saved_settings(speech=parts.output.speech, engine_id="Pyttsx3")
    on_speech_engine_changed = coordinator.build_engine_change_callback(
        speech=parts.output.speech,
    )
    app_service = KeyEchoAppService(
        hotkey_capture=parts.hotkey_capture,
        input_capture=parts.input_capture,
        capabilities=parts.output.capabilities,
        main_thread_dispatch=getattr(EchoApp, "dispatch", None),
    )
    input_service = KeyboardInputService(parts.input_capture, app_service)
    app_service.attach_input_service(input_service)
    app_service.bind()
    parts.hotkey_capture.start()

    def _on_engine_changed(engine_id: str) -> None:
        on_speech_engine_changed(engine_id)
        app_service.notify_speech_engine_changed(engine_id)

    speech_settings = SpeechSettingsFacade(
        speech=parts.output.speech,
        on_engine_changed=_on_engine_changed,
        on_voice_changed=config_store.save_voice,
        on_numeric_setting_changed=config_store.save_numeric_setting,
    )
    app = EchoApp(
        controller=app_service,
        speech_controller=speech_settings,
    )
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
