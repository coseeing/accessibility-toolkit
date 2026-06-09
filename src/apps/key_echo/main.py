from dataclasses import dataclass
import importlib
import sys
from typing import Any

from adapters.outputs.drivers.pyttsx3 import Pyttsx3SpeechOutput
from application.keyboard import KeyboardInputService
from application.output_capabilities import OutputCapabilities
from application.output_scheduler import OutputScheduler
from application.output_service import QueuedOutputService
from application.speech_backends import SpeechBackendOption
from application.speech_service import SpeechService
from apps.key_echo.service import KeyEchoAppService

WindowsKeyboardCapture = None
NvdaControllerSpeechOutput = None
MacOSEventTapManager = None
MacOSEventTapBackend = None
MacOSKeyboardCapture = None
AccessibilityPermissions = None


@dataclass(frozen=True)
class KeyEchoRuntime:
    capture: Any
    output_scheduler: OutputScheduler
    speech_service: SpeechService
    output_service: QueuedOutputService
    input_service: KeyboardInputService
    app_service: KeyEchoAppService
    app: Any


def build_runtime() -> KeyEchoRuntime:
    from ui.echo.app import EchoApp

    if sys.platform == "darwin":
        manager = _build_macos_event_tap_manager()
        capture = MacOSKeyboardCapture(manager=manager)
    else:
        capture = _get_windows_keyboard_capture_class()()
    output_scheduler = OutputScheduler()
    speech_service = SpeechService(
        backend_options=_default_backend_options(output_scheduler),
        selected_backend_id="pyttsx3",
    )
    output_service = QueuedOutputService(
        speech=speech_service,
        scheduler=output_scheduler,
    )
    app_service = KeyEchoAppService(
        outputs=OutputCapabilities(speech=output_service),
    )
    input_service = KeyboardInputService(capture, app_service)
    input_service.bind()
    app_service.attach_input_service(input_service)
    app = EchoApp(controller=app_service)
    return KeyEchoRuntime(
        capture=capture,
        output_scheduler=output_scheduler,
        speech_service=speech_service,
        output_service=output_service,
        input_service=input_service,
        app_service=app_service,
        app=app,
    )


def _default_backend_options(
    output_scheduler: OutputScheduler,
) -> tuple[SpeechBackendOption, ...]:
    options = [
        SpeechBackendOption(
            backend_id="pyttsx3",
            label="pyttsx3",
            factory=lambda: Pyttsx3SpeechOutput.load_default(
                scheduler=output_scheduler
            ),
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
    raise RuntimeError("macOS accessibility permission wiring is unavailable")


def _load_macos_event_tap_backend() -> Any:
    _load_macos_input_components()
    return MacOSEventTapBackend()


def _get_windows_keyboard_capture_class() -> Any:
    global WindowsKeyboardCapture
    if WindowsKeyboardCapture is None:
        from adapters.windows.keyboard_hook import WindowsKeyboardCapture as Capture

        WindowsKeyboardCapture = Capture
    return WindowsKeyboardCapture


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
    if (
        MacOSEventTapManager is not None
        and MacOSEventTapBackend is not None
        and MacOSKeyboardCapture is not None
    ):
        return
    try:
        event_tap = importlib.import_module("adapters.macos.event_tap")
        keyboard_hook = importlib.import_module("adapters.macos.keyboard_hook")
    except ImportError as error:
        raise RuntimeError("macOS input capture dependencies are unavailable") from error
    MacOSEventTapManager = event_tap.MacOSEventTapManager
    MacOSEventTapBackend = event_tap.QuartzEventTapBackend
    MacOSKeyboardCapture = keyboard_hook.MacOSKeyboardCapture


def main() -> int:
    runtime = build_runtime()
    return runtime.app.MainLoop()


if __name__ == "__main__":
    raise SystemExit(main())
