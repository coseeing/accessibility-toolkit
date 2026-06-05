from dataclasses import dataclass
import logging
from pathlib import Path
import sys

from adapters.outputs.drivers.pyttsx3 import Pyttsx3SpeechOutput
from adapters.windows.clipboard import WindowsClipboardService
from adapters.windows.hotkey import WindowsHotkeyCapture
from adapters.windows.keyboard_hook import WindowsKeyboardCapture
from adapters.windows.nvda_controller import NvdaControllerSpeechOutput
from application.config import SpeechBackendConfigStore
from application.keyboard import KeyboardInputService
from application.speech_backends import SpeechBackendOption
from application.speech_service import SpeechService
from apps.nvda_remote.service import NvdaRemoteAppService
from remote_core.serializer import JSONSerializer
from remote_core.transport.relay import RelayTransport
from ui.app import NvdaRemoteApp


@dataclass(frozen=True)
class NvdaRemoteRuntime:
    config_store: SpeechBackendConfigStore
    transport: RelayTransport
    input_capture: WindowsKeyboardCapture
    hotkey_capture: WindowsHotkeyCapture
    clipboard: WindowsClipboardService
    speech_service: SpeechService
    input_service: KeyboardInputService
    app_service: NvdaRemoteAppService
    app: NvdaRemoteApp


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def default_log_path() -> Path:
    if _is_frozen():
        return Path(sys.executable).resolve().parent / "nvda-remote-client.log"
    return Path.cwd().resolve() / "nvda-remote-client.log"


def default_config_path() -> Path:
    if _is_frozen():
        return Path(sys.executable).resolve().parent / "nvda-remote-client.json"
    return Path.cwd().resolve() / "nvda-remote-client.json"


def configure_logging() -> Path:
    log_path = default_log_path()
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        filename=log_path,
        filemode="a",
        force=True,
    )
    logging.getLogger(__name__).info("Logging initialized at %s", log_path)
    return log_path


def _default_backend_options() -> tuple[SpeechBackendOption, ...]:
    return (
        SpeechBackendOption(
            backend_id="nvda_controller",
            label="NVDA Controller",
            factory=NvdaControllerSpeechOutput.load_default,
        ),
        SpeechBackendOption(
            backend_id="pyttsx3",
            label="pyttsx3",
            factory=Pyttsx3SpeechOutput.load_default,
        ),
    )


def build_runtime() -> NvdaRemoteRuntime:
    config_store = SpeechBackendConfigStore(default_config_path())
    backend_options = _default_backend_options()
    selected_backend_id = config_store.load_backend_id(
        default_backend_id="nvda_controller"
    )
    try:
        speech_service = SpeechService(
            backend_options=backend_options,
            selected_backend_id=selected_backend_id,
        )
    except ValueError:
        logging.getLogger(__name__).warning(
            "Unknown configured speech backend %r; falling back to nvda_controller",
            selected_backend_id,
        )
        speech_service = SpeechService(
            backend_options=backend_options,
            selected_backend_id="nvda_controller",
        )
        config_store.save_backend_id("nvda_controller")

    transport = RelayTransport(JSONSerializer())
    input_capture = WindowsKeyboardCapture()
    hotkey_capture = WindowsHotkeyCapture()
    clipboard = WindowsClipboardService()
    app_service = NvdaRemoteAppService(
        transport=transport,
        input_capture=input_capture,
        hotkey_capture=hotkey_capture,
        clipboard=clipboard,
        speech=speech_service,
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
        speech_service=speech_service,
        input_service=input_service,
        app_service=app_service,
        app=app,
    )


def main() -> int:
    configure_logging()
    runtime = build_runtime()
    return runtime.app.MainLoop()


if __name__ == "__main__":
    raise SystemExit(main())
