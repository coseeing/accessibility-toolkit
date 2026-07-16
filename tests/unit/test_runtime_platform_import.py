from typing import get_type_hints

from accessibility_toolkit.output import ToneOutput, WaveOutput
from accessibility_toolkit.runtime.platform import PlatformProvider


def test_platform_provider_tone_factory_uses_the_public_output_type():
    hints = get_type_hints(PlatformProvider.create_tone_output)

    assert hints["return"] is ToneOutput


def test_platform_provider_wave_factory_uses_the_public_output_type():
    hints = get_type_hints(PlatformProvider.create_wave_output)

    assert hints["return"] is WaveOutput
