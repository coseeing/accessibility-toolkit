import json
import os

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


@pytest.mark.parametrize("format_version", [99, True, 1.0, "1"])
def test_non_exact_format_version_is_treated_as_invalid(tmp_path, format_version):
    path = tmp_path / "connections.json"
    path.write_text(json.dumps({"format_version": format_version, "groups": {"Default": []}}), encoding="utf-8")
    assert JsonConnectionStore(path).load() == ConnectionCatalog.default()


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
