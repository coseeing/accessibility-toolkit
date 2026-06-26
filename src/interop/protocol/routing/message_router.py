import math
from collections.abc import Callable
from typing import Any

from interop.speech.speech_sequence import SpeechSequence
from interop.protocol.messages import RemoteMessageType
from interop.protocol.events import (
    RemotePeerMessageReceived,
    RemoteProtocolMessageInvalid,
)

_MAX_TONE_HZ = 20000
_MAX_TONE_LENGTH_MS = 5000


def _clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _coerce_float(payload: dict[str, Any], field_name: str) -> float:
    value = payload.get(field_name)
    if isinstance(value, bool):
        raise ValueError(field_name)
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(field_name)
    return result


def _coerce_int(payload: dict[str, Any], field_name: str) -> int:
    value = payload.get(field_name)
    if isinstance(value, bool):
        raise ValueError(field_name)
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(field_name)
    return int(value)


class MessageRouter:
    def __init__(
        self,
        on_speech: Callable[[SpeechSequence], None],
        on_cancel: Callable[[], None],
        on_pause: Callable[[bool], None],
        on_clipboard: Callable[[str], None],
        on_tone: Callable[[float, int, int, int], None],
        on_status: Callable[[object], None],
    ) -> None:
        self._on_speech = on_speech
        self._on_cancel = on_cancel
        self._on_pause = on_pause
        self._on_clipboard = on_clipboard
        self._on_tone = on_tone
        self._on_status = on_status

    def handle_message(self, payload: dict[str, Any]) -> None:
        match payload.get("type"):
            case RemoteMessageType.SPEAK.value:
                self._on_speech(SpeechSequence.from_remote_payload(payload))
            case RemoteMessageType.CANCEL.value:
                self._on_cancel()
            case RemoteMessageType.PAUSE_SPEECH.value:
                self._handle_pause_message(payload)
            case RemoteMessageType.TONE.value:
                self._handle_tone_message(payload)
            case RemoteMessageType.SET_CLIPBOARD_TEXT.value:
                self._handle_clipboard_message(payload)
            case _:
                self._on_status(
                    RemotePeerMessageReceived(
                        message_type=str(payload.get("type", "")),
                        payload=payload,
                    )
                )

    def _handle_clipboard_message(self, payload: dict[str, Any]) -> None:
        text = payload.get("text")
        if not isinstance(text, str):
            self._on_status(
                RemoteProtocolMessageInvalid(
                    reason="clipboard_text_must_be_string",
                    payload=payload,
                )
            )
            return
        self._on_clipboard(text)

    def _handle_pause_message(self, payload: dict[str, Any]) -> None:
        switch = payload.get("switch")
        if not isinstance(switch, bool):
            self._on_status(
                RemoteProtocolMessageInvalid(
                    reason="pause_switch_must_be_bool",
                    payload=payload,
                )
            )
            return
        self._on_pause(switch)

    def _handle_tone_message(self, payload: dict[str, Any]) -> None:
        try:
            hz = min(max(0.0, _coerce_float(payload, "hz")), _MAX_TONE_HZ)
            length = _clamp_int(max(0, _coerce_int(payload, "length")), 0, _MAX_TONE_LENGTH_MS)
            left = _clamp_int(_coerce_int(payload, "left"), 0, 100)
            right = _clamp_int(_coerce_int(payload, "right"), 0, 100)
        except (TypeError, ValueError, OverflowError):
            self._on_status(
                RemoteProtocolMessageInvalid(
                    reason="tone_fields_must_be_numeric",
                    payload=payload,
                )
            )
            return
        self._on_tone(hz, length, left, right)
