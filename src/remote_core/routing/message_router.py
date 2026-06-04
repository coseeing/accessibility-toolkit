from collections.abc import Callable
from typing import Any

from remote_core.models.speech_sequence import SpeechSequence
from remote_core.protocol import RemoteMessageType


class MessageRouter:
    def __init__(
        self,
        on_speech: Callable[[SpeechSequence], None],
        on_cancel: Callable[[], None],
        on_pause: Callable[[bool], None],
        on_clipboard: Callable[[str], None],
        on_status: Callable[[dict[str, Any]], None],
    ) -> None:
        self._on_speech = on_speech
        self._on_cancel = on_cancel
        self._on_pause = on_pause
        self._on_clipboard = on_clipboard
        self._on_status = on_status

    def handle_message(self, payload: dict[str, Any]) -> None:
        match payload.get("type"):
            case RemoteMessageType.SPEAK.value:
                self._on_speech(SpeechSequence.from_remote_payload(payload))
            case RemoteMessageType.CANCEL.value:
                self._on_cancel()
            case RemoteMessageType.PAUSE_SPEECH.value:
                self._handle_pause_message(payload)
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

    def _handle_pause_message(self, payload: dict[str, Any]) -> None:
        switch = payload.get("switch")
        if not isinstance(switch, bool):
            self._on_status(
                {
                    "kind": "invalid_message",
                    "reason": "pause_switch_must_be_bool",
                    "payload": payload,
                }
            )
            return
        self._on_pause(switch)
