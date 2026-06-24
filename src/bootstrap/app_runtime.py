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
    selected_engine_id: str | None = None,
    fallback_engine_id: str | None = None,
    on_engine_fallback: Callable[[str], None] | None = None,
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
    if hasattr(provider, "default_speech_engine_id"):
        default_engine_id_getter = provider.default_speech_engine_id
    else:
        default_engine_id_getter = provider.default_speech_backend_id
    if hasattr(provider, "default_speech_engine_options"):
        default_engine_options_getter = provider.default_speech_engine_options
    else:
        default_engine_options_getter = provider.default_speech_backend_options
    default_engine_id = default_engine_id_getter()
    output = build_output_services(
        engine_options_factory=default_engine_options_getter,
        selected_engine_id=selected_engine_id or selected_backend_id or default_engine_id,
        fallback_engine_id=fallback_engine_id or fallback_backend_id,
        tone_output=tone_output,
        on_engine_fallback=on_engine_fallback or on_backend_fallback,
    )
    return AppRuntimeParts(
        input_capture=input_capture,
        hotkey_capture=hotkey_capture,
        clipboard=clipboard,
        tone_output=tone_output,
        output=output,
    )
