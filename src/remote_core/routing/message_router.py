from collections.abc import Callable
from typing import Any

from remote_core.models.speech import NormalizedSpeech
from remote_core.protocol import RemoteMessageType


class MessageRouter:
    def __init__(
        self,
        on_speech: Callable[[NormalizedSpeech], None],
        on_clipboard: Callable[[str], None],
        on_status: Callable[[dict[str, Any]], None],
    ) -> None:
        self._on_speech = on_speech
        self._on_clipboard = on_clipboard
        self._on_status = on_status

    def handle_message(self, payload: dict[str, Any]) -> None:
        match payload.get("type"):
            case RemoteMessageType.SPEAK.value:
                self._on_speech(NormalizedSpeech.from_remote_payload(payload))
            case RemoteMessageType.SET_CLIPBOARD_TEXT.value:
                self._handle_clipboard_message(payload)
            case _:
                self._on_status(
                    {
                        "kind": "remote",
                        "type": payload.get("type"),
                        "payload": payload,
                    }
                )

    def _handle_clipboard_message(self, payload: dict[str, Any]) -> None:
        text = payload.get("text")
        if not isinstance(text, str):
            self._on_status(
                {
                    "kind": "invalid_message",
                    "reason": "clipboard_text_must_be_string",
                    "payload": payload,
                }
            )
            return
        self._on_clipboard(text)
