# NVDA Remote Connection Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace manual connection entry in the standalone NVDA Remote main window with a persistent, accessible connection manager and an optional quick-connect default.

**Architecture:** A typed `apps.nvda_remote.connections` package owns saved-connection validation, URL formatting, atomic JSON persistence, and catalog operations. `NvdaRemoteAppService` adapts saved entries to the existing `RemoteSession`, while focused wxPython dialogs manage connections and groups without reading JSON directly.

**Tech Stack:** Python 3.11+, dataclasses, `pathlib`, `json`, `os.replace`, `urllib.parse`, `secrets`, wxPython, pytest.

## Global Constraints

- Do not require NVDA Python runtime modules.
- Do not add leader/follower controls, reversed-mode connection actions, local/self-hosted servers, or startup auto-connect.
- Every target must be saved before connection; remove manual Host, Port, and Key fields from the main frame.
- `quick_connect_id` defaults to `null`; Quick Connect is disabled for null/stale defaults and while connecting or connected.
- Manage Connections stays available while connected and is disabled only during an in-progress connection attempt.
- Store keys as plain text in the local runtime configuration file, separately from speech settings.
- Use `format_version: 1`, default port `6837`, and port range `1..65535`.
- Persist with a sibling temporary file followed by `os.replace`; never overwrite a malformed file merely because loading failed.
- Emit copied links as `nvdaremote://host[:port]?key=<encoded>&mode=slave[&insecure=true]`; omit port 6837 and bracket IPv6 hosts.
- Keep all platform-specific behavior outside shared connection-management modules.
- Do not create Git commits or stage new changes unless the user explicitly asks; each task ends with a diff/test checkpoint instead of a commit.

---

## File Structure

Create these focused application modules:

- `src/apps/nvda_remote/connections/models.py`: immutable saved-connection and mutable catalog models, validation, JSON conversion.
- `src/apps/nvda_remote/connections/links.py`: NVDA Remote-compatible URL formatting only.
- `src/apps/nvda_remote/connections/store.py`: versioned JSON load and atomic save.
- `src/apps/nvda_remote/connections/manager.py`: transactional group, connection, ordering, search, preference, and quick-default operations.
- `src/apps/nvda_remote/connections/__init__.py`: intentional public API for the package.
- `src/ui/nvda_remote/connection_editor.py`: add/edit dialog and secure seven-digit key generation.
- `src/ui/nvda_remote/group_manager_dialog.py`: group CRUD dialog.
- `src/ui/nvda_remote/connection_manager_dialog.py`: searchable connection list, actions, context menu, shortcuts, and connection dispatch.

Modify these integration points:

- `src/apps/nvda_remote/state.py`: add the `CONNECTING` state.
- `src/apps/nvda_remote/service.py`: inject the manager and expose saved/quick connection actions.
- `src/apps/nvda_remote/main.py`: compose the JSON store and manager using a separate runtime config path.
- `src/ui/nvda_remote/main_frame.py`: remove manual entry and add Manage Connections, Quick Connect, and Disconnect actions.
- `tests/unit/test_app_wx.py`: extend the existing fake wx surface and replace manual-entry UI tests.
- `README.md` and `docs/zh_TW/README.md`: document the saved-connection workflow.

Add focused tests:

- `tests/unit/test_nvda_remote_connection_models.py`
- `tests/unit/test_nvda_remote_connection_store.py`
- `tests/unit/test_nvda_remote_connection_manager.py`
- `tests/unit/test_nvda_remote_connection_links.py`
- `tests/unit/test_nvda_remote_connection_ui.py`

---

### Task 1: Saved-connection model and compatible links

**Files:**
- Create: `src/apps/nvda_remote/connections/__init__.py`
- Create: `src/apps/nvda_remote/connections/models.py`
- Create: `src/apps/nvda_remote/connections/links.py`
- Test: `tests/unit/test_nvda_remote_connection_models.py`
- Test: `tests/unit/test_nvda_remote_connection_links.py`

**Interfaces:**
- Produces: `SavedConnection.create(name, host, port, key, insecure=False, id_factory: Callable[[], object] = uuid4) -> SavedConnection`
- Produces: `SavedConnection.from_dict(payload) -> SavedConnection`
- Produces: `SavedConnection.to_dict() -> dict[str, object]`
- Produces: `ConnectionCatalog.default() -> ConnectionCatalog`
- Produces: `ConnectionCatalog.from_dict(payload) -> ConnectionCatalog`
- Produces: `ConnectionCatalog.to_dict() -> dict[str, object]`
- Produces: `format_connection_url(connection: SavedConnection) -> str`

- [ ] **Step 1: Write failing model tests**

```python
import pytest

from apps.nvda_remote.connections.models import ConnectionCatalog, SavedConnection


def test_saved_connection_create_trims_fields_and_serializes():
    connection = SavedConnection.create(
        name="  Office  ",
        host=" relay.example ",
        port=6837,
        key=" secret ",
        insecure=False,
        id_factory=lambda: "f30cbe12-d88e-4ce7-86c6-905274559839",
    )
    assert connection.name == "Office"
    assert connection.host == "relay.example"
    assert connection.key == "secret"
    assert connection.to_dict() == {
        "id": "f30cbe12-d88e-4ce7-86c6-905274559839",
        "name": "Office",
        "host": "relay.example",
        "port": 6837,
        "key": "secret",
        "insecure": False,
    }


@pytest.mark.parametrize("field", ["name", "host", "key"])
def test_saved_connection_rejects_blank_required_fields(field):
    values = {"name": "Office", "host": "relay.example", "port": 6837, "key": "secret"}
    values[field] = "   "
    with pytest.raises(ValueError, match=field):
        SavedConnection.create(**values)


@pytest.mark.parametrize("port", [0, 65536, True, "6837"])
def test_saved_connection_rejects_invalid_port(port):
    with pytest.raises(ValueError, match="port"):
        SavedConnection.create(name="Office", host="relay.example", port=port, key="secret")


def test_catalog_default_has_version_default_group_and_no_quick_connect():
    catalog = ConnectionCatalog.default()
    assert catalog.format_version == 1
    assert catalog.active_group == "Default"
    assert catalog.close_on_connect is True
    assert catalog.quick_connect_id is None
    assert catalog.groups == {"Default": []}


def test_catalog_rejects_duplicate_connection_ids_across_groups():
    connection = SavedConnection.create(name="Office", host="relay.example", port=6837, key="secret")
    payload = ConnectionCatalog.default().to_dict()
    payload["groups"] = {
        "Default": [connection.to_dict()],
        "Work": [connection.to_dict()],
    }
    with pytest.raises(ValueError, match="duplicate connection id"):
        ConnectionCatalog.from_dict(payload)


def test_catalog_rejects_boolean_format_version():
    payload = ConnectionCatalog.default().to_dict()
    payload["format_version"] = True
    with pytest.raises(ValueError, match="format"):
        ConnectionCatalog.from_dict(payload)
```

- [ ] **Step 2: Run model tests to verify RED**

Run: `pytest tests/unit/test_nvda_remote_connection_models.py -v`

Expected: collection fails with `ModuleNotFoundError: No module named 'apps.nvda_remote.connections'`.

- [ ] **Step 3: Implement the models and package exports**

```python
# src/apps/nvda_remote/connections/models.py
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
        if isinstance(version, bool) or version != FORMAT_VERSION:
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
```

Export `ConnectionCatalog`, `DEFAULT_GROUP`, `SavedConnection`, and later public store/manager symbols from `connections/__init__.py`.

- [ ] **Step 4: Write failing link-format tests**

```python
from apps.nvda_remote.connections.links import format_connection_url
from apps.nvda_remote.connections.models import SavedConnection


def connection(**changes):
    values = dict(
        id="f30cbe12-d88e-4ce7-86c6-905274559839",
        name="Office",
        host="relay.example",
        port=6837,
        key="space & symbols",
        insecure=False,
    )
    values.update(changes)
    return SavedConnection(**values)


def test_link_omits_default_port_and_encodes_key():
    assert format_connection_url(connection()) == (
        "nvdaremote://relay.example?key=space+%26+symbols&mode=slave"
    )


def test_link_brackets_ipv6_and_includes_non_default_port_and_insecure():
    assert format_connection_url(connection(host="2001:db8::1", port=7000, insecure=True)) == (
        "nvdaremote://[2001:db8::1]:7000?key=space+%26+symbols&mode=slave&insecure=true"
    )
```

- [ ] **Step 5: Run link tests to verify RED**

Run: `pytest tests/unit/test_nvda_remote_connection_links.py -v`

Expected: FAIL because `format_connection_url` does not exist.

- [ ] **Step 6: Implement URL formatting**

```python
# src/apps/nvda_remote/connections/links.py
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
```

- [ ] **Step 7: Run Task 1 tests and inspect the diff**

Run: `pytest tests/unit/test_nvda_remote_connection_models.py tests/unit/test_nvda_remote_connection_links.py -v`

Expected: all Task 1 tests PASS.

Run: `git diff --check && git status --short`

Expected: no whitespace errors; only intended connection package/tests plus pre-existing spec changes are listed.

---

### Task 2: Versioned atomic JSON store

**Files:**
- Create: `src/apps/nvda_remote/connections/store.py`
- Modify: `src/apps/nvda_remote/connections/__init__.py`
- Test: `tests/unit/test_nvda_remote_connection_store.py`

**Interfaces:**
- Consumes: `ConnectionCatalog.default/from_dict/to_dict`
- Produces: `JsonConnectionStore(path: Path, logger: logging.Logger | None = None)`
- Produces: `JsonConnectionStore.load() -> ConnectionCatalog`
- Produces: `JsonConnectionStore.save(catalog: ConnectionCatalog) -> None`

- [ ] **Step 1: Write failing load and corruption tests**

```python
import json
import pytest

from apps.nvda_remote.connections import ConnectionCatalog, JsonConnectionStore


def test_missing_store_loads_default_without_creating_file(tmp_path):
    path = tmp_path / "connections.json"
    catalog = JsonConnectionStore(path).load()
    assert catalog == ConnectionCatalog.default()
    assert path.exists() is False


def test_corrupt_store_loads_default_without_overwriting_source(tmp_path, caplog):
    path = tmp_path / "connections.json"
    path.write_text("{broken", encoding="utf-8")
    catalog = JsonConnectionStore(path).load()
    assert catalog == ConnectionCatalog.default()
    assert path.read_text(encoding="utf-8") == "{broken"
    assert "Failed to load saved connections" in caplog.text


def test_wrong_format_version_is_treated_as_invalid(tmp_path):
    path = tmp_path / "connections.json"
    path.write_text(json.dumps({"format_version": 99, "groups": {"Default": []}}), encoding="utf-8")
    assert JsonConnectionStore(path).load() == ConnectionCatalog.default()
```

- [ ] **Step 2: Run load tests to verify RED**

Run: `pytest tests/unit/test_nvda_remote_connection_store.py -v`

Expected: FAIL because `JsonConnectionStore` is not exported.

- [ ] **Step 3: Write failing atomic-save tests**

```python
import os


def test_save_round_trips_and_leaves_no_temporary_file(tmp_path):
    path = tmp_path / "connections.json"
    store = JsonConnectionStore(path)
    catalog = ConnectionCatalog.default()
    catalog.close_on_connect = False
    store.save(catalog)
    assert store.load() == catalog
    assert (tmp_path / "connections.json.tmp").exists() is False


def test_replace_failure_preserves_existing_file(tmp_path, monkeypatch):
    path = tmp_path / "connections.json"
    path.write_text('{"original": true}\n', encoding="utf-8")
    store = JsonConnectionStore(path)

    def fail_replace(source, target):
        raise OSError("disk failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="disk failure"):
        store.save(ConnectionCatalog.default())
    assert path.read_text(encoding="utf-8") == '{"original": true}\n'
    assert (tmp_path / "connections.json.tmp").exists() is False
```

- [ ] **Step 4: Implement atomic load/save**

```python
# src/apps/nvda_remote/connections/store.py
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from .models import ConnectionCatalog


class JsonConnectionStore:
    def __init__(self, path: Path, logger: logging.Logger | None = None) -> None:
        self.path = Path(path)
        self._logger = logger or logging.getLogger(__name__)

    def load(self) -> ConnectionCatalog:
        if not self.path.exists():
            return ConnectionCatalog.default()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return ConnectionCatalog.from_dict(payload)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            self._logger.error("Failed to load saved connections from %s", self.path, exc_info=True)
            return ConnectionCatalog.default()

    def save(self, catalog: ConnectionCatalog) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f"{self.path.name}.tmp")
        try:
            temporary.write_text(
                json.dumps(catalog.to_dict(), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, self.path)
        except OSError:
            try:
                temporary.unlink(missing_ok=True)
            finally:
                raise
```

Export `JsonConnectionStore` from `connections/__init__.py`.

- [ ] **Step 5: Run Task 2 tests and inspect the diff**

Run: `pytest tests/unit/test_nvda_remote_connection_store.py -v`

Expected: all Task 2 tests PASS.

Run: `git diff --check && git status --short`

Expected: no whitespace errors and no commit is created.

---

### Task 3: Transactional connection manager

**Files:**
- Create: `src/apps/nvda_remote/connections/manager.py`
- Modify: `src/apps/nvda_remote/connections/__init__.py`
- Test: `tests/unit/test_nvda_remote_connection_manager.py`

**Interfaces:**
- Consumes: `JsonConnectionStore.load/save`, `ConnectionCatalog`, `SavedConnection`
- Produces: `ConnectionManager(store: JsonConnectionStore)`
- Produces: group methods `groups`, `active_group`, `set_active_group`, `create_group`, `rename_group`, `delete_groups`
- Produces: connection methods `connections`, `search`, `add_connection`, `update_connection`, `delete_connections`, `swap_connections`, `find_connection`
- Produces: preferences `close_on_connect`, `set_close_on_connect`, `quick_connection`, `set_quick_connect`

- [ ] **Step 1: Write failing group and connection CRUD tests**

```python
import pytest

from apps.nvda_remote.connections import ConnectionManager, JsonConnectionStore


def manager(tmp_path):
    return ConnectionManager(JsonConnectionStore(tmp_path / "connections.json"))


def test_group_crud_moves_deleted_group_connections_to_default(tmp_path):
    service = manager(tmp_path)
    assert service.create_group(" Work ") is True
    saved = service.add_connection("Work", name="Office", host="relay.example", port=6837, key="secret")
    assert service.rename_group("Work", "Clients") is True
    assert service.delete_groups(["Clients"]) is True
    assert service.groups == ("Default",)
    assert service.connections("Default") == (saved,)


def test_default_group_cannot_be_renamed_or_deleted(tmp_path):
    service = manager(tmp_path)
    assert service.rename_group("Default", "Other") is False
    assert service.delete_groups(["Default"]) is False


def test_connection_update_delete_and_reload(tmp_path):
    service = manager(tmp_path)
    saved = service.add_connection("Default", name="Old", host="one.example", port=6837, key="one")
    updated = service.update_connection(
        "Default", saved.id, name="New", host="two.example", port=7000, key="two", insecure=True
    )
    assert updated.name == "New"
    reloaded = manager(tmp_path)
    assert reloaded.find_connection(saved.id) == updated
    assert reloaded.delete_connections("Default", [saved.id]) is True
    assert reloaded.find_connection(saved.id) is None
```

- [ ] **Step 2: Write failing search, filtered ordering, preference, and rollback tests**

```python
def test_search_and_swap_visible_filtered_connections(tmp_path):
    service = manager(tmp_path)
    first = service.add_connection("Default", name="Alpha", host="a.example", port=6837, key="1")
    hidden = service.add_connection("Default", name="Hidden", host="zz.test", port=6837, key="2")
    second = service.add_connection("Default", name="Another", host="b.example", port=6837, key="3")
    assert service.search("Default", "a") == (first, second)
    assert service.swap_connections("Default", first.id, second.id) is True
    assert service.connections("Default") == (second, hidden, first)


def test_deleting_quick_connection_clears_default(tmp_path):
    service = manager(tmp_path)
    saved = service.add_connection("Default", name="Office", host="relay.example", port=6837, key="secret")
    service.set_quick_connect(saved.id)
    assert service.quick_connection == saved
    service.delete_connections("Default", [saved.id])
    assert service.quick_connection is None


def test_stale_quick_id_is_unavailable(tmp_path):
    service = manager(tmp_path)
    service._catalog.quick_connect_id = "missing"
    assert service.quick_connection is None


def test_failed_save_does_not_publish_in_memory_mutation(tmp_path, monkeypatch):
    service = manager(tmp_path)
    monkeypatch.setattr(service._store, "save", lambda _catalog: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(OSError, match="disk"):
        service.create_group("Unsaved")
    assert service.groups == ("Default",)
```

- [ ] **Step 3: Run manager tests to verify RED**

Run: `pytest tests/unit/test_nvda_remote_connection_manager.py -v`

Expected: FAIL because `ConnectionManager` is not exported.

- [ ] **Step 4: Implement transactional catalog operations**

```python
# src/apps/nvda_remote/connections/manager.py
from __future__ import annotations

from copy import deepcopy
from collections.abc import Callable, Iterable

from .models import ConnectionCatalog, DEFAULT_GROUP, SavedConnection
from .store import JsonConnectionStore


class ConnectionManager:
    DEFAULT_GROUP = DEFAULT_GROUP

    def __init__(self, store: JsonConnectionStore) -> None:
        self._store = store
        self._catalog = store.load()

    def _change(self, mutation: Callable[[ConnectionCatalog], object]) -> object:
        candidate = deepcopy(self._catalog)
        result = mutation(candidate)
        self._store.save(candidate)
        self._catalog = candidate
        return result

    @property
    def groups(self) -> tuple[str, ...]:
        return tuple(self._catalog.groups)

    @property
    def active_group(self) -> str:
        return self._catalog.active_group

    def set_active_group(self, group: str) -> bool:
        if group not in self._catalog.groups:
            return False
        self._change(lambda catalog: setattr(catalog, "active_group", group))
        return True

    def create_group(self, name: str) -> bool:
        name = name.strip()
        if not name or name in self._catalog.groups:
            return False
        self._change(lambda catalog: catalog.groups.__setitem__(name, []))
        return True

    def rename_group(self, old_name: str, new_name: str) -> bool:
        new_name = new_name.strip()
        if old_name == DEFAULT_GROUP or old_name not in self._catalog.groups or not new_name or new_name in self._catalog.groups:
            return False
        def mutate(catalog: ConnectionCatalog) -> None:
            rebuilt: dict[str, list[SavedConnection]] = {}
            for name, values in catalog.groups.items():
                rebuilt[new_name if name == old_name else name] = values
            catalog.groups = rebuilt
            if catalog.active_group == old_name:
                catalog.active_group = new_name
        self._change(mutate)
        return True

    def delete_groups(self, names: Iterable[str]) -> bool:
        selected = tuple(dict.fromkeys(names))
        if not selected or DEFAULT_GROUP in selected or any(name not in self._catalog.groups for name in selected):
            return False
        def mutate(catalog: ConnectionCatalog) -> None:
            for name in selected:
                catalog.groups[DEFAULT_GROUP].extend(catalog.groups.pop(name))
            if catalog.active_group in selected:
                catalog.active_group = DEFAULT_GROUP
        self._change(mutate)
        return True

    def connections(self, group: str) -> tuple[SavedConnection, ...]:
        return tuple(self._catalog.groups.get(group, ()))

    def search(self, group: str, query: str) -> tuple[SavedConnection, ...]:
        folded = query.strip().casefold()
        values = self.connections(group)
        if not folded:
            return values
        return tuple(item for item in values if folded in item.name.casefold() or folded in item.host.casefold())

    def add_connection(self, group: str, **values: object) -> SavedConnection:
        if group not in self._catalog.groups:
            raise KeyError(group)
        connection = SavedConnection.create(**values)
        self._change(lambda catalog: catalog.groups[group].append(connection))
        return connection

    def update_connection(self, group: str, connection_id: str, **values: object) -> SavedConnection:
        current = next((item for item in self.connections(group) if item.id == connection_id), None)
        if current is None:
            raise KeyError(connection_id)
        updated = SavedConnection(id=current.id, **values)
        def mutate(catalog: ConnectionCatalog) -> None:
            index = next(i for i, item in enumerate(catalog.groups[group]) if item.id == connection_id)
            catalog.groups[group][index] = updated
        self._change(mutate)
        return updated

    def delete_connections(self, group: str, connection_ids: Iterable[str]) -> bool:
        ids = frozenset(connection_ids)
        if not ids or group not in self._catalog.groups or not ids.issubset({item.id for item in self.connections(group)}):
            return False
        def mutate(catalog: ConnectionCatalog) -> None:
            catalog.groups[group] = [item for item in catalog.groups[group] if item.id not in ids]
            if catalog.quick_connect_id in ids:
                catalog.quick_connect_id = None
        self._change(mutate)
        return True

    def swap_connections(self, group: str, first_id: str, second_id: str) -> bool:
        if first_id == second_id or group not in self._catalog.groups:
            return False
        indexes = {item.id: index for index, item in enumerate(self.connections(group))}
        if first_id not in indexes or second_id not in indexes:
            return False
        def mutate(catalog: ConnectionCatalog) -> None:
            first, second = indexes[first_id], indexes[second_id]
            catalog.groups[group][first], catalog.groups[group][second] = catalog.groups[group][second], catalog.groups[group][first]
        self._change(mutate)
        return True

    def find_connection(self, connection_id: str) -> SavedConnection | None:
        return next((item for group in self._catalog.groups.values() for item in group if item.id == connection_id), None)

    @property
    def close_on_connect(self) -> bool:
        return self._catalog.close_on_connect

    def set_close_on_connect(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise ValueError("close_on_connect must be a boolean")
        self._change(lambda catalog: setattr(catalog, "close_on_connect", value))

    @property
    def quick_connection(self) -> SavedConnection | None:
        value = self._catalog.quick_connect_id
        return None if value is None else self.find_connection(value)

    def set_quick_connect(self, connection_id: str | None) -> None:
        if connection_id is not None and self.find_connection(connection_id) is None:
            raise KeyError(connection_id)
        self._change(lambda catalog: setattr(catalog, "quick_connect_id", connection_id))
```

Export `ConnectionManager` from `connections/__init__.py`.

- [ ] **Step 5: Run Task 3 tests and inspect the diff**

Run: `pytest tests/unit/test_nvda_remote_connection_manager.py -v`

Expected: all Task 3 tests PASS.

Run: `git diff --check && git status --short`

Expected: no whitespace errors and no commit is created.

---

### Task 4: Saved-connection application service and runtime composition

**Files:**
- Modify: `src/apps/nvda_remote/state.py`
- Modify: `src/apps/nvda_remote/service.py`
- Modify: `src/apps/nvda_remote/main.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`
- Modify: `tests/unit/test_app_wx.py`

**Interfaces:**
- Consumes: `ConnectionManager`, `SavedConnection`, `format_connection_url`
- Produces: `ConnectionState.CONNECTING`
- Produces: constructor argument `connection_manager: ConnectionManager`
- Produces: `connect_saved(connection_id: str) -> None`
- Produces: `connect_quick() -> None`
- Produces: `copy_connection_link(connection_id: str) -> str`
- Produces: public `connection_manager` property used by the wx dialogs

- [ ] **Step 1: Write failing service tests for saved, replacement, quick, stale, copy, and failures**

```python
import pytest

from apps.nvda_remote.connections import ConnectionManager, JsonConnectionStore


def build_connection_manager(tmp_path):
    return ConnectionManager(JsonConnectionStore(tmp_path / "connections.json"))


def test_connect_saved_uses_persisted_tls_choice(tmp_path):
    manager = build_connection_manager(tmp_path)
    saved = manager.add_connection(
        "Default", name="Office", host="relay.example", port=7000, key="secret", insecure=True
    )
    service, transport, *_ = build_service(connection_manager=manager)
    service.bind()
    service.connect_saved(saved.id)
    assert service.state.connection_state == ConnectionState.CONNECTING
    assert transport.connected_to == ("relay.example", 7000, True)


def test_connect_saved_replaces_active_connection(tmp_path):
    manager = build_connection_manager(tmp_path)
    saved = manager.add_connection("Default", name="Office", host="relay.example", port=6837, key="secret")
    service, transport, *_ = build_service(connection_manager=manager)
    service.state.connection_state = ConnectionState.CONNECTED
    service.connect_saved(saved.id)
    assert transport.reader_stopped == 1
    assert transport.reader_started == 1


def test_connect_quick_rejects_missing_or_stale_default(tmp_path):
    service, *_ = build_service(connection_manager=build_connection_manager(tmp_path))
    with pytest.raises(LookupError, match="Quick Connect"):
        service.connect_quick()


def test_immediate_connect_failure_returns_to_idle(tmp_path):
    manager = build_connection_manager(tmp_path)
    saved = manager.add_connection("Default", name="Office", host="relay.example", port=6837, key="secret")
    service, transport, *_ = build_service(connection_manager=manager)
    transport.connect_error = OSError("offline")
    with pytest.raises(OSError, match="offline"):
        service.connect_saved(saved.id)
    assert service.state.connection_state == ConnectionState.IDLE


def test_copy_connection_link_writes_clipboard_and_returns_url(tmp_path):
    manager = build_connection_manager(tmp_path)
    saved = manager.add_connection("Default", name="Office", host="relay.example", port=6837, key="secret")
    service, *_ = build_service(connection_manager=manager)
    url = service.copy_connection_link(saved.id)
    assert url == "nvdaremote://relay.example?key=secret&mode=slave"
    assert service.clipboard.text == url
```

Update `FakeTransport.connect` so it records `connected_to` and raises an injected `connect_error`; update `build_service` to create a temporary manager by default so unrelated tests retain concise setup.

```python
# Add these fields to the existing FakeTransport.__init__:
self.connected_to = None
self.connect_error = None
self.closed = 0

def connect(self, host, port, insecure=False):
    if self.connect_error is not None:
        raise self.connect_error
    self.connected_to = (host, port, insecure)

def close(self):
    self.closed += 1

```

- [ ] **Step 2: Run focused service tests to verify RED**

Run: `pytest tests/unit/test_nvda_remote_app_service.py -k 'saved or quick or copy_connection or immediate_connect' -v`

Expected: FAIL because the new constructor argument and methods are absent.

- [ ] **Step 3: Add `CONNECTING` and implement saved-connection orchestration**

```python
# src/apps/nvda_remote/state.py
class ConnectionState(StrEnum):
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
```

```python
# additions in src/apps/nvda_remote/service.py
from apps.nvda_remote.connections import ConnectionManager
from apps.nvda_remote.connections.links import format_connection_url


# Add this keyword-only parameter to NvdaRemoteAppService.__init__:
connection_manager: ConnectionManager,

# Assign it beside the existing transport/input/output dependencies:
self.connection_manager = connection_manager


def connect(self, host: str, port: int, key: str, insecure: bool = False) -> None:
    if self.state.connection_state == ConnectionState.CONNECTING:
        raise RuntimeError("A connection attempt is already in progress")
    self.state.connection_state = ConnectionState.CONNECTING
    try:
        self.session.connect(ConnectionInfo(hostname=host, port=port, key=key, insecure=insecure))
        self.transport.start_reader()
    except Exception:
        self.transport.stop_reader()
        self.session.disconnect()
        raise


def connect_saved(self, connection_id: str) -> None:
    connection = self.connection_manager.find_connection(connection_id)
    if connection is None:
        raise LookupError("Saved connection no longer exists")
    if self.state.connection_state == ConnectionState.CONNECTING:
        raise RuntimeError("A connection attempt is already in progress")
    if self.state.connection_state == ConnectionState.CONNECTED:
        self.disconnect()
    self.connect(connection.host, connection.port, connection.key, connection.insecure)


def connect_quick(self) -> None:
    if self.state.connection_state != ConnectionState.IDLE:
        raise RuntimeError("Quick Connect is available only while disconnected")
    connection = self.connection_manager.quick_connection
    if connection is None:
        raise LookupError("Quick Connect is not configured")
    self.connect_saved(connection.id)


def copy_connection_link(self, connection_id: str) -> str:
    connection = self.connection_manager.find_connection(connection_id)
    if connection is None:
        raise LookupError("Saved connection no longer exists")
    url = format_connection_url(connection)
    self.clipboard.set_text(url)
    return url
```

Keep `disconnect()` valid for both `CONNECTING` and `CONNECTED`, stop active control first, then use the existing typed disconnect event for final state cleanup:

```python
def disconnect(self) -> None:
    if self.state.control_state == ControlState.CONTROLLING:
        self.stop_control()
    elif self.state.connection_state != ConnectionState.IDLE:
        if self._mode_manager.active_mode_id is not None:
            self._mode_manager.exit_active_mode()
        self._activation.exit_active()
    self.transport.stop_reader()
    self.session.disconnect()
```

- [ ] **Step 4: Compose a separate connection settings file**

```python
# additions in src/apps/nvda_remote/main.py
from apps.nvda_remote.connections import ConnectionManager, JsonConnectionStore


connection_store = JsonConnectionStore(default_config_path(app_name="nvda_remote_connections"))
connection_manager = ConnectionManager(connection_store)
app_service = NvdaRemoteAppService(
    connection_manager=connection_manager,
    transport=transport,
    input_capture=parts.input_capture,
    hotkey_capture=parts.hotkey_capture,
    clipboard=parts.clipboard,
    capabilities=parts.output.capabilities,
    main_thread_dispatch=getattr(NvdaRemoteApp, "dispatch", None),
    use_windows_native_key_payload=_use_windows_native_key_payload(),
)
```

Add `connection_manager: ConnectionManager` to `NvdaRemoteRuntime`. Update runtime test fakes so `default_config_path` accepts `app_name="accessibility-toolkit"` and asserts that the manager receives `nvda_remote_connections.json` independently from speech settings.

- [ ] **Step 5: Run service and runtime tests**

Run: `pytest tests/unit/test_nvda_remote_app_service.py tests/unit/test_nvda_remote_use_cases.py tests/unit/test_app_wx.py -k 'nvda_remote_main_build_runtime or saved or quick or copy_connection or immediate_connect or connection' -v`

Expected: all selected service/runtime tests PASS.

Run: `git diff --check && git status --short`

Expected: no whitespace errors and no commit is created.

---

### Task 5: Connection editor and group manager dialogs

**Files:**
- Create: `src/ui/nvda_remote/connection_editor.py`
- Create: `src/ui/nvda_remote/group_manager_dialog.py`
- Modify: `tests/unit/test_app_wx.py`
- Create: `tests/unit/test_nvda_remote_connection_ui.py`

**Interfaces:**
- Consumes: `SavedConnection`, `ConnectionManager`
- Produces: `generate_key() -> str`
- Produces: `ConnectionEditorDialog(parent, initial: SavedConnection | None = None)` with `result: dict[str, object] | None`
- Produces: `GroupManagerDialog(parent, manager: ConnectionManager, on_changed: Callable[[], None])`

At the top of `tests/unit/test_nvda_remote_connection_ui.py`, reuse the repository's wx installer without importing production wx modules before installation:

```python
import importlib
from unittest.mock import patch

from apps.nvda_remote.connections import ConnectionManager, JsonConnectionStore
from tests.unit.test_app_wx import install_fake_wx


def build_manager(tmp_path):
    return ConnectionManager(JsonConnectionStore(tmp_path / "connections.json"))


def load_editor_ui(monkeypatch):
    install_fake_wx(monkeypatch)
    editor_module = importlib.import_module("ui.nvda_remote.connection_editor")
    group_module = importlib.import_module("ui.nvda_remote.group_manager_dialog")
    return editor_module, group_module
```

- [ ] **Step 1: Extend fake wx only for the controls these dialogs use**

Add constants/events `ID_OK`, `ID_CANCEL`, `ID_CLOSE`, `YES`, `NO`, `ICON_WARNING`, `HORIZONTAL`, `ALIGN_CENTER_VERTICAL`, `EVT_CHECKBOX`, and `EVT_LISTBOX`. Add deterministic fakes with the same value/selection APIs used by production code:

Also append these module names to `UI_MODULES` so the existing autouse fixture
clears wx-bound imports between tests:

```python
"ui.nvda_remote.connection_editor",
"ui.nvda_remote.group_manager_dialog",
"ui.nvda_remote.connection_manager_dialog",
```

```python
class Dialog(Frame):
    def __init__(self, parent=None, title="", size=None):
        super().__init__(parent=parent, title=title)
        self.size = size
        self.modal_result = fake_wx.ID_CANCEL
        self.closed = False

    def ShowModal(self):
        return self.modal_result

    def EndModal(self, result):
        self.modal_result = result
        self.closed = True

    def Close(self):
        self.closed = True

    def Destroy(self):
        self.closed = True


class SpinCtrl(TextCtrl):
    def __init__(self, parent, value="6837", min=1, max=65535):
        super().__init__(parent, value=value)
        self.minimum = min
        self.maximum = max

    def GetValue(self):
        return int(super().GetValue())


class CheckBox(Button):
    def __init__(self, parent, label=""):
        super().__init__(parent, label)
        self.value = False

    def SetValue(self, value):
        self.value = bool(value)

    def GetValue(self):
        return self.value
```

Update the existing `TextCtrl.__init__` to accept `style=0`, and add
`Choice.GetStringSelection`, `Choice.SetStringSelection`, and `Choice.Set` because
the dialogs use those public wx methods.

Add a `ListBox` fake supporting `Set`, `GetSelections`, `GetString`, `SetSelection`, and `FindString`. Register all fakes on `fake_wx`.

- [ ] **Step 2: Write failing editor tests**

```python
def test_generate_key_is_seven_decimal_digits(monkeypatch):
    editor_module, _group_module = load_editor_ui(monkeypatch)
    with patch.object(editor_module.secrets, "randbelow", return_value=42):
        assert editor_module.generate_key() == "1000042"


def test_editor_rejects_blank_fields_without_result(monkeypatch):
    fake_wx = install_fake_wx(monkeypatch)
    editor_module = importlib.import_module("ui.nvda_remote.connection_editor")
    dialog = editor_module.ConnectionEditorDialog(None)
    dialog.name_ctrl.SetValue(" ")
    dialog.host_ctrl.SetValue("relay.example")
    dialog.key_ctrl.SetValue("secret")
    dialog._on_ok(None)
    assert dialog.result is None
    assert fake_wx.message_box_calls[-1][1] == "Invalid Connection"


def test_editor_returns_trimmed_values_and_insecure_choice(monkeypatch):
    editor_module, _group_module = load_editor_ui(monkeypatch)
    dialog = editor_module.ConnectionEditorDialog(None)
    dialog.name_ctrl.SetValue(" Office ")
    dialog.host_ctrl.SetValue(" relay.example ")
    dialog.port_ctrl.SetValue("7000")
    dialog.key_ctrl.SetValue(" secret ")
    dialog.insecure_ctrl.SetValue(True)
    dialog._on_ok(None)
    assert dialog.result == {
        "name": "Office", "host": "relay.example", "port": 7000, "key": "secret", "insecure": True
    }
```

- [ ] **Step 3: Implement the editor**

Use labeled `wx.StaticText` controls, a masked key `wx.TextCtrl(parent, style=wx.TE_PASSWORD)`, `wx.SpinCtrl`, an explicit **Disable TLS certificate validation** checkbox, Generate Key, OK, and Cancel. `_on_ok` must call `SavedConnection.create(name=name, host=host, port=port, key=key, insecure=insecure)` to reuse domain validation, catch `ValueError`, call `wx.MessageBox`, and set `result` only for valid data. `generate_key` is exactly:

```python
import secrets


def generate_key() -> str:
    return str(1_000_000 + secrets.randbelow(9_000_000))


def _on_ok(self, _event) -> None:
    try:
        validated = SavedConnection.create(
            name=self.name_ctrl.GetValue(),
            host=self.host_ctrl.GetValue(),
            port=self.port_ctrl.GetValue(),
            key=self.key_ctrl.GetValue(),
            insecure=self.insecure_ctrl.GetValue(),
        )
    except ValueError as error:
        wx.MessageBox(str(error), "Invalid Connection", wx.OK | wx.ICON_ERROR)
        return
    self.result = {
        "name": validated.name,
        "host": validated.host,
        "port": validated.port,
        "key": validated.key,
        "insecure": validated.insecure,
    }
    self.EndModal(wx.ID_OK)
```

- [ ] **Step 4: Write failing group-manager tests**

```python
def test_group_manager_disables_rename_and_delete_for_default(tmp_path, monkeypatch):
    _editor_module, group_module = load_editor_ui(monkeypatch)
    dialog = group_module.GroupManagerDialog(None, build_manager(tmp_path), lambda: None)
    dialog.group_list.SetSelection(0)
    dialog._sync_actions()
    assert dialog.rename_button.enabled is False
    assert dialog.delete_button.enabled is False


def test_group_manager_deletes_selected_groups_and_moves_connections(tmp_path, monkeypatch):
    fake_wx = install_fake_wx(monkeypatch)
    group_module = importlib.import_module("ui.nvda_remote.group_manager_dialog")
    manager = build_manager(tmp_path)
    manager.create_group("One")
    manager.create_group("Two")
    manager.add_connection("One", name="Office", host="relay.example", port=6837, key="secret")
    dialog = group_module.GroupManagerDialog(None, manager, lambda: None)
    dialog.group_list.selections = [1, 2]
    fake_wx.message_box_result = fake_wx.YES
    dialog._on_delete(None)
    assert manager.groups == ("Default",)
    assert len(manager.connections("Default")) == 1
```

- [ ] **Step 5: Implement group CRUD UI and run Task 5 tests**

The dialog calls only `ConnectionManager` methods. Add uses `wx.GetTextFromUser("Enter new group name:", "New Group", parent=self).strip()` and rename uses the same API with title `"Rename Group"` and the current name as `default_value`. Delete gathers all selected non-default group names, confirms once with `wx.MessageBox(message, "Confirm Delete", wx.YES_NO | wx.ICON_WARNING)`, calls `delete_groups`, refreshes, and invokes `on_changed`.

```python
def _on_add(self, _event) -> None:
    name = wx.GetTextFromUser("Enter new group name:", "New Group", parent=self).strip()
    if name and not self.manager.create_group(name):
        wx.MessageBox("Group already exists or is invalid.", "Invalid Group", wx.OK | wx.ICON_ERROR)
    self._refresh_groups()
    self.on_changed()


def _on_rename(self, _event) -> None:
    selected = self._selected_group_names()
    if len(selected) != 1 or selected[0] == self.manager.DEFAULT_GROUP:
        return
    name = wx.GetTextFromUser(
        "Enter new group name:",
        "Rename Group",
        default_value=selected[0],
        parent=self,
    ).strip()
    if name and not self.manager.rename_group(selected[0], name):
        wx.MessageBox("Group already exists or is invalid.", "Invalid Group", wx.OK | wx.ICON_ERROR)
    self._refresh_groups()
    self.on_changed()


def _on_delete(self, _event) -> None:
    selected = tuple(name for name in self._selected_group_names() if name != self.manager.DEFAULT_GROUP)
    if not selected:
        return
    message = f"Delete {len(selected)} selected group(s)? Connections will be moved to Default."
    if wx.MessageBox(message, "Confirm Delete", wx.YES_NO | wx.ICON_WARNING) != wx.YES:
        return
    self.manager.delete_groups(selected)
    self._refresh_groups()
    self.on_changed()
```

Run: `pytest tests/unit/test_nvda_remote_connection_ui.py -k 'generate_key or editor or group_manager' -v`

Expected: all selected Task 5 tests PASS.

Run: `git diff --check && git status --short`

Expected: no whitespace errors and no commit is created.

---

### Task 6: Searchable connection manager dialog

**Files:**
- Create: `src/ui/nvda_remote/connection_manager_dialog.py`
- Modify: `tests/unit/test_app_wx.py`
- Modify: `tests/unit/test_nvda_remote_connection_ui.py`

**Interfaces:**
- Consumes: `controller.connection_manager`, `controller.connect_saved`, `controller.copy_connection_link`
- Consumes: `ConnectionEditorDialog`, `GroupManagerDialog`
- Produces: `ConnectionManagerDialog(parent, controller, on_changed: Callable[[], None])`

Use this test controller and key-event support in
`tests/unit/test_nvda_remote_connection_ui.py`:

```python
class ConnectionControllerStub:
    def __init__(self, connection_manager):
        self.connection_manager = connection_manager
        self.connect_saved_calls = []
        self.copy_link_calls = []

    def connect_saved(self, connection_id):
        self.connect_saved_calls.append(connection_id)

    def copy_connection_link(self, connection_id):
        self.copy_link_calls.append(connection_id)
        return "copied"


class FakeKeyEvent:
    def __init__(self, key, *, control=False, alt=False, shift=False):
        self.key = key
        self.control = control
        self.alt = alt
        self.shift = shift
        self.skipped = False

    def GetKeyCode(self):
        return self.key

    def ControlDown(self):
        return self.control

    def AltDown(self):
        return self.alt

    def ShiftDown(self):
        return self.shift

    def Skip(self):
        self.skipped = True


def load_manager_dialog(monkeypatch):
    fake_wx = install_fake_wx(monkeypatch)
    module = importlib.import_module("ui.nvda_remote.connection_manager_dialog")
    return fake_wx, module.ConnectionManagerDialog


def build_dialog_with_one_connection(tmp_path, monkeypatch):
    fake_wx, dialog_class = load_manager_dialog(monkeypatch)
    controller = ConnectionControllerStub(build_manager(tmp_path))
    saved = controller.connection_manager.add_connection(
        "Default", name="Office", host="relay.example", port=6837, key="one"
    )
    return fake_wx, dialog_class(None, controller, lambda: None), controller, saved


def build_filtered_dialog(tmp_path, monkeypatch):
    fake_wx, dialog_class = load_manager_dialog(monkeypatch)
    controller = ConnectionControllerStub(build_manager(tmp_path))
    first = controller.connection_manager.add_connection(
        "Default", name="Alpha", host="a.example", port=6837, key="one"
    )
    hidden = controller.connection_manager.add_connection(
        "Default", name="Hidden", host="zz.test", port=6837, key="two"
    )
    second = controller.connection_manager.add_connection(
        "Default", name="Another", host="b.example", port=6837, key="three"
    )
    dialog = dialog_class(None, controller, lambda: None)
    dialog.search_ctrl.SetValue("a")
    dialog._refresh_connections()
    return fake_wx, dialog, controller, first, hidden, second
```

- [ ] **Step 1: Extend fake wx for report-list and context-menu behavior**

Add constants/events used by production code: `LC_REPORT`, `LIST_AUTOSIZE`, `LIST_AUTOSIZE_USEHEADER`, `EVT_LIST_ITEM_ACTIVATED`, `EVT_LIST_ITEM_SELECTED`, `EVT_LIST_ITEM_DESELECTED`, `EVT_CONTEXT_MENU`, `EVT_CHAR_HOOK`, `WXK_RETURN`, `WXK_NUMPAD_ENTER`, `WXK_UP`, `WXK_DOWN`, `WXK_F2`, and `WXK_DELETE`. Implement a `ListCtrl` fake with rows, columns, selection, focus, and the exact methods used by the dialog (`InsertColumn`, `InsertItem`, `SetItem`, `DeleteAllItems`, `GetItemCount`, `GetFirstSelected`, `GetNextSelected`, `Select`, `Focus`). Extend `Menu` with separators, item enabling, destruction, and bound callbacks.

- [ ] **Step 2: Write failing list/search/selection tests**

```python
def test_connection_manager_filters_name_or_host_case_insensitively(tmp_path, monkeypatch):
    _fake_wx, dialog_class = load_manager_dialog(monkeypatch)
    controller = ConnectionControllerStub(build_manager(tmp_path))
    controller.connection_manager.add_connection(
        "Default", name="Office", host="relay.example", port=6837, key="one"
    )
    controller.connection_manager.add_connection(
        "Default", name="Home", host="house.example", port=7000, key="two"
    )
    dialog = dialog_class(None, controller, lambda: None)
    dialog.search_ctrl.SetValue("RELAY")
    dialog._refresh_connections()
    assert [row[0] for row in dialog.connection_list.rows] == ["Office"]


def test_connection_manager_double_click_connects_selected_entry(tmp_path, monkeypatch):
    _fake_wx, dialog_class = load_manager_dialog(monkeypatch)
    controller = ConnectionControllerStub(build_manager(tmp_path))
    saved = controller.connection_manager.add_connection(
        "Default", name="Office", host="relay.example", port=6837, key="one"
    )
    dialog = dialog_class(None, controller, lambda: None)
    dialog.connection_list.Select(0)
    dialog._on_connect(None)
    assert controller.connect_saved_calls == [saved.id]


def test_set_quick_and_delete_refresh_main_window(tmp_path, monkeypatch):
    fake_wx, dialog_class = load_manager_dialog(monkeypatch)
    fake_wx.message_box_result = fake_wx.YES
    changed = []
    controller = ConnectionControllerStub(build_manager(tmp_path))
    saved = controller.connection_manager.add_connection(
        "Default", name="Office", host="relay.example", port=6837, key="one"
    )
    dialog = dialog_class(None, controller, lambda: changed.append(True))
    dialog.connection_list.Select(0)
    dialog._on_set_quick(None)
    assert controller.connection_manager.quick_connection == saved
    dialog._delete_selected(confirm=True)
    assert controller.connection_manager.quick_connection is None
    assert changed == [True, True]
```

- [ ] **Step 3: Implement dialog layout and CRUD dispatch**

The dialog owns `_visible_connections: tuple[SavedConnection, ...]`. Group changes call `set_active_group`; search calls `manager.search`; list refresh preserves selection by ID. New/edit open `ConnectionEditorDialog`; delete confirms once and calls `delete_connections`; group management opens `GroupManagerDialog`; close-on-connect writes through `set_close_on_connect`.

Use these action guards exactly:

```python
def _refresh_connections(self, selected_id: str | None = None) -> None:
    group = self.group_choice.GetStringSelection()
    self._visible_connections = self.manager.search(group, self.search_ctrl.GetValue())
    self.connection_list.DeleteAllItems()
    selected_index = 0
    for index, connection in enumerate(self._visible_connections):
        row = self.connection_list.InsertItem(index, connection.name)
        self.connection_list.SetItem(row, 1, connection.host)
        self.connection_list.SetItem(row, 2, str(connection.port))
        if connection.id == selected_id:
            selected_index = index
    if self._visible_connections:
        self.connection_list.Select(selected_index)
        self.connection_list.Focus(selected_index)
    self._sync_actions()


def _selected_connections(self) -> tuple[SavedConnection, ...]:
    indexes: list[int] = []
    index = self.connection_list.GetFirstSelected()
    while index != -1:
        indexes.append(index)
        index = self.connection_list.GetNextSelected(index)
    return tuple(self._visible_connections[index] for index in indexes)


def _on_connect(self, _event) -> None:
    selected = self._selected_connections()
    if len(selected) != 1:
        return
    try:
        self.controller.connect_saved(selected[0].id)
    except Exception as error:
        wx.MessageBox(str(error), "Connection Error", wx.OK | wx.ICON_ERROR)
        return
    self.on_changed()
    if self.manager.close_on_connect:
        self.Close()


def _on_set_quick(self, _event) -> None:
    selected = self._selected_connections()
    if len(selected) != 1:
        return
    self.manager.set_quick_connect(selected[0].id)
    self.on_changed()


def _on_new(self, _event) -> None:
    dialog = ConnectionEditorDialog(self)
    if dialog.ShowModal() == wx.ID_OK and dialog.result is not None:
        created = self.manager.add_connection(
            self.group_choice.GetStringSelection(),
            **dialog.result,
        )
        self._refresh_connections(created.id)
        self.on_changed()
    dialog.Destroy()


def _on_edit(self, _event) -> None:
    selected = self._selected_connections()
    if len(selected) != 1:
        return
    dialog = ConnectionEditorDialog(self, initial=selected[0])
    if dialog.ShowModal() == wx.ID_OK and dialog.result is not None:
        updated = self.manager.update_connection(
            self.group_choice.GetStringSelection(),
            selected[0].id,
            **dialog.result,
        )
        self._refresh_connections(updated.id)
        self.on_changed()
    dialog.Destroy()


def _copy_selected(self) -> None:
    selected = self._selected_connections()
    if len(selected) != 1:
        return
    try:
        self.controller.copy_connection_link(selected[0].id)
    except Exception as error:
        wx.MessageBox(str(error), "Copy Link Error", wx.OK | wx.ICON_ERROR)


def _delete_selected(self, *, confirm: bool = True) -> None:
    selected = self._selected_connections()
    if not selected:
        return
    if confirm and wx.MessageBox(
        f"Delete {len(selected)} selected connection(s)?",
        "Confirm Delete",
        wx.YES_NO | wx.ICON_WARNING,
    ) != wx.YES:
        return
    group = self.group_choice.GetStringSelection()
    self.manager.delete_connections(group, [item.id for item in selected])
    self._refresh_connections()
    self.on_changed()
```

- [ ] **Step 4: Write failing shortcut, filtered-move, copy, and context tests**

```python
def test_filtered_alt_down_swaps_adjacent_visible_entries(tmp_path, monkeypatch):
    _fake_wx, dialog, controller, first, hidden, second = build_filtered_dialog(tmp_path, monkeypatch)
    dialog.connection_list.Select(0)
    dialog._move_selected(1)
    assert controller.connection_manager.connections("Default") == (second, hidden, first)


def test_ctrl_c_copies_only_single_selection(tmp_path, monkeypatch):
    _fake_wx, dialog, controller, saved = build_dialog_with_one_connection(tmp_path, monkeypatch)
    dialog.connection_list.Select(0)
    dialog._copy_selected()
    assert controller.copy_link_calls == [saved.id]


def test_plain_enter_connects_but_shift_enter_has_no_reversed_action(tmp_path, monkeypatch):
    fake_wx, dialog, controller, saved = build_dialog_with_one_connection(tmp_path, monkeypatch)
    dialog.connection_list.Select(0)
    dialog._on_list_key(FakeKeyEvent(fake_wx.WXK_RETURN))
    assert controller.connect_saved_calls == [saved.id]
    dialog._on_list_key(FakeKeyEvent(fake_wx.WXK_RETURN, shift=True))
    assert controller.connect_saved_calls == [saved.id]
```

- [ ] **Step 5: Implement context menu and keyboard mapping**

Implement exactly these applicable bindings: Enter connects; `Alt+Up/Down` calls `_move_selected`; `F2` edits one; Delete deletes one or many; `Ctrl+A` selects all visible rows; `Ctrl+C` copies exactly one. The context menu contains Connect, Edit, Copy Link, Set as Quick Connect, Move Up, Move Down, and Delete. Do not create Connect Reversed or Auto-Connect-at-startup actions.

```python
def _on_list_key(self, event) -> None:
    key = event.GetKeyCode()
    if event.AltDown() and not event.ControlDown() and not event.ShiftDown():
        if key == wx.WXK_UP:
            self._move_selected(-1)
            return
        if key == wx.WXK_DOWN:
            self._move_selected(1)
            return
    if event.ControlDown() and not event.AltDown() and not event.ShiftDown():
        if key == ord("A"):
            for index in range(self.connection_list.GetItemCount()):
                self.connection_list.Select(index)
            return
        if key == ord("C"):
            self._copy_selected()
            return
    if not event.ControlDown() and not event.AltDown() and not event.ShiftDown():
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._on_connect(event)
            return
        if key == wx.WXK_F2:
            self._on_edit(event)
            return
        if key == wx.WXK_DELETE:
            self._delete_selected()
            return
    event.Skip()


def _move_selected(self, direction: int) -> None:
    selected = self._selected_connections()
    if len(selected) != 1:
        return
    index = self._visible_connections.index(selected[0])
    target = index + direction
    if not 0 <= target < len(self._visible_connections):
        return
    self.manager.swap_connections(
        self.group_choice.GetStringSelection(),
        selected[0].id,
        self._visible_connections[target].id,
    )
    self._refresh_connections(selected[0].id)
```

- [ ] **Step 6: Run Task 6 tests and inspect the diff**

Run: `pytest tests/unit/test_nvda_remote_connection_ui.py -v`

Expected: all manager/editor/group UI tests PASS.

Run: `git diff --check && git status --short`

Expected: no whitespace errors and no commit is created.

---

### Task 7: Main-frame saved-only workflow

**Files:**
- Modify: `src/ui/nvda_remote/main_frame.py`
- Modify: `tests/unit/test_app_wx.py`

**Interfaces:**
- Consumes: `ConnectionManagerDialog`, `controller.connect_quick`, `controller.disconnect`, `controller.connection_manager.quick_connection`, `controller.state`
- Produces: buttons `manage_connections_button`, `quick_connect_button`, `disconnect_button`
- Removes: `host_ctrl`, `port_ctrl`, `key_ctrl`, `connect_button`, `_on_connect`, `_sync_connection_fields`, and automatic TLS retry.

- [ ] **Step 1: Replace old manual-entry tests with failing saved-only tests**

```python
def test_main_frame_exposes_saved_connection_actions_not_manual_fields(monkeypatch, tmp_path):
    install_fake_wx(monkeypatch)
    controller = FakeController(connection_manager=build_manager(tmp_path))
    frame = MainFrame(controller=controller)
    assert not hasattr(frame, "host_ctrl")
    assert not hasattr(frame, "port_ctrl")
    assert not hasattr(frame, "key_ctrl")
    assert frame.manage_connections_button.GetLabel() == "Manage Connections..."
    assert frame.quick_connect_button.enabled is False
    assert frame.disconnect_button.enabled is False


def test_main_frame_enables_quick_only_for_valid_default_while_idle(monkeypatch, tmp_path):
    install_fake_wx(monkeypatch)
    manager = build_manager(tmp_path)
    saved = manager.add_connection("Default", name="Office", host="relay.example", port=6837, key="secret")
    manager.set_quick_connect(saved.id)
    controller = FakeController(connection_manager=manager)
    frame = MainFrame(controller=controller)
    assert frame.quick_connect_button.enabled is True
    frame._on_quick_connect(None)
    assert controller.connect_quick_calls == 1


def test_main_frame_action_states_for_connecting_connected_and_idle(monkeypatch, tmp_path):
    install_fake_wx(monkeypatch)
    controller = FakeController(connection_manager=build_manager(tmp_path))
    frame = MainFrame(controller=controller)
    controller.state.connection_state = "connecting"
    frame._sync_connection_actions()
    assert frame.manage_connections_button.enabled is False
    assert frame.quick_connect_button.enabled is False
    assert frame.disconnect_button.enabled is True
    controller.state.connection_state = "connected"
    frame._sync_connection_actions()
    assert frame.manage_connections_button.enabled is True
    assert frame.quick_connect_button.enabled is False
    assert frame.disconnect_button.enabled is True
```

Delete or rewrite old tests that set `host_ctrl`, expect automatic insecure retry, or treat Connect as a Connect/Disconnect toggle. Retain control-mode, clipboard, status-listener, and close-to-tray coverage.

- [ ] **Step 2: Run main-frame tests to verify RED**

Run: `pytest tests/unit/test_app_wx.py -k 'main_frame' -v`

Expected: FAIL because the current frame still exposes manual fields and lacks the three new actions.

- [ ] **Step 3: Implement the saved-only main frame**

```python
from apps.nvda_remote.state import ConnectionState
from ui.nvda_remote.connection_manager_dialog import ConnectionManagerDialog


def _connection_state(self) -> str:
    if self.controller is None or not hasattr(self.controller, "state"):
        return ConnectionState.IDLE
    return getattr(self.controller.state, "connection_state", ConnectionState.IDLE)


def _sync_connection_actions(self) -> None:
    state = self._connection_state()
    is_idle = state == ConnectionState.IDLE
    is_connecting = state == ConnectionState.CONNECTING
    has_quick = bool(
        self.controller is not None
        and self.controller.connection_manager.quick_connection is not None
    )
    self.manage_connections_button.Enable(not is_connecting)
    self.quick_connect_button.Enable(is_idle and has_quick)
    self.disconnect_button.Enable(not is_idle)


def _is_connected(self) -> bool:
    return self._connection_state() == ConnectionState.CONNECTED


def _on_manage_connections(self, _event) -> None:
    dialog = ConnectionManagerDialog(self, self.controller, self._sync_connection_actions)
    dialog.ShowModal()
    dialog.Destroy()
    self._sync_connection_actions()


def _on_quick_connect(self, _event) -> None:
    try:
        self.controller.connect_quick()
    except Exception as error:
        self._show_error(str(error), "Connection Error")
    self._sync_all_controls()


def _on_disconnect(self, _event) -> None:
    self.controller.disconnect()
    self._sync_all_controls()
```

Construct and bind the three buttons before the existing Start Control and Push Clipboard buttons. `_sync_all_controls` calls `_sync_connection_actions`, `_sync_control_button`, and `_sync_clipboard_button`. Control and clipboard remain enabled only for `ConnectionState.CONNECTED`, not `CONNECTING`.

- [ ] **Step 4: Run main-frame and app-shell tests**

Run: `pytest tests/unit/test_app_wx.py -k 'main_frame or nvda_remote_app or nvda_remote_main' -v`

Expected: all selected tests PASS with no references to manual connection fields.

Run: `git diff --check && git status --short`

Expected: no whitespace errors and no commit is created.

---

### Task 8: Documentation, integration coverage, and full verification

**Files:**
- Modify: `README.md`
- Modify: `docs/zh_TW/README.md`
- Modify: `tests/integration/test_relay_session.py`

**Interfaces:**
- Consumes: composed `ConnectionManager`, `NvdaRemoteAppService.connect_saved`, existing fake Relay transport/session.
- Produces: user-facing connection-manager workflow documentation and an end-to-end saved-entry connection test.

- [ ] **Step 1: Add end-to-end saved-catalog integration coverage**

```python
def test_saved_connection_flows_from_json_catalog_to_relay_session(tmp_path):
    store = JsonConnectionStore(tmp_path / "nvda_remote_connections.json")
    manager = ConnectionManager(store)
    saved = manager.add_connection(
        "Default", name="Office", host="example.com", port=6837, key="secret", insecure=True
    )
    manager.set_quick_connect(saved.id)

    service, transport, _capture, _hotkey, _dispatch_calls = build_service(
        connection_manager=ConnectionManager(store)
    )
    service.bind()
    service.connect_quick()

    assert transport.connected_to == ("example.com", 6837, True)
    assert (RemoteMessageType.JOIN, {"channel": "secret", "mode": "master"}) in transport.sent
```

Import `build_service` from `tests.unit.test_nvda_remote_app_service`; it uses the
real `NvdaRemoteAppService` and `RemoteSession` with fake transport/output/capture
boundaries. Import `RemoteMessageType`, `ConnectionManager`, and
`JsonConnectionStore` explicitly in the integration test.

- [ ] **Step 2: Run the integration test against the completed wiring**

Run: `pytest tests/integration/test_relay_session.py::test_saved_connection_flows_from_json_catalog_to_relay_session -v`

Expected: PASS and demonstrate disk reload plus `connect_quick`; no startup code calls `connect_quick()` automatically.

- [ ] **Step 3: Document the workflow in both README files**

Add equivalent English and Traditional Chinese sections stating:

```markdown
### NVDA Remote saved connections

The NVDA Remote main window connects only through saved entries. Open **Manage
Connections**, create a group or connection, then activate the saved entry to
connect. Optionally choose **Set as Quick Connect**; the main-window Quick Connect
button remains disabled until a valid default is configured. Saved keys are kept
in plain text in `nvda_remote_connections.json` beside the other runtime files.
```

The Chinese version must use Taiwanese terms: 「連線」、「連線管理器」、「快速連線」、
「連接埠」、「設定檔」, and 「執行檔」.

- [ ] **Step 4: Run focused connection-manager verification**

Run:

```bash
pytest \
  tests/unit/test_nvda_remote_connection_models.py \
  tests/unit/test_nvda_remote_connection_links.py \
  tests/unit/test_nvda_remote_connection_store.py \
  tests/unit/test_nvda_remote_connection_manager.py \
  tests/unit/test_nvda_remote_connection_ui.py \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_app_wx.py \
  tests/integration/test_relay_session.py -v
```

Expected: all selected tests PASS.

- [ ] **Step 5: Run the complete repository suite**

Run: `pytest tests/unit tests/integration -v`

Expected: all tests PASS with no regressions.

- [ ] **Step 6: Verify source independence and working-tree scope**

Run:

```bash
python3 -c "from apps.nvda_remote.connections import ConnectionManager, JsonConnectionStore, SavedConnection"
rg -n "import (addonHandler|globalVars|_remoteClient)|from (addonHandler|globalVars|_remoteClient)" src/apps/nvda_remote src/ui/nvda_remote
git diff --cached --check
git diff --check
git status --short
```

Expected: the import succeeds; `rg` prints no NVDA runtime imports; `git diff --check` prints nothing; status contains only the intended specs, plan, source, test, and README changes. Do not stage or commit them.

---

## Final Review Checklist

- Each design requirement maps to a task above.
- Both specifications and both README files describe the same saved-only workflow.
- No UI exposes connection mode, reversed connection, local server, or startup auto-connect.
- A stale/deleted quick default disables Quick Connect immediately.
- A connected user can open the manager and switch targets through disconnect-then-connect.
- Connection attempts use the stored `insecure` value and never retry certificate failures implicitly.
- Malformed JSON is preserved on load; atomic-save failure preserves the prior file.
- Filtered movement swaps the adjacent visible items in underlying group order.
- Keyboard and context actions exclude Remote PlusPlus features removed from scope.
- Focused and full test commands pass before completion is claimed.
- No Git commit or staging operation is performed without explicit user authorization.
