from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
from uuid import UUID, uuid4

FORMAT_VERSION = 1
DEFAULT_GROUP = "Default"


def _required(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    return value.strip()


@dataclass(frozen=True, slots=True)
class SavedConnection:
    id: str
    name: str
    host: str
    port: int
    key: str
    insecure: bool = False

    def __post_init__(self) -> None:
        normalized_id = _required(self.id, "id")
        UUID(normalized_id)
        object.__setattr__(self, "id", normalized_id)
        object.__setattr__(self, "name", _required(self.name, "name"))
        host = _required(self.host, "host")
        if host.startswith("[") and host.endswith("]"):
            host = _required(host[1:-1], "host")
        object.__setattr__(self, "host", host)
        object.__setattr__(self, "key", _required(self.key, "key"))
        if isinstance(self.port, bool) or not isinstance(self.port, int) or not 1 <= self.port <= 65535:
            raise ValueError("port must be an integer between 1 and 65535")
        if not isinstance(self.insecure, bool):
            raise ValueError("insecure must be a boolean")

    @classmethod
    def create(
        cls,
        *,
        name: str,
        host: str,
        port: int,
        key: str,
        insecure: bool = False,
        id_factory: Callable[[], object] = uuid4,
    ) -> "SavedConnection":
        return cls(str(id_factory()), name, host, port, key, insecure)

    @classmethod
    def from_dict(cls, payload: object) -> "SavedConnection":
        if not isinstance(payload, dict):
            raise ValueError("connection must be an object")
        return cls(
            id=payload.get("id"),
            name=payload.get("name"),
            host=payload.get("host"),
            port=payload.get("port"),
            key=payload.get("key"),
            insecure=payload.get("insecure", False),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "key": self.key,
            "insecure": self.insecure,
        }


@dataclass(slots=True)
class ConnectionCatalog:
    format_version: int = FORMAT_VERSION
    active_group: str = DEFAULT_GROUP
    close_on_connect: bool = True
    quick_connect_id: str | None = None
    groups: dict[str, list[SavedConnection]] = field(default_factory=lambda: {DEFAULT_GROUP: []})

    @classmethod
    def default(cls) -> "ConnectionCatalog":
        return cls()

    @classmethod
    def from_dict(cls, payload: object) -> "ConnectionCatalog":
        if not isinstance(payload, dict):
            raise ValueError("connection catalog must be an object")
        version = payload.get("format_version")
        if type(version) is not int or version != FORMAT_VERSION:
            raise ValueError("unsupported connection catalog format")
        raw_groups = payload.get("groups")
        if not isinstance(raw_groups, dict) or DEFAULT_GROUP not in raw_groups:
            raise ValueError("groups must contain Default")
        groups: dict[str, list[SavedConnection]] = {}
        seen_ids: set[str] = set()
        for raw_name, raw_connections in raw_groups.items():
            name = _required(raw_name, "group name")
            if name in groups:
                raise ValueError("duplicate normalized group name")
            if not isinstance(raw_connections, list):
                raise ValueError("group connections must be a list")
            connections = [SavedConnection.from_dict(item) for item in raw_connections]
            for connection in connections:
                if connection.id in seen_ids:
                    raise ValueError(f"duplicate connection id: {connection.id}")
                seen_ids.add(connection.id)
            groups[name] = connections
        active_group = payload.get("active_group")
        if active_group not in groups:
            active_group = DEFAULT_GROUP
        close_on_connect = payload.get("close_on_connect", True)
        quick_connect_id = payload.get("quick_connect_id")
        if not isinstance(close_on_connect, bool):
            raise ValueError("close_on_connect must be a boolean")
        if quick_connect_id is not None and not isinstance(quick_connect_id, str):
            raise ValueError("quick_connect_id must be a string or null")
        return cls(FORMAT_VERSION, active_group, close_on_connect, quick_connect_id, groups)

    def to_dict(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "active_group": self.active_group,
            "close_on_connect": self.close_on_connect,
            "quick_connect_id": self.quick_connect_id,
            "groups": {
                name: [connection.to_dict() for connection in connections]
                for name, connections in self.groups.items()
            },
        }
