from collections.abc import Callable
from dataclasses import dataclass

from accessibility_toolkit.adapters.inputs.base import HotkeyCapture, InputCapture
from accessibility_toolkit.adapters.outputs.interfaces import ToneOutput
from accessibility_toolkit.application.output import ClipboardService
from accessibility_toolkit.runtime.output import OutputServices, build_output_services
from accessibility_toolkit.runtime.platform import PlatformProvider


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
    selected_engine_id: str | None = None,
    fallback_engine_id: str | None = None,
    on_engine_fallback: Callable[[str], None] | None = None,
    include_clipboard: bool = False,
    include_tone: bool = True,
) -> AppRuntimeParts:
    provider = provider or PlatformProvider()
    input_capture = provider.create_input_capture()
    hotkey_capture = provider.create_hotkey_capture(hotkey_usage)
    clipboard = provider.create_clipboard_service() if include_clipboard else None
    tone_output = provider.create_tone_output() if include_tone else None
    default_engine_id = provider.default_speech_engine_id()
    output = build_output_services(
        engine_options_factory=provider.default_speech_engine_options,
        selected_engine_id=selected_engine_id or default_engine_id,
        fallback_engine_id=fallback_engine_id,
        tone_output=tone_output,
        on_engine_fallback=on_engine_fallback,
    )
    return AppRuntimeParts(
        input_capture=input_capture,
        hotkey_capture=hotkey_capture,
        clipboard=clipboard,
        tone_output=tone_output,
        output=output,
    )
