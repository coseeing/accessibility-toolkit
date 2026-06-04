import json
from enum import Enum
from typing import Any

from remote_core.models.speech_commands import restore_speech_command


def _as_sequence(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("type") != "speak" or "sequence" not in payload:
        return payload

    raw_sequence = payload["sequence"]
    if not isinstance(raw_sequence, list):
        return payload

    sequence: list[Any] = []
    for item in raw_sequence:
        if isinstance(item, str):
            sequence.append(item)
            continue
        if (
            isinstance(item, list)
            and len(item) >= 2
            and isinstance(item[0], str)
            and isinstance(item[1], dict)
        ):
            sequence.append(restore_speech_command(item[0], item[1]))
            continue
        sequence.append(item)
    payload["sequence"] = sequence
    return payload


class JSONSerializer:
    SEP = b"\n"

    def serialize(self, message_type: str | Enum, **payload: Any) -> bytes:
        value = message_type.value if isinstance(message_type, Enum) else message_type
        payload["type"] = value
        return json.dumps(payload).encode("utf-8") + self.SEP

    def deserialize(self, data: bytes) -> dict[str, Any]:
        payload = json.loads(data.decode("utf-8"), object_hook=_as_sequence)
        if not isinstance(payload, dict):
            raise ValueError("Expected JSON object payload")
        return payload
