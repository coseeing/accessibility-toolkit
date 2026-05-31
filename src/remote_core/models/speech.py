from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SpeechSegment:
    kind: str
    value: str | int | float | None


@dataclass(frozen=True, slots=True)
class NormalizedSpeech:
    segments: tuple[SpeechSegment, ...]

    @classmethod
    def from_remote_payload(cls, payload: dict) -> "NormalizedSpeech":
        segments: list[SpeechSegment] = []
        sequence = payload.get("sequence", [])
        if not isinstance(sequence, list | tuple):
            sequence = []
        for item in sequence:
            if isinstance(item, str):
                segments.append(SpeechSegment(kind="text", value=item))
                continue
            if (
                isinstance(item, list)
                and len(item) >= 2
                and item[0] == "BreakCommand"
                and isinstance(item[1], dict)
            ):
                segments.append(SpeechSegment(kind="break", value=item[1].get("time", 0)))
        return cls(segments=tuple(segments))
