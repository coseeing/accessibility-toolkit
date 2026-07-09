from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True, slots=True)
class SpeechCommand:
    kind: str
    data: dict[str, object] = field(default_factory=dict)


def _set_command_attrs(
    command: SpeechCommand,
    kind: str,
    data: dict[str, object],
    **attrs: object,
) -> None:
    object.__setattr__(command, "kind", kind)
    object.__setattr__(command, "data", data)
    for field_name, value in attrs.items():
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


def _resolve_prosody_mode(offset: int, multiplier: float) -> str:
    if offset != 0 and multiplier != 1.0:
        raise ValueError("offset and multiplier cannot both be non-default")
    if offset != 0:
        return "offset"
    if multiplier != 1.0:
        return "multiplier"
    return "default"


def _restore_prosody_command(
    command_type: type["ProsodyCommand"],
    data: dict[str, object],
) -> "ProsodyCommand":
    offset = _coerce_int(data.get("offset", data.get("_offset", 0)), 0)
    multiplier = _coerce_float(data.get("multiplier", data.get("_multiplier", 1.0)), 1.0)
    is_default = data.get("isDefault", data.get("is_default", None))
    if isinstance(is_default, bool) and is_default:
        offset = 0
        multiplier = 1.0
    return command_type(
        offset=offset,
        multiplier=multiplier,
    )


@dataclass(frozen=True, slots=True)
class IndexCommand(SpeechCommand):
    index: int = 0

    def __init__(self, index: int) -> None:
        _set_command_attrs(self, "IndexCommand", {"index": index}, index=index)


@dataclass(frozen=True, slots=True)
class BreakCommand(SpeechCommand):
    time: int = 0

    def __init__(self, time: int = 0) -> None:
        _set_command_attrs(self, "BreakCommand", {"time": time}, time=time)


@dataclass(frozen=True, slots=True)
class ProsodyCommand(SpeechCommand):
    offset: int = 0
    multiplier: float = 1.0
    mode: str = "default"

    def __init__(
        self,
        kind: str,
        offset: int = 0,
        multiplier: float = 1.0,
    ) -> None:
        mode = _resolve_prosody_mode(offset, multiplier)
        data = (
            {"offset": offset}
            if mode == "offset"
            else {"multiplier": multiplier}
            if mode == "multiplier"
            else {}
        )
        _set_command_attrs(
            self,
            kind,
            data,
            offset=offset,
            multiplier=multiplier,
            mode=mode,
        )


@dataclass(frozen=True, slots=True)
class PitchCommand(ProsodyCommand):
    def __init__(self, offset: int = 0, multiplier: float = 1.0) -> None:
        ProsodyCommand.__init__(self, "PitchCommand", offset=offset, multiplier=multiplier)


@dataclass(frozen=True, slots=True)
class RateCommand(ProsodyCommand):
    def __init__(self, offset: int = 0, multiplier: float = 1.0) -> None:
        ProsodyCommand.__init__(self, "RateCommand", offset=offset, multiplier=multiplier)


@dataclass(frozen=True, slots=True)
class VolumeCommand(ProsodyCommand):
    def __init__(self, offset: int = 0, multiplier: float = 1.0) -> None:
        ProsodyCommand.__init__(self, "VolumeCommand", offset=offset, multiplier=multiplier)


SupportedCommandFactory = Callable[[dict[str, object]], SpeechCommand]


SUPPORTED_COMMAND_FACTORIES: dict[str, SupportedCommandFactory] = {
    "IndexCommand": lambda data: IndexCommand(index=_coerce_int(data.get("index", 0), 0)),
    "BreakCommand": lambda data: BreakCommand(time=_coerce_int(data.get("time", 0), 0)),
    "PitchCommand": lambda data: _restore_prosody_command(PitchCommand, data),
    "RateCommand": lambda data: _restore_prosody_command(RateCommand, data),
    "VolumeCommand": lambda data: _restore_prosody_command(VolumeCommand, data),
}


def restore_speech_command(kind: str, data: dict[str, object]) -> SpeechCommand:
    factory = SUPPORTED_COMMAND_FACTORIES.get(kind)
    if factory is None:
        return SpeechCommand(kind=kind, data=dict(data))
    return factory(data)
