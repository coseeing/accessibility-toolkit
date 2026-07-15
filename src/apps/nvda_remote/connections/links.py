from urllib.parse import ParseResult, urlencode

from .models import SavedConnection

DEFAULT_PORT = 6837


def format_connection_url(connection: SavedConnection) -> str:
    host = f"[{connection.host}]" if ":" in connection.host else connection.host
    netloc = host if connection.port == DEFAULT_PORT else f"{host}:{connection.port}"
    query: list[tuple[str, str]] = [("key", connection.key), ("mode", "slave")]
    if connection.insecure:
        query.append(("insecure", "true"))
    return ParseResult("nvdaremote", netloc, "", "", urlencode(query), "").geturl()
