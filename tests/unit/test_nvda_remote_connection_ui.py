import importlib
from unittest.mock import patch

from apps.nvda_remote.connections import ConnectionManager, JsonConnectionStore
from tests.unit.test_app_wx import install_fake_wx


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


def test_editor_pairs_visible_mnemonic_labels_with_fields(monkeypatch):
    editor_module, _group_module = load_editor_ui(monkeypatch)
    dialog = editor_module.ConnectionEditorDialog(None)

    assert isinstance(dialog.field_labels, tuple)
    assert [label.GetLabel() for label, _control in dialog.field_labels] == [
        "&Name:",
        "&Host:",
        "&Port:",
        "&Key:",
    ]
    assert [control for _label, control in dialog.field_labels] == [
        dialog.name_ctrl,
        dialog.host_ctrl,
        dialog.port_ctrl,
        dialog.key_ctrl,
    ]

    field_rows = [entry[0] for entry in dialog.panel.sizer.children[:4]]
    for row, (label, control) in zip(field_rows, dialog.field_labels, strict=True):
        assert row.children[0][0] is label
        assert row.children[1][0] is control

    assert dialog.panel.children[:8] == [
        dialog.field_labels[0][0], dialog.name_ctrl,
        dialog.field_labels[1][0], dialog.host_ctrl,
        dialog.field_labels[2][0], dialog.port_ctrl,
        dialog.field_labels[3][0], dialog.key_ctrl,
    ]


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
    fake_wx, dialog, controller, saved = build_dialog_with_one_connection(tmp_path, monkeypatch)
    dialog.connection_list.Select(0)
    dialog.connection_list.bindings[fake_wx.EVT_LIST_ITEM_ACTIVATED](None)
    assert controller.connect_saved_calls == [saved.id]


def test_set_quick_and_delete_refresh_main_window(tmp_path, monkeypatch):
    fake_wx, dialog, controller, saved = build_dialog_with_one_connection(tmp_path, monkeypatch)
    fake_wx.message_box_result = fake_wx.YES
    changed = []
    dialog.on_changed = lambda: changed.append(True)
    dialog.connection_list.Select(0)
    dialog.quick_button.bindings[fake_wx.EVT_BUTTON](None)
    assert controller.connection_manager.quick_connection == saved
    dialog.delete_button.bindings[fake_wx.EVT_BUTTON](None)
    assert controller.connection_manager.quick_connection is None
    assert changed == [True, True]


def test_filtered_alt_down_swaps_adjacent_visible_entries(tmp_path, monkeypatch):
    fake_wx, dialog, controller, first, hidden, second = build_filtered_dialog(tmp_path, monkeypatch)
    dialog.connection_list.Select(0)
    dialog.connection_list.bindings[fake_wx.EVT_CHAR_HOOK](FakeKeyEvent(fake_wx.WXK_DOWN, alt=True))
    assert controller.connection_manager.connections("Default") == (second, hidden, first)
    dialog.connection_list.bindings[fake_wx.EVT_CHAR_HOOK](FakeKeyEvent(fake_wx.WXK_UP, alt=True))
    assert controller.connection_manager.connections("Default") == (first, hidden, second)


def test_ctrl_c_copies_only_single_selection(tmp_path, monkeypatch):
    fake_wx, dialog, controller, saved = build_dialog_with_one_connection(tmp_path, monkeypatch)
    dialog.connection_list.Select(0)
    dialog.connection_list.bindings[fake_wx.EVT_CHAR_HOOK](FakeKeyEvent(ord("C"), control=True))
    assert controller.copy_link_calls == [saved.id]


def test_plain_enter_connects_but_shift_enter_has_no_reversed_action(tmp_path, monkeypatch):
    fake_wx, dialog, controller, saved = build_dialog_with_one_connection(tmp_path, monkeypatch)
    dialog.connection_list.Select(0)
    char_hook = dialog.connection_list.bindings[fake_wx.EVT_CHAR_HOOK]
    plain_enter = FakeKeyEvent(fake_wx.WXK_RETURN)
    char_hook(plain_enter)
    assert controller.connect_saved_calls == [saved.id]
    char_hook(FakeKeyEvent(fake_wx.WXK_RETURN, shift=True))
    assert controller.connect_saved_calls == [saved.id]
    assert plain_enter.skipped is False


def test_bound_f2_and_delete_keyboard_actions(tmp_path, monkeypatch):
    fake_wx, dialog, controller, saved = build_dialog_with_one_connection(tmp_path, monkeypatch)
    char_hook = dialog.connection_list.bindings[fake_wx.EVT_CHAR_HOOK]
    f2 = FakeKeyEvent(fake_wx.WXK_F2)
    dialog.connection_list.Select(0)
    char_hook(f2)
    assert f2.skipped is False
    fake_wx.message_box_result = fake_wx.YES
    char_hook(FakeKeyEvent(fake_wx.WXK_DELETE))
    assert controller.connection_manager.find_connection(saved.id) is None


def test_context_menu_uses_real_wx_ids_and_selection_guards(tmp_path, monkeypatch):
    fake_wx, dialog, controller, first, hidden, second = build_filtered_dialog(tmp_path, monkeypatch)
    dialog.connection_list.Select(0)
    dialog.PopupMenu = lambda menu: setattr(dialog, "shown_menu", menu)
    dialog.connection_list.bindings[fake_wx.EVT_CONTEXT_MENU](None)
    items = {item.GetItemLabelText(): item for item in dialog.shown_menu.GetMenuItems()}
    assert len({item.GetId() for item in items.values()}) == 7
    assert items["Connect"].enabled is True
    assert items["Edit"].enabled is True
    assert items["Copy Link"].enabled is True
    assert items["Set as Quick Connect"].enabled is True
    assert items["Move Up"].enabled is False
    assert items["Move Down"].enabled is True
    assert items["Delete"].enabled is True
    dialog.shown_menu.bindings[items["Copy Link"].GetId()](None)
    assert controller.copy_link_calls == [first.id]
    assert dialog.context_menu is None


def test_context_menu_disables_single_selection_actions_without_selection(tmp_path, monkeypatch):
    fake_wx, dialog, _controller, _saved = build_dialog_with_one_connection(tmp_path, monkeypatch)
    dialog.connection_list.Select(0, select=False)
    dialog.PopupMenu = lambda menu: setattr(dialog, "shown_menu", menu)
    dialog.connection_list.bindings[fake_wx.EVT_CONTEXT_MENU](None)
    items = {item.GetItemLabelText(): item for item in dialog.shown_menu.GetMenuItems()}
    assert all(items[label].enabled is False for label in ("Connect", "Edit", "Copy Link", "Set as Quick Connect"))
    assert items["Move Up"].enabled is False
    assert items["Move Down"].enabled is False
    assert items["Delete"].enabled is False


def test_keyboard_binding_selects_only_visible_rows_and_rejects_multi_copy(tmp_path, monkeypatch):
    fake_wx, dialog, controller, _first, _hidden, _second = build_filtered_dialog(tmp_path, monkeypatch)
    dialog.connection_list.Select(0, select=False)
    char_hook = dialog.connection_list.bindings[fake_wx.EVT_CHAR_HOOK]
    char_hook(FakeKeyEvent(ord("A"), control=True))
    assert dialog.connection_list.selected == [0, 1]
    char_hook(FakeKeyEvent(ord("C"), control=True))
    assert controller.copy_link_calls == []


def test_group_choice_binding_filters_connections_and_dialog_is_accessible(tmp_path, monkeypatch):
    fake_wx, dialog_class = load_manager_dialog(monkeypatch)
    manager = build_manager(tmp_path)
    manager.create_group("Work")
    manager.add_connection("Work", name="Office", host="relay.example", port=6837, key="one")
    controller = ConnectionControllerStub(manager)
    dialog = dialog_class(None, controller, lambda: None)
    dialog.group_choice.SetStringSelection("Work")
    dialog.group_choice.bindings[fake_wx.EVT_CHOICE](None)
    assert [row[0] for row in dialog.connection_list.rows] == ["Office"]
    assert dialog.group_choice.name == "Connection group"
    assert dialog.search_ctrl.name == "Search connections"
    assert dialog.connection_list.name == "Connections"
    assert dialog.connection_list.has_focus is True
    assert dialog.close_button.is_default is True
    assert dialog.escape_id == fake_wx.ID_CLOSE
