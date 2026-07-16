import logging
import sys
from dataclasses import dataclass
from typing import Any

from accessibility_toolkit.input.capture import HotkeyCapture, InputCapture
from accessibility_toolkit.input import HID
from accessibility_toolkit.output import ClipboardService, ToneOutput, WaveOutput
from accessibility_toolkit.output.speech import SpeechEngineOption
from accessibility_toolkit.scheduling import Scheduler

_logger = logging.getLogger(__name__)

# --- lazy import cache variables ---
_DefaultToneOutput: Any = None
_DefaultWaveOutput: Any = None
_Pyttsx3SpeechOutput: Any = None
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
    tone_output: ToneOutput
    wave_output: WaveOutput | None = None


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


# --- output implementation lazy helpers ---

def _get_default_tone_output_class() -> Any:
    global _DefaultToneOutput
    if _DefaultToneOutput is None:
        from accessibility_toolkit.output.tone import DefaultToneOutput as Output

        _DefaultToneOutput = Output
    return _DefaultToneOutput


def _get_default_wave_output_class() -> Any:
    global _DefaultWaveOutput
    if _DefaultWaveOutput is None:
        from accessibility_toolkit.output.wave import DefaultWaveOutput as Output

        _DefaultWaveOutput = Output
    return _DefaultWaveOutput


def _get_pyttsx3_speech_output_class() -> Any:
    global _Pyttsx3SpeechOutput
    if _Pyttsx3SpeechOutput is None:
        from accessibility_toolkit.output.speech.drivers.pyttsx3 import (
            Pyttsx3SpeechOutput as Output,
        )

        _Pyttsx3SpeechOutput = Output
    return _Pyttsx3SpeechOutput


# --- Windows lazy helpers ---

def _get_windows_keyboard_capture_class() -> Any:
    global _WindowsKeyboardCapture
    if _WindowsKeyboardCapture is None:
        from accessibility_toolkit.input.windows.keyboard_hook import WindowsKeyboardCapture as Capture
        _WindowsKeyboardCapture = Capture
    return _WindowsKeyboardCapture


def _get_windows_hotkey_capture_class() -> Any:
    global _WindowsHotkeyCapture
    if _WindowsHotkeyCapture is None:
        from accessibility_toolkit.input.windows.hotkey import WindowsHotkeyCapture as Capture
        _WindowsHotkeyCapture = Capture
    return _WindowsHotkeyCapture


def _get_windows_clipboard_service_class() -> Any:
    global _WindowsClipboardService
    if _WindowsClipboardService is None:
        from accessibility_toolkit.output.windows.clipboard import (
            WindowsClipboardService as Service,
        )
        _WindowsClipboardService = Service
    return _WindowsClipboardService


def _get_nvda_controller_speech_output_class() -> Any:
    global _NvdaControllerSpeechOutput
    if _NvdaControllerSpeechOutput is None:
        from accessibility_toolkit.output.speech.windows.nvda_controller import (
            NvdaControllerSpeechOutput as Output,
        )
        _NvdaControllerSpeechOutput = Output
    return _NvdaControllerSpeechOutput


# --- macOS lazy helpers ---

def _get_macos_permissions_type() -> Any:
    global _AccessibilityPermissions
    if _AccessibilityPermissions is None:
        from accessibility_toolkit.input.macos.permissions import AccessibilityPermissions

        _AccessibilityPermissions = AccessibilityPermissions
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
        from accessibility_toolkit.input.macos.event_tap import (
            MacOSEventTapManager,
            QuartzEventTapBackend,
        )
        from accessibility_toolkit.input.macos.hotkey import MacOSHotkeyCapture
        from accessibility_toolkit.input.macos.keyboard_hook import MacOSKeyboardCapture
    except ImportError as error:
        raise RuntimeError("macOS input capture dependencies are unavailable") from error
    _MacOSEventTapManager = MacOSEventTapManager
    _MacOSEventTapBackend = QuartzEventTapBackend
    _MacOSKeyboardCapture = MacOSKeyboardCapture
    _MacOSHotkeyCapture = MacOSHotkeyCapture


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


def create_tone_output() -> ToneOutput:
    return _get_default_tone_output_class().load_default()


def create_wave_output() -> WaveOutput:
    return _get_default_wave_output_class().load_default()


def default_speech_engine_options(
    scheduler: Scheduler,
) -> tuple[SpeechEngineOption, ...]:
    options = [
        SpeechEngineOption(
            engine_id="Pyttsx3",
            label="Pyttsx3",
            factory=lambda: _get_pyttsx3_speech_output_class().load_default(
                scheduler=scheduler
            ),
        ),
    ]
    if sys.platform == "win32":
        options.insert(
            0,
            SpeechEngineOption(
                engine_id="NvdaController",
                label="Nvda Controller",
                factory=lambda: _get_nvda_controller_speech_output_class().load_default(
                    scheduler=scheduler
                ),
            ),
        )
    return tuple(options)


def default_speech_engine_id() -> str:
    return "NvdaController" if sys.platform == "win32" else "Pyttsx3"


class PlatformProvider:
    def create_input_capture(self) -> InputCapture:
        return create_input_capture()

    def create_hotkey_capture(
        self, usage: int = _DEFAULT_HOTKEY_USAGE
    ) -> HotkeyCapture:
        return create_hotkey_capture(usage)

    def create_clipboard_service(self) -> ClipboardService:
        return create_clipboard_service()

    def create_tone_output(self) -> ToneOutput:
        return create_tone_output()

    def create_wave_output(self) -> WaveOutput:
        return create_wave_output()

    def default_speech_engine_options(
        self, scheduler: Scheduler
    ) -> tuple[SpeechEngineOption, ...]:
        return default_speech_engine_options(scheduler)

    def default_speech_engine_id(self) -> str:
        return default_speech_engine_id()

    def build_services(
        self, hotkey_usage: int = _DEFAULT_HOTKEY_USAGE
    ) -> PlatformServices:
        return PlatformServices(
            input_capture=self.create_input_capture(),
            hotkey_capture=self.create_hotkey_capture(hotkey_usage),
            clipboard=self.create_clipboard_service(),
            tone_output=self.create_tone_output(),
            wave_output=self.create_wave_output(),
        )
