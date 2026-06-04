from dataclasses import dataclass

from remote_core.models.speech_commands import (
    BreakCommand,
    IndexCommand,
    PitchCommand,
    RateCommand,
    SpeechCommand,
    VolumeCommand,
)


_FACTORIES = {
    "IndexCommand": lambda data: IndexCommand(index=int(data.get("index", 0))),
    "BreakCommand": lambda data: BreakCommand(time=int(data.get("time", 0))),
    "PitchCommand": lambda data: PitchCommand(offset=int(data.get("offset", 0))),
    "RateCommand": lambda data: RateCommand(
        multiplier=float(data.get("multiplier", 1.0))
    ),
    "VolumeCommand": lambda data: VolumeCommand(
        multiplier=float(data.get("multiplier", 1.0))
    ),
}


@dataclass(frozen=True, slots=True)
class SpeechSequence:
    items: tuple[str | SpeechCommand, ...]

    @classmethod
    def from_remote_payload(cls, payload: dict[str, object]) -> "SpeechSequence":
        restored: list[str | SpeechCommand] = []
        sequence = payload.get("sequence", [])
        if not isinstance(sequence, (list, tuple)):
            sequence = []
        for item in sequence:
            if isinstance(item, str):
                restored.append(item)
                continue
            if (
                isinstance(item, (list, tuple))
                and len(item) >= 2
                and isinstance(item[0], str)
                and isinstance(item[1], dict)
            ):
                factory = _FACTORIES.get(item[0])
                restored.append(
                    factory(item[1])
                    if factory is not None
                    else SpeechCommand(kind=item[0], data=dict(item[1]))
                )
        return cls(items=tuple(restored))
