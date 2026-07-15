import wx

from accessibility_toolkit.events import ErrorRaised
from apps.nvda_remote.state import ConnectionState

from .connection_manager_dialog import ConnectionManagerDialog


class MainFrame(wx.Frame):
    def __init__(self, controller):
        super().__init__(parent=None, title="NVDA Remote Client")
        self.controller = controller
        if self.controller is not None and hasattr(self.controller, "set_status_listener"):
            self.controller.set_status_listener(self._on_controller_status)

        self.Bind(wx.EVT_CLOSE, self._on_close)

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.manage_connections_button = wx.Button(
            panel, label="Manage Connections..."
        )
        self.quick_connect_button = wx.Button(panel, label="Quick Connect")
        self.disconnect_button = wx.Button(panel, label="Disconnect")
        self.control_button = wx.Button(panel, label="Start Control")
        self.clipboard_button = wx.Button(panel, label="Push Clipboard")

        for widget in (
            self.manage_connections_button,
            self.quick_connect_button,
            self.disconnect_button,
            self.control_button,
            self.clipboard_button,
        ):
            sizer.Add(widget, 0, wx.EXPAND | wx.ALL, 4)

        panel.SetSizer(sizer)

        self.manage_connections_button.Bind(wx.EVT_BUTTON, self._on_manage_connections)
        self.quick_connect_button.Bind(wx.EVT_BUTTON, self._on_quick_connect)
        self.disconnect_button.Bind(wx.EVT_BUTTON, self._on_disconnect)
        self.control_button.Bind(wx.EVT_BUTTON, self._on_start_control)
        self.clipboard_button.Bind(wx.EVT_BUTTON, self._on_push_clipboard)
        self._sync_all_controls()
        self.manage_connections_button.SetFocus()

    def _show_error(self, message: str, caption: str) -> None:
        wx.MessageBox(message, caption, wx.OK | wx.ICON_ERROR)

    def _connection_state(self) -> str:
        if self.controller is None or not hasattr(self.controller, "state"):
            return ConnectionState.IDLE
        return getattr(self.controller.state, "connection_state", ConnectionState.IDLE)

    def _sync_connection_actions(self) -> None:
        state = self._connection_state()
        is_idle = state == ConnectionState.IDLE
        is_connecting = state == ConnectionState.CONNECTING
        manager = getattr(self.controller, "connection_manager", None)
        has_quick = bool(manager is not None and manager.quick_connection is not None)
        self.manage_connections_button.Enable(not is_connecting)
        self.quick_connect_button.Enable(is_idle and has_quick)
        self.disconnect_button.Enable(state == ConnectionState.CONNECTED)

    def _on_manage_connections(self, _event) -> None:
        if self.controller is None:
            return
        dialog = ConnectionManagerDialog(
            self, self.controller, self._sync_connection_actions
        )
        dialog.ShowModal()
        dialog.Destroy()
        self._sync_connection_actions()

    def _on_quick_connect(self, _event) -> None:
        if self.controller is None:
            return
        try:
            self.controller.connect_quick()
        except Exception as error:
            self._show_error(str(error), "Connection Error")
        self._sync_all_controls()

    def _on_disconnect(self, _event) -> None:
        if self.controller is None:
            return
        self.controller.disconnect()
        self._sync_all_controls()

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
        return self._connection_state() == ConnectionState.CONNECTED

    def _is_controlling(self) -> bool:
        if self.controller is None or not hasattr(self.controller, "state"):
            return False
        return getattr(self.controller.state, "control_state", "idle") == "controlling"

    def _sync_control_button(self) -> None:
        if not self._is_connected():
            self.control_button.SetLabel("Start Control")
            self.control_button.Disable()
            return
        self.control_button.Enable(True)
        self.control_button.SetLabel(
            "Stop Control" if self._is_controlling() else "Start Control"
        )

    def _sync_clipboard_button(self) -> None:
        clipboard_available = True
        if self.controller is not None and hasattr(
            self.controller, "is_clipboard_available"
        ):
            clipboard_available = bool(self.controller.is_clipboard_available())
        self.clipboard_button.Enable(self._is_connected() and clipboard_available)

    def _sync_all_controls(self) -> None:
        self._sync_connection_actions()
        self._sync_control_button()
        self._sync_clipboard_button()

    def _on_controller_status(self, status) -> None:
        if isinstance(status, ErrorRaised) and status.message:
            self._show_error(status.message, "Input Error")
        self._sync_all_controls()

    def _on_close(self, event) -> None:
        self.Hide()
        if hasattr(event, "Veto"):
            event.Veto()
