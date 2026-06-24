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


def percent_to_range(percent: int, min_value: float, max_value: float) -> float:
    """Map a normalized 0-100 percent into an arbitrary [min_value, max_value] range."""
    clamped = clamp_percent(percent)
    return (clamped / 100.0) * (max_value - min_value) + min_value


def range_to_percent(raw: float, min_value: float, max_value: float) -> int:
    """Map an arbitrary raw value in [min_value, max_value] back to a 0-100 percent."""
    if max_value == min_value:
        return 0
    percent = round(((raw - min_value) / (max_value - min_value)) * 100)
    return clamp_percent(percent)