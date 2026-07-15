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


def test_editor_uses_accessible_names_and_standard_keyboard_defaults(monkeypatch):
    fake_wx = install_fake_wx(monkeypatch)
    editor_module = importlib.import_module("ui.nvda_remote.connection_editor")
    dialog = editor_module.ConnectionEditorDialog(None)
    assert dialog.name_ctrl.name == "Connection name"
    assert dialog.host_ctrl.name == "Connection host"
    assert dialog.port_ctrl.name == "Connection port"
    assert dialog.key_ctrl.name == "Connection key"
    assert dialog.ok_button.id == fake_wx.ID_OK
    assert dialog.cancel_button.id == fake_wx.ID_CANCEL
    assert dialog.ok_button.is_default is True
    assert dialog.escape_id == fake_wx.ID_CANCEL
    assert dialog.name_ctrl.has_focus is True


def test_group_manager_disables_rename_and_delete_for_default(tmp_path, monkeypatch):
    _editor_module, group_module = load_editor_ui(monkeypatch)
    dialog = group_module.GroupManagerDialog(None, build_manager(tmp_path), lambda: None)
    dialog.group_list.SetSelection(0)
    dialog._sync_actions()
    assert dialog.rename_button.enabled is False
    assert dialog.delete_button.enabled is False


def test_group_manager_has_accessible_multiselect_and_standard_close(monkeypatch, tmp_path):
    fake_wx = install_fake_wx(monkeypatch)
    group_module = importlib.import_module("ui.nvda_remote.group_manager_dialog")
    dialog = group_module.GroupManagerDialog(None, build_manager(tmp_path), lambda: None)
    assert dialog.group_list.name == "Groups"
    assert dialog.group_list.style & fake_wx.LB_EXTENDED
    assert dialog.close_button.id == fake_wx.ID_CLOSE
    assert dialog.close_button.is_default is True
    assert dialog.escape_id == fake_wx.ID_CLOSE
    assert dialog.group_list.has_focus is True


def test_group_manager_deletes_selected_groups_and_moves_connections(tmp_path, monkeypatch):
    fake_wx = install_fake_wx(monkeypatch)
    group_module = importlib.import_module("ui.nvda_remote.group_manager_dialog")
    manager = build_manager(tmp_path)
    manager.create_group("One")
    manager.create_group("Two")
    manager.add_connection("One", name="Office", host="relay.example", port=6837, key="secret")
    dialog = group_module.GroupManagerDialog(None, manager, lambda: None)
    dialog.group_list.SetSelection(1)
    dialog.group_list.SetSelection(2, select=True)
    fake_wx.message_box_result = fake_wx.YES
    dialog._on_delete(None)
    assert manager.groups == ("Default",)
    assert len(manager.connections("Default")) == 1


def test_group_manager_enables_delete_when_default_and_other_group_selected(tmp_path, monkeypatch):
    _editor_module, group_module = load_editor_ui(monkeypatch)
    manager = build_manager(tmp_path)
    manager.create_group("One")
    dialog = group_module.GroupManagerDialog(None, manager, lambda: None)
    dialog.group_list.SetSelection(0)
    dialog.group_list.SetSelection(1, select=True)
    dialog._sync_actions()
    assert dialog.delete_button.enabled is True
