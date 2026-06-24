from dataclasses import dataclass


@dataclass(frozen=True)
class SpeechNumericSetting:
    id: str
    label: str
    default_percent: int = 50
    min_percent: int = 0
    max_percent: int = 100
    step: int = 1
    large_step: int = 10


def clamp_percent(value: int) -> int:
    return max(0, min(100, int(value)))


def percent_to_range(percent: int, minimum: int, maximum: int) -> int:
    if minimum >= maximum:
        return int(minimum)
    normalized_percent = clamp_percent(percent)
    span = maximum - minimum
    return round(minimum + (span * (normalized_percent / 100.0)))


def range_to_percent(value: int, minimum: int, maximum: int) -> int:
    if minimum >= maximum:
        return 0
    clamped_value = max(minimum, min(maximum, int(value)))
    span = maximum - minimum
    return clamp_percent(round(((clamped_value - minimum) / span) * 100))
