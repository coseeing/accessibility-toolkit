import wx

from ui.echo.main_frame import EchoMainFrame
from ui.shared.speech_settings_frame import SpeechSettingsFrame
from apps.shared.tool_app_shell import ToolAppShell


class EchoApp(wx.App):
    dispatch = staticmethod(wx.CallAfter)

    def __init__(self, controller):
        self.controller = controller
        super().__init__(False)

    def OnInit(self):
        self.shell = ToolAppShell(
            controller=self.controller,
            main_frame_factory=lambda ctrl: EchoMainFrame(controller=ctrl),
            speech_frame_factory=lambda ctrl: SpeechSettingsFrame(controller=ctrl),
            app_name="Key Echo",
        )
        self.shell.initialize()
        return True

    def OnExit(self):
        return 0
