import json
from enum import Enum
from typing import Any


class JSONSerializer:
    SEP = b"\n"

    def serialize(self, message_type: str | Enum, **payload: Any) -> bytes:
        value = message_type.value if isinstance(message_type, Enum) else message_type
        payload["type"] = value
        return json.dumps(payload).encode("utf-8") + self.SEP

    def deserialize(self, data: bytes) -> dict[str, Any]:
        payload = json.loads(data.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Expected JSON object payload")
        return payload
