import importlib
import types
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
    original_choice = fake_wx.Choice

    class Choice(original_choice):
        def SetName(self, name):
            self.name = name

    fake_wx.Choice = Choice
    fake_wx.LC_REPORT = 2048
    fake_wx.LIST_AUTOSIZE = 1
    fake_wx.LIST_AUTOSIZE_USEHEADER = 2
    fake_wx.EVT_LIST_ITEM_ACTIVATED = object()
    fake_wx.EVT_LIST_ITEM_SELECTED = object()
    fake_wx.EVT_LIST_ITEM_DESELECTED = object()
    fake_wx.EVT_CONTEXT_MENU = object()
    fake_wx.EVT_CHAR_HOOK = object()
    fake_wx.WXK_RETURN = 13
    fake_wx.WXK_NUMPAD_ENTER = 271
    fake_wx.WXK_UP = 315
    fake_wx.WXK_DOWN = 317
    fake_wx.WXK_F2 = 113
    fake_wx.WXK_DELETE = 127

    class ListCtrl:
        def __init__(self, parent, style=0):
            self.parent = parent
            self.style = style
            self.rows = []
            self.columns = []
            self.selected = []
            self.focused = -1
            self.bindings = {}

        def InsertColumn(self, index, label):
            self.columns.insert(index, label)

        def InsertItem(self, index, text):
            self.rows.insert(index, [text])
            return index

        def SetItem(self, row, column, text):
            while len(self.rows[row]) <= column:
                self.rows[row].append("")
            self.rows[row][column] = text

        def DeleteAllItems(self):
            self.rows.clear()
            self.selected.clear()
            self.focused = -1

        def GetItemCount(self):
            return len(self.rows)

        def GetFirstSelected(self):
            return min(self.selected) if self.selected else -1

        def GetNextSelected(self, index):
            return next((item for item in sorted(self.selected) if item > index), -1)

        def Select(self, index, select=True):
            if select and index not in self.selected:
                self.selected.append(index)
            elif not select and index in self.selected:
                self.selected.remove(index)

        def Focus(self, index):
            self.focused = index

        def SetFocus(self):
            self.has_focus = True

        def SetName(self, name):
            self.name = name

        def Bind(self, event, handler):
            self.bindings[event] = handler

    fake_wx.ListCtrl = ListCtrl

    class Menu:
        def __init__(self):
            self.items = []
            self.bindings = {}

        def Append(self, id_, label):
            item = types.SimpleNamespace(id=id_, label=label, enabled=True)
            item.GetItemLabelText = lambda: label
            self.items.append(item)
            return item

        def AppendSeparator(self):
            self.items.append(None)

        def Enable(self, id_, enabled):
            for item in self.items:
                if item is not None and item.id == id_:
                    item.enabled = enabled

        def Bind(self, event, handler, id_=None):
            self.bindings[id_] = handler

        def Destroy(self):
            self.destroyed = True

    fake_wx.Menu = Menu
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
    _fake_wx, dialog, controller, saved = build_dialog_with_one_connection(tmp_path, monkeypatch)
    dialog.connection_list.Select(0)
    dialog._on_connect(None)
    assert controller.connect_saved_calls == [saved.id]


def test_set_quick_and_delete_refresh_main_window(tmp_path, monkeypatch):
    fake_wx, dialog, controller, saved = build_dialog_with_one_connection(tmp_path, monkeypatch)
    fake_wx.message_box_result = fake_wx.YES
    changed = []
    dialog.on_changed = lambda: changed.append(True)
    dialog.connection_list.Select(0)
    dialog._on_set_quick(None)
    assert controller.connection_manager.quick_connection == saved
    dialog._delete_selected(confirm=True)
    assert controller.connection_manager.quick_connection is None
    assert changed == [True, True]


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
