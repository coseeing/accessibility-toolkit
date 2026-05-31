import wx


class MainFrame(wx.Frame):
    def __init__(self, controller):
        super().__init__(parent=None, title="NVDA Remote Client")
        self.controller = controller

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

    def _on_connect(self, event):
        if self.controller is None:
            return
        self.controller.connect(
            self.host_ctrl.GetValue(),
            int(self.port_ctrl.GetValue()),
            self.key_ctrl.GetValue(),
        )

    def _on_start_control(self, event):
        if self.controller is None:
            return
        self.controller.start_control()

    def _on_push_clipboard(self, event):
        if self.controller is None:
            return
        self.controller.push_clipboard()
