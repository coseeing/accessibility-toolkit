from __future__ import annotations

from collections.abc import Callable, Iterable
from copy import deepcopy

from .models import DEFAULT_GROUP, ConnectionCatalog, SavedConnection
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
        if (
            old_name == DEFAULT_GROUP
            or old_name not in self._catalog.groups
            or not new_name
            or new_name in self._catalog.groups
        ):
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
            catalog.groups[group][first], catalog.groups[group][second] = (
                catalog.groups[group][second],
                catalog.groups[group][first],
            )

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
