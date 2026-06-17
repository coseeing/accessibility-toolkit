import logging
import wave
from io import BytesIO

from adapters.outputs.tone import (
    SAMPLE_RATE,
    MAX_TONE_HZ,
    MAX_TONE_LENGTH_MS,
    DefaultToneOutput,
    generate_beep_wav,
    normalize_beep_parameters,
)


class FakePlaybackBackend:
    def __init__(self) -> None:
        self.calls = []

    def play(self, wav_data: bytes) -> None:
        self.calls.append(wav_data)


class FailingPlaybackBackend:
    def play(self, wav_data: bytes) -> None:
        raise RuntimeError("audio failed")


def test_normalize_beep_parameters_clamps_balance_and_non_negative_values() -> None:
    params = normalize_beep_parameters(-10, -5, -20, 250)

    assert params.hz == 0.0
    assert params.length == 0
    assert params.left == 0
    assert params.right == 100


def test_generate_beep_wav_creates_stereo_16_bit_wav() -> None:
    params = normalize_beep_parameters(440, 100, 25, 75)

    wav_data = generate_beep_wav(params)

    with wave.open(BytesIO(wav_data), "rb") as wav_file:
        assert wav_file.getnchannels() == 2
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == SAMPLE_RATE
        assert wav_file.getnframes() == SAMPLE_RATE // 10


def test_default_tone_output_plays_generated_wav() -> None:
    playback = FakePlaybackBackend()
    output = DefaultToneOutput(playback=playback)

    output.beep(440, 100, 25, 75)

    assert len(playback.calls) == 1
    assert playback.calls[0].startswith(b"RIFF")


def test_default_tone_output_skips_zero_length_tone() -> None:
    playback = FakePlaybackBackend()
    output = DefaultToneOutput(playback=playback)

    output.beep(440, 0, 50, 50)

    assert playback.calls == []


def test_default_tone_output_logs_backend_failures(caplog) -> None:
    output = DefaultToneOutput(playback=FailingPlaybackBackend())

    with caplog.at_level(logging.WARNING):
        output.beep(440, 100, 50, 50)

    assert "Failed to play tone" in caplog.text


def test_normalize_beep_parameters_clamps_to_maximum_bounds() -> None:
    params = normalize_beep_parameters(50000, 30000, 50, 50)

    assert params.hz == MAX_TONE_HZ
    assert params.length == MAX_TONE_LENGTH_MS


def test_normalize_beep_parameters_zeros_inf_hz() -> None:
    params = normalize_beep_parameters(float("inf"), 100, 50, 50)

    assert params.hz == 0.0


def test_normalize_beep_parameters_zeros_nan_hz() -> None:
    params = normalize_beep_parameters(float("nan"), 100, 50, 50)

    assert params.hz == 0.0


def test_default_tone_output_skips_zero_hz_tone() -> None:
    playback = FakePlaybackBackend()
    output = DefaultToneOutput(playback=playback)

    output.beep(0, 100, 50, 50)

    assert playback.calls == []
