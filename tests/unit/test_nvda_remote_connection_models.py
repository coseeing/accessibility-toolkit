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


@pytest.mark.parametrize("format_version", [True, 1.0, "1"])
def test_catalog_rejects_non_integer_format_version(format_version):
    payload = ConnectionCatalog.default().to_dict()
    payload["format_version"] = format_version
    with pytest.raises(ValueError, match="format"):
        ConnectionCatalog.from_dict(payload)
