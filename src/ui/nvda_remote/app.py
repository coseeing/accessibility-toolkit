import wx

from ui.nvda_remote.main_frame import MainFrame
from accessibility_toolkit_wx.shell.tool_app_shell import ToolAppShell
from accessibility_toolkit_wx.speech.speech_settings_frame import SpeechSettingsFrame


class NvdaRemoteApp(wx.App):
    dispatch = staticmethod(wx.CallAfter)

    def __init__(self, controller, speech_controller=None):
        self.controller = controller
        self.speech_controller = speech_controller if speech_controller is not None else controller
        super().__init__(False)

    def OnInit(self):
        self.shell = ToolAppShell(
            controller=self.controller,
            speech_controller=self.speech_controller,
            main_frame_factory=lambda ctrl: MainFrame(controller=ctrl),
            speech_frame_factory=lambda ctrl: SpeechSettingsFrame(controller=ctrl),
        )
        self.shell.initialize()
        return True

    def OnExit(self):
        return 0
