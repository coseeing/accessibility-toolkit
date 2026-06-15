from pathlib import Path

import wx


class Access8GraphMainFrame(wx.Frame):
    def __init__(self, controller):
        super().__init__(parent=None, title="Access8Graph")
        self.controller = controller
        if self.controller is not None and hasattr(self.controller, "set_status_listener"):
            self.controller.set_status_listener(self._on_controller_status)

        self.Bind(wx.EVT_CLOSE, self._on_close)

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.status_label = wx.StaticText(panel, label="No file selected")
        self.choose_button = wx.Button(panel, label="Choose GraphML...")
        self.navigation_button = wx.Button(panel, label="Start Navigation")

        sizer.Add(self.status_label, 0, wx.EXPAND | wx.ALL, 4)
        sizer.Add(self.choose_button, 0, wx.EXPAND | wx.ALL, 4)
        sizer.Add(self.navigation_button, 0, wx.EXPAND | wx.ALL, 4)
        panel.SetSizer(sizer)

        self.choose_button.Bind(wx.EVT_BUTTON, self._on_choose_graphml)
        self.navigation_button.Bind(wx.EVT_BUTTON, self._on_toggle_navigation)
        self._sync_controls()

    def _show_error(self, message: str, caption: str) -> None:
        wx.MessageBox(message, caption, wx.OK | wx.ICON_ERROR)

    def _on_choose_graphml(self, _event) -> None:
        if self.controller is None:
            return
        with wx.FileDialog(
            self,
            "Choose GraphML file",
            wildcard="GraphML files (*.graphml)|*.graphml",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            try:
                self.controller.choose_graphml(dialog.GetPath())
            except Exception as error:
                self._show_error(str(error), "GraphML Error")
        self._sync_controls()

    def _on_toggle_navigation(self, _event) -> None:
        if self.controller is None:
            return
        if self._is_navigation_running():
            self.controller.stop_navigation()
        else:
            try:
                self.controller.start_navigation()
            except Exception as error:
                self._show_error(str(error), "Input Error")
        self._sync_controls()

    def _is_navigation_running(self) -> bool:
        if self.controller is None or not hasattr(self.controller, "is_navigation_running"):
            return False
        return bool(self.controller.is_navigation_running())

    def _selected_path(self) -> str | None:
        if self.controller is None or not hasattr(self.controller, "get_selected_graphml_path"):
            return None
        return self.controller.get_selected_graphml_path()

    def _sync_controls(self) -> None:
        running = self._is_navigation_running()
        selected_path = self._selected_path()
        self.navigation_button.SetLabel(
            "Stop Navigation" if running else "Start Navigation"
        )
        self.navigation_button.Enable(bool(selected_path) or running)
        if running:
            self.status_label.SetLabel("Navigation running")
        elif selected_path:
            self.status_label.SetLabel(Path(selected_path).name)
        else:
            self.status_label.SetLabel("No file selected")

    def _on_controller_status(self, status) -> None:
        if isinstance(status, dict) and status.get("kind") == "error":
            self.status_label.SetLabel(str(status.get("message", "")))
        self._sync_controls()

    def _on_close(self, event) -> None:
        self.Hide()
        if hasattr(event, "Veto"):
            event.Veto()
