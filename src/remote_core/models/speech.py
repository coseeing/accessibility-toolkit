from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SpeechSegment:
    kind: str
    value: str | int | float | None


@dataclass(frozen=True, slots=True)
class NormalizedSpeech:
    segments: list[SpeechSegment]

    @classmethod
    def from_remote_payload(cls, payload: dict) -> "NormalizedSpeech":
        segments: list[SpeechSegment] = []
        for item in payload.get("sequence", []):
            if isinstance(item, str):
                segments.append(SpeechSegment(kind="text", value=item))
                continue
            if isinstance(item, list) and item and item[0] == "BreakCommand":
                segments.append(SpeechSegment(kind="break", value=item[1].get("time", 0)))
        return cls(segments=segments)
