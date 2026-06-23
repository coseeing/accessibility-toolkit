from collections.abc import Callable
from dataclasses import dataclass

from adapters.inputs.base import HotkeyCapture, InputCapture
from adapters.outputs.interfaces import ToneOutput
from application.output import ClipboardService
from bootstrap.output import OutputServices, build_output_services
from bootstrap.platform import PlatformProvider


@dataclass(frozen=True)
class AppRuntimeParts:
    input_capture: InputCapture
    hotkey_capture: HotkeyCapture
    clipboard: ClipboardService | None
    tone_output: ToneOutput | None
    output: OutputServices


def build_app_runtime_parts(
    *,
    hotkey_usage: int,
    provider: PlatformProvider | None = None,
    selected_backend_id: str | None = None,
    fallback_backend_id: str | None = None,
    on_backend_fallback: Callable[[str], None] | None = None,
    include_clipboard: bool = False,
    include_tone: bool = True,
) -> AppRuntimeParts:
    provider = provider or PlatformProvider()
    input_capture = provider.create_input_capture()
    hotkey_capture = provider.create_hotkey_capture(hotkey_usage)
    clipboard = provider.create_clipboard_service() if include_clipboard else None
    tone_output = provider.create_tone_output() if include_tone else None
    default_backend_id = provider.default_speech_backend_id()
    output = build_output_services(
        backend_options_factory=provider.default_speech_backend_options,
        selected_backend_id=selected_backend_id or default_backend_id,
        fallback_backend_id=fallback_backend_id,
        tone_output=tone_output,
        on_backend_fallback=on_backend_fallback,
    )
    return AppRuntimeParts(
        input_capture=input_capture,
        hotkey_capture=hotkey_capture,
        clipboard=clipboard,
        tone_output=tone_output,
        output=output,
    )
