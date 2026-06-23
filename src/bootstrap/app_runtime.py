from collections.abc import Callable
from dataclasses import dataclass

from adapters.inputs.base import HotkeyCapture, InputCapture
from application.output import ClipboardService
from bootstrap.output import OutputServices, build_output_services
from bootstrap.platform import PlatformProvider


@dataclass(frozen=True)
class AppRuntimeParts:
    input_capture: InputCapture
    hotkey_capture: HotkeyCapture
    clipboard: ClipboardService
    tone_output: object
    output: OutputServices


def build_app_runtime_parts(
    *,
    hotkey_usage: int,
    provider: PlatformProvider | None = None,
    selected_backend_id: str | None = None,
    fallback_backend_id: str | None = None,
    on_backend_fallback: Callable[[str], None] | None = None,
    include_tone: bool = True,
) -> AppRuntimeParts:
    provider = provider or PlatformProvider()
    platform_services = provider.build_services(hotkey_usage=hotkey_usage)
    default_backend_id = provider.default_speech_backend_id()
    output = build_output_services(
        backend_options_factory=provider.default_speech_backend_options,
        selected_backend_id=selected_backend_id or default_backend_id,
        fallback_backend_id=fallback_backend_id,
        tone_output=platform_services.tone_output if include_tone else None,
        on_backend_fallback=on_backend_fallback,
    )
    return AppRuntimeParts(
        input_capture=platform_services.input_capture,
        hotkey_capture=platform_services.hotkey_capture,
        clipboard=platform_services.clipboard,
        tone_output=platform_services.tone_output,
        output=output,
    )
