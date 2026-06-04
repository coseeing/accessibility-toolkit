from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True, slots=True)
class SpeechCommand:
    kind: str
    data: dict[str, object] = field(default_factory=dict)


def _set_command_attrs(
    command: SpeechCommand,
    kind: str,
    field_name: str,
    value: int | float,
) -> None:
    object.__setattr__(command, "kind", kind)
    object.__setattr__(command, "data", {field_name: value})
    object.__setattr__(command, field_name, value)


def _coerce_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True, slots=True)
class IndexCommand(SpeechCommand):
    index: int = 0

    def __init__(self, index: int) -> None:
        _set_command_attrs(self, "IndexCommand", "index", index)


@dataclass(frozen=True, slots=True)
class BreakCommand(SpeechCommand):
    time: int = 0

    def __init__(self, time: int = 0) -> None:
        _set_command_attrs(self, "BreakCommand", "time", time)


@dataclass(frozen=True, slots=True)
class PitchCommand(SpeechCommand):
    offset: int = 0

    def __init__(self, offset: int = 0) -> None:
        _set_command_attrs(self, "PitchCommand", "offset", offset)


@dataclass(frozen=True, slots=True)
class RateCommand(SpeechCommand):
    multiplier: float = 1.0

    def __init__(self, multiplier: float = 1.0) -> None:
        _set_command_attrs(self, "RateCommand", "multiplier", multiplier)


@dataclass(frozen=True, slots=True)
class VolumeCommand(SpeechCommand):
    multiplier: float = 1.0

    def __init__(self, multiplier: float = 1.0) -> None:
        _set_command_attrs(self, "VolumeCommand", "multiplier", multiplier)


SupportedCommandFactory = Callable[[dict[str, object]], SpeechCommand]


SUPPORTED_COMMAND_FACTORIES: dict[str, SupportedCommandFactory] = {
    "IndexCommand": lambda data: IndexCommand(index=_coerce_int(data.get("index", 0), 0)),
    "BreakCommand": lambda data: BreakCommand(time=_coerce_int(data.get("time", 0), 0)),
    "PitchCommand": lambda data: PitchCommand(
        offset=_coerce_int(data.get("offset", 0), 0)
    ),
    "RateCommand": lambda data: RateCommand(
        multiplier=_coerce_float(data.get("multiplier", 1.0), 1.0)
    ),
    "VolumeCommand": lambda data: VolumeCommand(
        multiplier=_coerce_float(data.get("multiplier", 1.0), 1.0)
    ),
}


def restore_speech_command(kind: str, data: dict[str, object]) -> SpeechCommand:
    factory = SUPPORTED_COMMAND_FACTORIES.get(kind)
    if factory is None:
        return SpeechCommand(kind=kind, data=dict(data))
    return factory(data)
