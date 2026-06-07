from dataclasses import dataclass
import logging
from pathlib import Path
import sys
from typing import Any

from adapters.inputs.base import HotkeyCapture, InputCapture
from adapters.macos.permissions import AccessibilityPermissions
from adapters.outputs.drivers.pyttsx3 import Pyttsx3SpeechOutput
from adapters.windows.clipboard import WindowsClipboardService
from adapters.windows.hotkey import WindowsHotkeyCapture
from adapters.windows.keyboard_hook import WindowsKeyboardCapture
from adapters.windows.nvda_controller import NvdaControllerSpeechOutput
from application.config import SpeechBackendConfigStore
from application.keyboard import KeyboardInputService
from application.output_scheduler import OutputScheduler
from application.output_service import QueuedOutputService
from application.services import ClipboardService
from application.speech_backends import SpeechBackendOption
from application.speech_service import SpeechService
from apps.nvda_remote.service import NvdaRemoteAppService
from interop.protocol.serializer import JSONSerializer
from interop.protocol.transport.relay import RelayTransport
from ui.nvda_remote.app import NvdaRemoteApp

try:
    from adapters.macos.event_tap import MacOSEventTapManager
    from adapters.macos.event_tap import QuartzEventTapBackend as MacOSEventTapBackend
    from adapters.macos.hotkey import MacOSHotkeyCapture
    from adapters.macos.keyboard_hook import MacOSKeyboardCapture
except ImportError:  # pragma: no cover - non-macOS dependency path
    MacOSEventTapManager = None
    MacOSEventTapBackend = None
    MacOSHotkeyCapture = None
    MacOSKeyboardCapture = None


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
    log_format = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    root_logger = logging.getLogger()
    try:
        if not root_logger.handlers:
            logging.basicConfig(
                level=logging.DEBUG,
                format=log_format,
                filename=log_path,
                filemode="a",
            )
        else:
            file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(log_format))
            root_logger.addHandler(file_handler)
        logging.getLogger(__name__).info("Logging initialized at %s", log_path)
    except OSError as error:
        if not root_logger.handlers:
            logging.basicConfig(
                level=logging.DEBUG,
                format=log_format,
            )
        logging.getLogger(__name__).warning(
            "File logging unavailable at %s: %s",
            log_path,
            error,
        )
    return log_path

def _default_backend_options(
    output_scheduler: OutputScheduler,
) -> tuple[SpeechBackendOption, ...]:
    return (
        SpeechBackendOption(
            backend_id="nvda_controller",
            label="NVDA Controller",
            factory=lambda: NvdaControllerSpeechOutput.load_default(
                scheduler=output_scheduler
            ),
        ),
        SpeechBackendOption(
            backend_id="pyttsx3",
            label="pyttsx3",
            factory=lambda: Pyttsx3SpeechOutput.load_default(scheduler=output_scheduler),
        ),
    )


class _UnavailableMacOSPermissions:
    def is_trusted(self, *, prompt: bool = False) -> bool:
        del prompt
        raise RuntimeError("macOS accessibility permission wiring is unavailable")


class _UnsupportedClipboardService:
    """Safe clipboard fallback for platforms without an implemented adapter."""

    def set_text(self, text: str) -> None:
        del text

    def get_text(self) -> str:
        return ""


def _build_macos_event_tap_manager() -> Any:
    if (
        MacOSEventTapManager is None
        or MacOSEventTapBackend is None
        or MacOSKeyboardCapture is None
        or MacOSHotkeyCapture is None
    ):
        raise RuntimeError("macOS input capture dependencies are unavailable")
    return MacOSEventTapManager(
        permissions=_load_macos_permissions(),
        backend=_load_macos_event_tap_backend(),
    )


def _load_macos_permissions() -> Any:
    load_default = getattr(AccessibilityPermissions, "load_default", None)
    if callable(load_default):
        return load_default()
    return _UnavailableMacOSPermissions()


def _load_macos_event_tap_backend() -> Any:
    if MacOSEventTapBackend is None:
        raise RuntimeError("macOS Quartz event tap backend is unavailable")
    return MacOSEventTapBackend()


def _build_input_adapters() -> tuple[InputCapture, HotkeyCapture]:
    if sys.platform == "darwin":
        manager = _build_macos_event_tap_manager()
        return (
            MacOSKeyboardCapture(manager=manager),
            MacOSHotkeyCapture(manager=manager),
        )
    return WindowsKeyboardCapture(), WindowsHotkeyCapture()


def _build_clipboard_service() -> ClipboardService:
    if sys.platform == "win32":
        return WindowsClipboardService()
    return _UnsupportedClipboardService()


def build_runtime() -> NvdaRemoteRuntime:
    config_store = SpeechBackendConfigStore(default_config_path())
    output_scheduler = OutputScheduler()
    backend_options = _default_backend_options(output_scheduler)
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
    input_capture, hotkey_capture = _build_input_adapters()
    clipboard = _build_clipboard_service()
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
        configure_logging()
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
