import json
import logging
from enum import Enum
from typing import Any

from remote_core.models.speech_sequence import restore_sequence_items


logger = logging.getLogger(__name__)


def _as_sequence(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("type") != "speak" or "sequence" not in payload:
        return payload

    raw_sequence = payload["sequence"]
    if not isinstance(raw_sequence, list):
        return payload

    payload["sequence"] = list(
        restore_sequence_items(raw_sequence, preserve_unrecognized=True)
    )
    return payload


class JSONSerializer:
    SEP = b"\n"

    def serialize(self, message_type: str | Enum, **payload: Any) -> bytes:
        value = message_type.value if isinstance(message_type, Enum) else message_type
        payload["type"] = value
        return json.dumps(payload).encode("utf-8") + self.SEP

    def deserialize(self, data: bytes) -> dict[str, Any]:
        logger.debug("JSONSerializer.deserialize input=%r", data)
        payload = json.loads(data.decode("utf-8"), object_hook=_as_sequence)
        if not isinstance(payload, dict):
            raise ValueError("Expected JSON object payload")
        logger.debug(
            "JSONSerializer.deserialize output type=%r keys=%s",
            payload.get("type"),
            sorted(payload.keys()),
        )
        return payload
