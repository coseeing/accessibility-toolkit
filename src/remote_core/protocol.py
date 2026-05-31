from enum import StrEnum
from urllib.parse import urlparse


SERVER_PORT = 6837


class RemoteMessageType(StrEnum):
    PROTOCOL_VERSION = "protocol_version"
    JOIN = "join"
    CHANNEL_JOINED = "channel_joined"
    CLIENT_JOINED = "client_joined"
    CLIENT_LEFT = "client_left"
    KEY = "key"
    SPEAK = "speak"
    CANCEL = "cancel"
    PAUSE_SPEECH = "pause_speech"
    SET_CLIPBOARD_TEXT = "set_clipboard_text"
    MOTD = "motd"
    VERSION_MISMATCH = "version_mismatch"
    PING = "ping"
    ERROR = "error"


def address_to_host_port(address: str) -> tuple[str, int]:
    parsed = urlparse(f"//{address}")
    return parsed.hostname or "", parsed.port or SERVER_PORT
