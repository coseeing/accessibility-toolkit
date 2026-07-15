from __future__ import annotations

import secrets

import wx

from apps.nvda_remote.connections import SavedConnection


def generate_key() -> str:
    return str(1_000_000 + secrets.randbelow(9_000_000))


class ConnectionEditorDialog(wx.Dialog):
    def __init__(self, parent, initial: SavedConnection | None = None):
        super().__init__(parent, title="Connection", size=(420, 300))
        self.result: dict[str, object] | None = None

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.name_ctrl = wx.TextCtrl(panel, value=initial.name if initial else "")
        self.host_ctrl = wx.TextCtrl(panel, value=initial.host if initial else "")
        self.port_ctrl = wx.SpinCtrl(panel, value=str(initial.port if initial else 6837), min=1, max=65535)
        self.key_ctrl = wx.TextCtrl(
            panel,
            value=initial.key if initial else "",
            style=wx.TE_PASSWORD,
        )
        self.insecure_ctrl = wx.CheckBox(panel, label="Disable TLS certificate validation")
        if initial:
            self.insecure_ctrl.SetValue(initial.insecure)
        self.name_ctrl.SetName("Connection name")
        self.host_ctrl.SetName("Connection host")
        self.port_ctrl.SetName("Connection port")
        self.key_ctrl.SetName("Connection key")
        self.insecure_ctrl.SetName("Disable TLS certificate validation")

        for label, control in (
            ("Name", self.name_ctrl),
            ("Host", self.host_ctrl),
            ("Port", self.port_ctrl),
            ("Key", self.key_ctrl),
        ):
            row = wx.BoxSizer(wx.HORIZONTAL)
            row.Add(wx.StaticText(panel, label=label), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
            row.Add(control, 1, wx.EXPAND | wx.ALL, 4)
            sizer.Add(row, 0, wx.EXPAND, 0)
        sizer.Add(self.insecure_ctrl, 0, wx.ALL, 4)

        button_row = wx.BoxSizer(wx.HORIZONTAL)
        self.generate_button = wx.Button(panel, wx.ID_ANY, "&Generate Key")
        self.ok_button = wx.Button(panel, wx.ID_OK, "&OK")
        self.cancel_button = wx.Button(panel, wx.ID_CANCEL, "&Cancel")
        for button in (self.generate_button, self.ok_button, self.cancel_button):
            button_row.Add(button, 0, wx.ALL, 4)
        sizer.Add(button_row, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
        panel.SetSizer(sizer)

        self.generate_button.Bind(wx.EVT_BUTTON, self._on_generate_key)
        self.ok_button.Bind(wx.EVT_BUTTON, self._on_ok)
        self.cancel_button.Bind(wx.EVT_BUTTON, self._on_cancel)
        self.ok_button.SetDefault()
        self.SetEscapeId(wx.ID_CANCEL)
        self.name_ctrl.SetFocus()

    def _on_generate_key(self, _event) -> None:
        self.key_ctrl.SetValue(generate_key())

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

    def _on_cancel(self, _event) -> None:
        self.EndModal(wx.ID_CANCEL)
