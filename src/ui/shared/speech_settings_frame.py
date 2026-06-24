import wx

from ui.shared.speech_controls import SpeechControlsMixin


class SpeechSettingsFrame(wx.Frame, SpeechControlsMixin):
    def __init__(self, controller):
        super().__init__(parent=None, title="Speech Settings")
        self.controller = controller
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self._build_speech_controls(panel, sizer, wx)
        panel.SetSizer(sizer)
        self._bind_speech_control_events(wx)
        self._sync_speech_engine_choice()
        self._sync_speech_controls()
        self.Bind(wx.EVT_CLOSE, self._on_close)

    def _show_error(self, message: str, caption: str) -> None:
        wx.MessageBox(message, caption, wx.OK | wx.ICON_ERROR)

    def _on_close(self, event) -> None:
        self.Hide()
        if hasattr(event, "Veto"):
            event.Veto()
