from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SpeechCommand:
    kind: str
    data: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class IndexCommand(SpeechCommand):
    index: int = 0

    def __init__(self, index: int) -> None:
        object.__setattr__(self, "kind", "IndexCommand")
        object.__setattr__(self, "data", {"index": index})
        object.__setattr__(self, "index", index)


@dataclass(frozen=True, slots=True)
class BreakCommand(SpeechCommand):
    time: int = 0

    def __init__(self, time: int = 0) -> None:
        object.__setattr__(self, "kind", "BreakCommand")
        object.__setattr__(self, "data", {"time": time})
        object.__setattr__(self, "time", time)


@dataclass(frozen=True, slots=True)
class PitchCommand(SpeechCommand):
    offset: int = 0

    def __init__(self, offset: int = 0) -> None:
        object.__setattr__(self, "kind", "PitchCommand")
        object.__setattr__(self, "data", {"offset": offset})
        object.__setattr__(self, "offset", offset)


@dataclass(frozen=True, slots=True)
class RateCommand(SpeechCommand):
    multiplier: float = 1.0

    def __init__(self, multiplier: float = 1.0) -> None:
        object.__setattr__(self, "kind", "RateCommand")
        object.__setattr__(self, "data", {"multiplier": multiplier})
        object.__setattr__(self, "multiplier", multiplier)


@dataclass(frozen=True, slots=True)
class VolumeCommand(SpeechCommand):
    multiplier: float = 1.0

    def __init__(self, multiplier: float = 1.0) -> None:
        object.__setattr__(self, "kind", "VolumeCommand")
        object.__setattr__(self, "data", {"multiplier": multiplier})
        object.__setattr__(self, "multiplier", multiplier)
