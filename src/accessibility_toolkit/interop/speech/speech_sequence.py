import logging
from dataclasses import dataclass

from accessibility_toolkit.interop.speech.speech_commands import (
    SpeechCommand,
    restore_speech_command,
)


logger = logging.getLogger(__name__)


def restore_sequence_items(
    payload_sequence: object,
    *,
    preserve_unrecognized: bool = False,
) -> tuple[object, ...]:
    restored: list[object] = []
    if not isinstance(payload_sequence, (list, tuple)):
        return ()

    for item in payload_sequence:
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
            continue
        if preserve_unrecognized:
            restored.append(item)
    return tuple(restored)


@dataclass(frozen=True, slots=True)
class SpeechSequence:
    items: tuple[str | SpeechCommand, ...]

    @classmethod
    def from_remote_payload(cls, payload: dict[str, object]) -> "SpeechSequence":
        restored = cls(items=restore_sequence_items(payload.get("sequence", [])))
        logger.debug("SpeechSequence.from_remote_payload restored=%r", restored.items)
        return restored
