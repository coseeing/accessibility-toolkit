from dataclasses import dataclass
import importlib
import logging
from pathlib import Path
import sys
from typing import Any

from adapters.inputs.base import HotkeyCapture, InputCapture
from adapters.outputs.drivers.pyttsx3 import Pyttsx3SpeechOutput
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

AccessibilityPermissions = None
WindowsClipboardService = None
WindowsHotkeyCapture = None
WindowsKeyboardCapture = None
NvdaControllerSpeechOutput = None
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
    options = [
        SpeechBackendOption(
            backend_id="pyttsx3",
            label="pyttsx3",
            factory=lambda: Pyttsx3SpeechOutput.load_default(scheduler=output_scheduler),
        ),
    ]
    if sys.platform == "win32":
        options.insert(
            0,
            SpeechBackendOption(
                backend_id="nvda_controller",
                label="NVDA Controller",
                factory=lambda: _get_nvda_controller_speech_output_class().load_default(
                    scheduler=output_scheduler
                ),
            ),
        )
    return tuple(options)


class _UnavailableMacOSPermissions:
    def is_trusted(self, *, prompt: bool = False) -> bool:
        del prompt
        raise RuntimeError("macOS accessibility permission wiring is unavailable")

    def has_listen_event_access(self, *, prompt: bool = False) -> bool:
        del prompt
        raise RuntimeError("macOS input monitoring permission wiring is unavailable")


class _UnsupportedClipboardService:
    """Safe clipboard fallback for platforms without an implemented adapter."""

    supported = False

    def set_text(self, text: str) -> None:
        del text

    def get_text(self) -> str:
        return ""


def _build_macos_event_tap_manager() -> Any:
    _load_macos_input_components()
    return MacOSEventTapManager(
        permissions=_load_macos_permissions(),
        backend=_load_macos_event_tap_backend(),
    )


def _load_macos_permissions() -> Any:
    permissions_type = _get_macos_permissions_type()
    load_default = getattr(permissions_type, "load_default", None)
    if callable(load_default):
        return load_default()
    return _UnavailableMacOSPermissions()


def _load_macos_event_tap_backend() -> Any:
    _load_macos_input_components()
    return MacOSEventTapBackend()


def _build_input_adapters() -> tuple[InputCapture, HotkeyCapture]:
    if sys.platform == "darwin":
        manager = _build_macos_event_tap_manager()
        return (
            MacOSKeyboardCapture(manager=manager),
            MacOSHotkeyCapture(manager=manager),
        )
    return _get_windows_keyboard_capture_class()(), _get_windows_hotkey_capture_class()()


def _build_clipboard_service() -> ClipboardService:
    if sys.platform == "win32":
        return _get_windows_clipboard_service_class()()
    return _UnsupportedClipboardService()


def _get_windows_keyboard_capture_class() -> Any:
    global WindowsKeyboardCapture
    if WindowsKeyboardCapture is None:
        from adapters.windows.keyboard_hook import WindowsKeyboardCapture as Capture

        WindowsKeyboardCapture = Capture
    return WindowsKeyboardCapture


def _get_windows_hotkey_capture_class() -> Any:
    global WindowsHotkeyCapture
    if WindowsHotkeyCapture is None:
        from adapters.windows.hotkey import WindowsHotkeyCapture as Capture

        WindowsHotkeyCapture = Capture
    return WindowsHotkeyCapture


def _get_windows_clipboard_service_class() -> Any:
    global WindowsClipboardService
    if WindowsClipboardService is None:
        from adapters.windows.clipboard import WindowsClipboardService as Service

        WindowsClipboardService = Service
    return WindowsClipboardService


def _get_nvda_controller_speech_output_class() -> Any:
    global NvdaControllerSpeechOutput
    if NvdaControllerSpeechOutput is None:
        from adapters.windows.nvda_controller import NvdaControllerSpeechOutput as Output

        NvdaControllerSpeechOutput = Output
    return NvdaControllerSpeechOutput


def _get_macos_permissions_type() -> Any:
    global AccessibilityPermissions
    if AccessibilityPermissions is None:
        module = importlib.import_module("adapters.macos.permissions")
        AccessibilityPermissions = module.AccessibilityPermissions
    return AccessibilityPermissions


def _load_macos_input_components() -> None:
    global MacOSEventTapManager
    global MacOSEventTapBackend
    global MacOSKeyboardCapture
    global MacOSHotkeyCapture
    if (
        MacOSEventTapManager is not None
        and MacOSEventTapBackend is not None
        and MacOSKeyboardCapture is not None
        and MacOSHotkeyCapture is not None
    ):
        return
    try:
        event_tap = importlib.import_module("adapters.macos.event_tap")
        hotkey = importlib.import_module("adapters.macos.hotkey")
        keyboard_hook = importlib.import_module("adapters.macos.keyboard_hook")
    except ImportError as error:  # pragma: no cover - depends on local platform deps
        raise RuntimeError("macOS input capture dependencies are unavailable") from error
    MacOSEventTapManager = event_tap.MacOSEventTapManager
    MacOSEventTapBackend = event_tap.QuartzEventTapBackend
    MacOSKeyboardCapture = keyboard_hook.MacOSKeyboardCapture
    MacOSHotkeyCapture = hotkey.MacOSHotkeyCapture


def build_runtime() -> NvdaRemoteRuntime:
    config_store = SpeechBackendConfigStore(default_config_path())
    output_scheduler = OutputScheduler()
    backend_options = _default_backend_options(output_scheduler)
    default_backend_id = "nvda_controller" if sys.platform == "win32" else "pyttsx3"
    selected_backend_id = config_store.load_backend_id(
        default_backend_id=default_backend_id
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
            selected_backend_id=default_backend_id,
        )
        config_store.save_backend_id(default_backend_id)

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
