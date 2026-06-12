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
        )
        self.shell.initialize()
        return True

    def OnExit(self):
        if self.controller is not None and hasattr(self.controller, "shutdown"):
            self.controller.shutdown()
        elif self.controller is not None and hasattr(self.controller, "stop_echo"):
            self.controller.stop_echo()
        return 0
