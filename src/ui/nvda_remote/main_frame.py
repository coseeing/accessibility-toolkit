import ssl

import wx

from accessibility_toolkit.events import ErrorRaised


class MainFrame(wx.Frame):
    def __init__(self, controller):
        super().__init__(parent=None, title="NVDA Remote Client")
        self.controller = controller
        if self.controller is not None and hasattr(self.controller, "set_status_listener"):
            self.controller.set_status_listener(self._on_controller_status)

        self.Bind(wx.EVT_CLOSE, self._on_close)

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.host_ctrl = wx.TextCtrl(panel)
        self.port_ctrl = wx.TextCtrl(panel, value="6837")
        self.key_ctrl = wx.TextCtrl(panel)
        self.connect_button = wx.Button(panel, label="Connect")
        self.control_button = wx.Button(panel, label="Start Control")
        self.clipboard_button = wx.Button(panel, label="Push Clipboard")

        for widget in (
            self.host_ctrl,
            self.port_ctrl,
            self.key_ctrl,
            self.connect_button,
            self.control_button,
            self.clipboard_button,
        ):
            sizer.Add(widget, 0, wx.EXPAND | wx.ALL, 4)

        panel.SetSizer(sizer)

        self.connect_button.Bind(wx.EVT_BUTTON, self._on_connect)
        self.control_button.Bind(wx.EVT_BUTTON, self._on_start_control)
        self.clipboard_button.Bind(wx.EVT_BUTTON, self._on_push_clipboard)
        self._sync_connect_button_label()
        self._sync_control_button()
        self._sync_connection_fields()
        self._sync_clipboard_button()

    def _show_error(self, message: str, caption: str) -> None:
        wx.MessageBox(message, caption, wx.OK | wx.ICON_ERROR)

    def _on_connect(self, _event):
        if self.controller is None:
            return
        if self._is_connected():
            self.controller.disconnect()
            self._sync_connect_button_label()
            self._sync_control_button()
            self._sync_connection_fields()
            self._sync_clipboard_button()
            return
        try:
            host = self.host_ctrl.GetValue()
            port = int(self.port_ctrl.GetValue())
            key = self.key_ctrl.GetValue()
            self.controller.connect(host, port, key)
        except ssl.SSLCertVerificationError:
            self.controller.connect(host, port, key, insecure=True)
        except Exception as error:
            self._show_error(str(error), "Connection Error")
        self._sync_connect_button_label()
        self._sync_control_button()
        self._sync_connection_fields()
        self._sync_clipboard_button()

    def _on_start_control(self, _event):
        if self.controller is None:
            return
        if self._is_controlling():
            self.controller.stop_control()
        else:
            try:
                self.controller.start_control()
            except Exception as error:
                self._show_error(str(error), "Input Error")
                self._sync_control_button()
                return
        self._sync_control_button()

    def _on_push_clipboard(self, _event):
        if self.controller is None:
            return
        self.controller.push_clipboard()

    def _is_connected(self) -> bool:
        if self.controller is None or not hasattr(self.controller, "state"):
            return False
        return getattr(self.controller.state, "connection_state", "idle") != "idle"

    def _is_controlling(self) -> bool:
        if self.controller is None or not hasattr(self.controller, "state"):
            return False
        return getattr(self.controller.state, "control_state", "idle") == "controlling"

    def _sync_connect_button_label(self) -> None:
        self.connect_button.SetLabel("Disconnect" if self._is_connected() else "Connect")

    def _sync_control_button(self) -> None:
        if not self._is_connected():
            self.control_button.SetLabel("Start Control")
            self.control_button.Disable()
            return
        self.control_button.Enable(True)
        self.control_button.SetLabel(
            "Stop Control" if self._is_controlling() else "Start Control"
        )

    def _sync_connection_fields(self) -> None:
        enabled = not self._is_connected()
        self.host_ctrl.Enable(enabled)
        self.port_ctrl.Enable(enabled)
        self.key_ctrl.Enable(enabled)

    def _sync_clipboard_button(self) -> None:
        clipboard_available = True
        if self.controller is not None and hasattr(
            self.controller, "is_clipboard_available"
        ):
            clipboard_available = bool(self.controller.is_clipboard_available())
        self.clipboard_button.Enable(self._is_connected() and clipboard_available)

    def _on_controller_status(self, status) -> None:
        if isinstance(status, ErrorRaised) and status.message:
            self._show_error(status.message, "Input Error")
        self._sync_connect_button_label()
        self._sync_control_button()
        self._sync_connection_fields()
        self._sync_clipboard_button()

    def _on_close(self, event) -> None:
        self.Hide()
        if hasattr(event, "Veto"):
            event.Veto()
