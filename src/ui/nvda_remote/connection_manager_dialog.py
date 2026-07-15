from __future__ import annotations

from collections.abc import Callable

import wx

from apps.nvda_remote.connections import ConnectionManager, SavedConnection

from .connection_editor import ConnectionEditorDialog
from .group_manager_dialog import GroupManagerDialog


class ConnectionManagerDialog(wx.Dialog):
    def __init__(self, parent, controller, on_changed: Callable[[], None]):
        super().__init__(parent, title="Manage Connections", size=(700, 500))
        self.controller = controller
        self.manager: ConnectionManager = controller.connection_manager
        self.on_changed = on_changed
        self._visible_connections: tuple[SavedConnection, ...] = ()

        panel = wx.Panel(self)
        outer = wx.BoxSizer(wx.VERTICAL)

        group_row = wx.BoxSizer(wx.HORIZONTAL)
        group_row.Add(wx.StaticText(panel, label="Group"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
        self.group_choice = wx.Choice(panel, choices=self.manager.groups)
        self.group_choice.SetStringSelection(self.manager.active_group)
        self.group_choice.SetName("Connection group")
        group_row.Add(self.group_choice, 1, wx.EXPAND | wx.ALL, 4)
        self.groups_button = wx.Button(panel, wx.ID_ANY, "&Manage Groups")
        group_row.Add(self.groups_button, 0, wx.ALL, 4)
        outer.Add(group_row, 0, wx.EXPAND, 0)

        search_row = wx.BoxSizer(wx.HORIZONTAL)
        search_row.Add(wx.StaticText(panel, label="Search"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
        self.search_ctrl = wx.TextCtrl(panel)
        self.search_ctrl.SetName("Search connections")
        search_row.Add(self.search_ctrl, 1, wx.EXPAND | wx.ALL, 4)
        outer.Add(search_row, 0, wx.EXPAND, 0)

        self.connection_list = wx.ListCtrl(panel, style=wx.LC_REPORT)
        self.connection_list.SetName("Connections")
        for index, label in enumerate(("Name", "Host", "Port")):
            self.connection_list.InsertColumn(index, label)
        outer.Add(self.connection_list, 1, wx.EXPAND | wx.ALL, 4)

        action_row = wx.BoxSizer(wx.HORIZONTAL)
        self.new_button = wx.Button(panel, wx.ID_ANY, "&New")
        self.edit_button = wx.Button(panel, wx.ID_ANY, "&Edit")
        self.delete_button = wx.Button(panel, wx.ID_ANY, "&Delete")
        self.quick_button = wx.Button(panel, wx.ID_ANY, "Set as &Quick Connect")
        self.close_button = wx.Button(panel, wx.ID_CLOSE, "&Close")
        for button in (self.new_button, self.edit_button, self.delete_button, self.quick_button, self.close_button):
            action_row.Add(button, 0, wx.ALL, 4)
        outer.Add(action_row, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)

        self.close_on_connect = wx.CheckBox(panel, label="Close after connecting")
        self.close_on_connect.SetValue(self.manager.close_on_connect)
        outer.Add(self.close_on_connect, 0, wx.ALL, 4)
        panel.SetSizer(outer)

        self.group_choice.Bind(wx.EVT_CHOICE, self._on_group_changed)
        self.search_ctrl.Bind(wx.EVT_TEXT, self._on_search)
        self.connection_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_connect)
        self.connection_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_selection_changed)
        self.connection_list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_selection_changed)
        self.connection_list.Bind(wx.EVT_CONTEXT_MENU, self._on_context_menu)
        self.connection_list.Bind(wx.EVT_CHAR_HOOK, self._on_list_key)
        self.groups_button.Bind(wx.EVT_BUTTON, self._on_manage_groups)
        self.new_button.Bind(wx.EVT_BUTTON, self._on_new)
        self.edit_button.Bind(wx.EVT_BUTTON, self._on_edit)
        self.delete_button.Bind(wx.EVT_BUTTON, self._on_delete)
        self.quick_button.Bind(wx.EVT_BUTTON, self._on_set_quick)
        self.close_on_connect.Bind(wx.EVT_CHECKBOX, self._on_close_on_connect)
        self.close_button.Bind(wx.EVT_BUTTON, self._on_close)
        self.close_button.SetDefault()
        self.SetEscapeId(wx.ID_CLOSE)
        self._refresh_connections()
        self.connection_list.SetFocus()

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

    def _sync_actions(self) -> None:
        selected = self._selected_connections()
        one = len(selected) == 1
        self.edit_button.Enable(one)
        self.quick_button.Enable(one)
        self.delete_button.Enable(bool(selected))

    def _on_group_changed(self, _event) -> None:
        group = self.group_choice.GetStringSelection()
        self.manager.set_active_group(group)
        self._refresh_connections()

    def _on_search(self, _event) -> None:
        self._refresh_connections()

    def _on_selection_changed(self, _event) -> None:
        self._sync_actions()

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
            created = self.manager.add_connection(self.group_choice.GetStringSelection(), **dialog.result)
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
                self.group_choice.GetStringSelection(), selected[0].id, **dialog.result
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
        self.manager.delete_connections(
            self.group_choice.GetStringSelection(), [item.id for item in selected]
        )
        self._refresh_connections()
        self.on_changed()

    def _move_selected(self, direction: int) -> None:
        selected = self._selected_connections()
        if len(selected) != 1:
            return
        index = self._visible_connections.index(selected[0])
        target = index + direction
        if not 0 <= target < len(self._visible_connections):
            return
        self.manager.swap_connections(
            self.group_choice.GetStringSelection(), selected[0].id, self._visible_connections[target].id
        )
        self._refresh_connections(selected[0].id)

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

    def _on_manage_groups(self, _event) -> None:
        dialog = GroupManagerDialog(self, self.manager, self._refresh_group_choices)
        dialog.ShowModal()
        dialog.Destroy()

    def _refresh_group_choices(self) -> None:
        active_group = self.manager.active_group
        self.group_choice.Set(self.manager.groups)
        self.group_choice.SetStringSelection(active_group)
        self._refresh_connections()
        self.on_changed()

    def _on_close_on_connect(self, _event) -> None:
        self.manager.set_close_on_connect(self.close_on_connect.GetValue())
        self.on_changed()

    def _on_context_menu(self, _event) -> None:
        menu = wx.Menu()
        self.context_menu = menu
        selected = self._selected_connections()
        single = len(selected) == 1
        if single:
            index = self._visible_connections.index(selected[0])
            can_move_up = index > 0
            can_move_down = index < len(self._visible_connections) - 1
        else:
            can_move_up = can_move_down = False
        actions = (
            ("Connect", self._on_connect, single),
            ("Edit", self._on_edit, single),
            ("Copy Link", lambda _event: self._copy_selected(), single),
            ("Set as Quick Connect", self._on_set_quick, single),
            ("Move Up", lambda _event: self._move_selected(-1), can_move_up),
            ("Move Down", lambda _event: self._move_selected(1), can_move_down),
            ("Delete", self._on_delete, bool(selected)),
        )
        for label, handler, enabled in actions:
            item = menu.Append(wx.ID_ANY, label)
            item.Enable(enabled)
            menu.Bind(wx.EVT_MENU, handler, id=item.GetId())
        popup = getattr(self, "PopupMenu", None)
        try:
            if popup is not None:
                popup(menu)
        finally:
            menu.Destroy()
            self.context_menu = None

    def _on_delete(self, _event) -> None:
        self._delete_selected()

    def _on_close(self, _event) -> None:
        self.EndModal(wx.ID_CLOSE)
