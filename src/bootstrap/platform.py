import importlib
import logging
import sys
from dataclasses import dataclass
from typing import Any

from adapters.inputs.base import HotkeyCapture, InputCapture
from adapters.outputs.drivers.pyttsx3 import Pyttsx3SpeechOutput
from adapters.outputs.tone import DefaultToneOutput
from application.output import Scheduler
from application.output import ClipboardService
from application.output.speech import SpeechBackendOption
from interop.key import HID

_logger = logging.getLogger(__name__)

# --- lazy import cache variables ---
_WindowsKeyboardCapture: Any = None
_WindowsHotkeyCapture: Any = None
_WindowsClipboardService: Any = None
_NvdaControllerSpeechOutput: Any = None
_AccessibilityPermissions: Any = None
_MacOSEventTapManager: Any = None
_MacOSEventTapBackend: Any = None
_MacOSKeyboardCapture: Any = None
_MacOSHotkeyCapture: Any = None
_macos_event_tap_manager_instance: Any = None

_DEFAULT_HOTKEY_USAGE = HID.F11

_MACOS_HOTKEY_KEY_CODES: dict[int, int] = {
    HID.F11: 103,
    HID.F10: 109,
    HID.ENTER: 36,
}


@dataclass(frozen=True)
class PlatformServices:
    input_capture: InputCapture
    hotkey_capture: HotkeyCapture
    clipboard: ClipboardService
    tone_output: DefaultToneOutput


# --- null / fallback implementations ---

class _NullInputCapture:
    @property
    def running(self) -> bool:
        return False

    def set_listener(self, listener: Any) -> None:
        del listener

    def start(self) -> None:
        _logger.warning("InputCapture is not supported on this platform")

    def stop(self) -> None:
        pass


class _NullHotkeyCapture:
    @property
    def running(self) -> bool:
        return False

    def set_handler(self, handler: Any) -> None:
        del handler

    def start(self) -> None:
        _logger.warning("HotkeyCapture is not supported on this platform")

    def stop(self) -> None:
        pass


class _UnsupportedClipboardService:
    supported = False

    def set_text(self, text: str) -> None:
        del text

    def get_text(self) -> str:
        return ""


class _UnavailableMacOSPermissions:
    def is_trusted(self, *, prompt: bool = False) -> bool:
        del prompt
        raise RuntimeError("macOS accessibility permission wiring is unavailable")

    def has_listen_event_access(self, *, prompt: bool = False) -> bool:
        del prompt
        raise RuntimeError("macOS input monitoring permission wiring is unavailable")


# --- Windows lazy helpers ---

def _get_windows_keyboard_capture_class() -> Any:
    global _WindowsKeyboardCapture
    if _WindowsKeyboardCapture is None:
        from adapters.windows.keyboard_hook import WindowsKeyboardCapture as Capture
        _WindowsKeyboardCapture = Capture
    return _WindowsKeyboardCapture


def _get_windows_hotkey_capture_class() -> Any:
    global _WindowsHotkeyCapture
    if _WindowsHotkeyCapture is None:
        from adapters.windows.hotkey import WindowsHotkeyCapture as Capture
        _WindowsHotkeyCapture = Capture
    return _WindowsHotkeyCapture


def _get_windows_clipboard_service_class() -> Any:
    global _WindowsClipboardService
    if _WindowsClipboardService is None:
        from adapters.windows.clipboard import WindowsClipboardService as Service
        _WindowsClipboardService = Service
    return _WindowsClipboardService


def _get_nvda_controller_speech_output_class() -> Any:
    global _NvdaControllerSpeechOutput
    if _NvdaControllerSpeechOutput is None:
        from adapters.windows.nvda_controller import NvdaControllerSpeechOutput as Output
        _NvdaControllerSpeechOutput = Output
    return _NvdaControllerSpeechOutput


# --- macOS lazy helpers ---

def _get_macos_permissions_type() -> Any:
    global _AccessibilityPermissions
    if _AccessibilityPermissions is None:
        module = importlib.import_module("adapters.macos.permissions")
        _AccessibilityPermissions = module.AccessibilityPermissions
    return _AccessibilityPermissions


def _load_macos_permissions() -> Any:
    permissions_type = _get_macos_permissions_type()
    load_default = getattr(permissions_type, "load_default", None)
    if callable(load_default):
        return load_default()
    return _UnavailableMacOSPermissions()


def _load_macos_event_tap_backend() -> Any:
    global _MacOSEventTapBackend
    _load_macos_input_components()
    return _MacOSEventTapBackend()


def _load_macos_input_components() -> None:
    global _MacOSEventTapManager
    global _MacOSEventTapBackend
    global _MacOSKeyboardCapture
    global _MacOSHotkeyCapture
    if (
        _MacOSEventTapManager is not None
        and _MacOSEventTapBackend is not None
        and _MacOSKeyboardCapture is not None
        and _MacOSHotkeyCapture is not None
    ):
        return
    try:
        event_tap = importlib.import_module("adapters.macos.event_tap")
        hotkey = importlib.import_module("adapters.macos.hotkey")
        keyboard_hook = importlib.import_module("adapters.macos.keyboard_hook")
    except ImportError as error:
        raise RuntimeError("macOS input capture dependencies are unavailable") from error
    _MacOSEventTapManager = event_tap.MacOSEventTapManager
    _MacOSEventTapBackend = event_tap.QuartzEventTapBackend
    _MacOSKeyboardCapture = keyboard_hook.MacOSKeyboardCapture
    _MacOSHotkeyCapture = hotkey.MacOSHotkeyCapture


def _ensure_macos_event_tap_manager() -> Any:
    global _macos_event_tap_manager_instance
    if _macos_event_tap_manager_instance is None:
        _load_macos_input_components()
        _macos_event_tap_manager_instance = _MacOSEventTapManager(
            permissions=_load_macos_permissions(),
            backend=_load_macos_event_tap_backend(),
        )
    return _macos_event_tap_manager_instance


# --- public factory functions ---

def create_input_capture() -> InputCapture:
    if sys.platform == "darwin":
        manager = _ensure_macos_event_tap_manager()
        return _MacOSKeyboardCapture(manager=manager)
    if sys.platform == "win32":
        return _get_windows_keyboard_capture_class()()
    return _NullInputCapture()


def create_hotkey_capture(usage: int = _DEFAULT_HOTKEY_USAGE) -> HotkeyCapture:
    if sys.platform == "darwin":
        manager = _ensure_macos_event_tap_manager()
        key_code = _MACOS_HOTKEY_KEY_CODES.get(usage)
        if key_code is None:
            raise ValueError(f"Unsupported macOS hotkey usage: 0x{usage:02X}")
        return _MacOSHotkeyCapture(manager=manager, key_code=key_code)
    if sys.platform == "win32":
        if usage <= 0:
            raise ValueError(f"Unsupported Windows hotkey usage: 0x{usage:02X}")
        return _get_windows_hotkey_capture_class()(usage=usage, label=f"HID_0x{usage:02X}")
    return _NullHotkeyCapture()


def create_clipboard_service() -> ClipboardService:
    if sys.platform == "win32":
        return _get_windows_clipboard_service_class()()
    return _UnsupportedClipboardService()


def create_tone_output() -> DefaultToneOutput:
    return DefaultToneOutput.load_default()


def default_speech_backend_options(
    scheduler: Scheduler,
) -> tuple[SpeechBackendOption, ...]:
    options = [
        SpeechBackendOption(
            backend_id="pyttsx3",
            label="pyttsx3",
            factory=lambda: Pyttsx3SpeechOutput.load_default(scheduler=scheduler),
        ),
    ]
    if sys.platform == "win32":
        options.insert(
            0,
            SpeechBackendOption(
                backend_id="nvda_controller",
                label="NVDA Controller",
                factory=lambda: _get_nvda_controller_speech_output_class().load_default(
                    scheduler=scheduler
                ),
            ),
        )
    return tuple(options)


def default_speech_backend_id() -> str:
    return "nvda_controller" if sys.platform == "win32" else "pyttsx3"


class PlatformProvider:
    def create_input_capture(self) -> InputCapture:
        return create_input_capture()

    def create_hotkey_capture(
        self, usage: int = _DEFAULT_HOTKEY_USAGE
    ) -> HotkeyCapture:
        return create_hotkey_capture(usage)

    def create_clipboard_service(self) -> ClipboardService:
        return create_clipboard_service()

    def create_tone_output(self) -> DefaultToneOutput:
        return create_tone_output()

    def default_speech_backend_options(
        self, scheduler: Scheduler
    ) -> tuple[SpeechBackendOption, ...]:
        return default_speech_backend_options(scheduler)

    def default_speech_backend_id(self) -> str:
        return default_speech_backend_id()

    def build_services(
        self, hotkey_usage: int = _DEFAULT_HOTKEY_USAGE
    ) -> PlatformServices:
        return PlatformServices(
            input_capture=self.create_input_capture(),
            hotkey_capture=self.create_hotkey_capture(hotkey_usage),
            clipboard=self.create_clipboard_service(),
            tone_output=self.create_tone_output(),
        )
