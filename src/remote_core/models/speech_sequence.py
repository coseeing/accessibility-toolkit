from dataclasses import dataclass

from remote_core.models.speech_commands import (
    SpeechCommand,
    restore_speech_command,
)


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
            if isinstance(item, SpeechCommand):
                restored.append(item)
                continue
            if (
                isinstance(item, (list, tuple))
                and len(item) >= 2
                and isinstance(item[0], str)
                and isinstance(item[1], dict)
            ):
                restored.append(restore_speech_command(item[0], item[1]))
        return cls(items=tuple(restored))
