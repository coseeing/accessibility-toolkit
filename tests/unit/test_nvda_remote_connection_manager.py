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
