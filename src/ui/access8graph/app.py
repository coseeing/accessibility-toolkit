import wx

from accessibility_toolkit_wx.shell.tool_app_shell import ToolAppShell
from ui.access8graph.main_frame import Access8GraphMainFrame
from accessibility_toolkit_wx.speech.speech_settings_frame import SpeechSettingsFrame


class Access8GraphApp(wx.App):
    dispatch = staticmethod(wx.CallAfter)

    def __init__(self, controller, speech_controller=None):
        self.controller = controller
        self.speech_controller = speech_controller if speech_controller is not None else controller
        super().__init__(False)

    def OnInit(self):
        self.shell = ToolAppShell(
            controller=self.controller,
            speech_controller=self.speech_controller,
            main_frame_factory=lambda ctrl: Access8GraphMainFrame(controller=ctrl),
            speech_frame_factory=lambda ctrl: SpeechSettingsFrame(controller=ctrl),
            app_name="Access8Graph",
        )
        self.shell.initialize()
        return True

    def OnExit(self):
        return 0
