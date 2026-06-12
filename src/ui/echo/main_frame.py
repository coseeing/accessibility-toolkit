import wx

from ui.shared.speech_controls import SpeechControlsMixin


class EchoMainFrame(wx.Frame, SpeechControlsMixin):
    def __init__(self, controller):
        super().__init__(parent=None, title="Key Echo Demo")
        self.controller = controller
        if self.controller is not None and hasattr(self.controller, "set_status_listener"):
            self.controller.set_status_listener(self._on_controller_status)

        self.Bind(wx.EVT_CLOSE, self._on_close)

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.status_label = wx.StaticText(panel, label="Stopped")
        self.control_button = wx.Button(panel, label="Start")
        sizer.Add(self.status_label, 0, wx.EXPAND | wx.ALL, 4)
        sizer.Add(self.control_button, 0, wx.EXPAND | wx.ALL, 4)

        self._build_speech_controls(panel, sizer, wx)
        panel.SetSizer(sizer)

        self.control_button.Bind(wx.EVT_BUTTON, self._on_toggle_echo)
        self._bind_speech_control_events(wx)
        self._sync_echo_controls()
        self._sync_speech_backend_choice()
        self._sync_speech_controls()

    def _show_error(self, message: str, caption: str) -> None:
        wx.MessageBox(message, caption, wx.OK | wx.ICON_ERROR)

    def _on_toggle_echo(self, _event):
        if self.controller is None:
            return
        if self._is_echo_running():
            self.controller.stop_echo()
        else:
            try:
                self.controller.start_echo()
            except Exception as error:
                self._show_error(str(error), "Input Error")
                self._sync_echo_controls()
                return
        self._sync_echo_controls()

    def _is_echo_running(self) -> bool:
        if self.controller is None or not hasattr(self.controller, "is_echo_running"):
            return False
        return bool(self.controller.is_echo_running())

    def _sync_echo_controls(self) -> None:
        running = self._is_echo_running()
        self.control_button.SetLabel("Stop" if running else "Start")
        self.status_label.SetLabel("Running" if running else "Stopped")

    def _on_controller_status(self, _status) -> None:
        self._sync_echo_controls()
        self._sync_speech_backend_choice()
        self._sync_speech_controls()

    def _on_close(self, event) -> None:
        self.Hide()
        if hasattr(event, "Veto"):
            event.Veto()
