from __future__ import annotations

from collections.abc import Callable

import wx

from apps.nvda_remote.connections import ConnectionManager


class GroupManagerDialog(wx.Dialog):
    def __init__(self, parent, manager: ConnectionManager, on_changed: Callable[[], None]):
        super().__init__(parent, title="Manage Groups", size=(360, 300))
        self.manager = manager
        self.on_changed = on_changed

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.group_list = wx.ListBox(panel, style=wx.LB_EXTENDED)
        self.group_list.SetName("Groups")
        sizer.Add(self.group_list, 1, wx.EXPAND | wx.ALL, 4)

        button_row = wx.BoxSizer(wx.HORIZONTAL)
        self.add_button = wx.Button(panel, wx.ID_ANY, "&Add")
        self.rename_button = wx.Button(panel, wx.ID_ANY, "&Rename")
        self.delete_button = wx.Button(panel, wx.ID_ANY, "&Delete")
        self.close_button = wx.Button(panel, wx.ID_CLOSE, "&Close")
        for button in (self.add_button, self.rename_button, self.delete_button, self.close_button):
            button_row.Add(button, 0, wx.ALL, 4)
        sizer.Add(button_row, 0, wx.ALL, 4)
        panel.SetSizer(sizer)

        self.group_list.Bind(wx.EVT_LISTBOX, self._on_group_selected)
        self.add_button.Bind(wx.EVT_BUTTON, self._on_add)
        self.rename_button.Bind(wx.EVT_BUTTON, self._on_rename)
        self.delete_button.Bind(wx.EVT_BUTTON, self._on_delete)
        self.close_button.Bind(wx.EVT_BUTTON, self._on_close)
        self.close_button.SetDefault()
        self.SetEscapeId(wx.ID_CLOSE)
        self._refresh_groups()
        self.group_list.SetFocus()

    def _selected_group_names(self) -> tuple[str, ...]:
        return tuple(self.group_list.GetString(index) for index in self.group_list.GetSelections())

    def _refresh_groups(self) -> None:
        groups = self.manager.groups
        self.group_list.Set(groups)
        active_index = self.group_list.FindString(self.manager.active_group)
        if active_index >= 0:
            self.group_list.SetSelection(active_index)
        self._sync_actions()

    def _sync_actions(self) -> None:
        selected = self._selected_group_names()
        can_edit = len(selected) == 1 and selected[0] != self.manager.DEFAULT_GROUP
        self.rename_button.Enable(can_edit)
        self.delete_button.Enable(any(name != self.manager.DEFAULT_GROUP for name in selected))

    def _on_group_selected(self, _event) -> None:
        selected = self._selected_group_names()
        if len(selected) == 1:
            self.manager.set_active_group(selected[0])
        self._sync_actions()

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

    def _on_close(self, _event) -> None:
        self.EndModal(wx.ID_CLOSE)
