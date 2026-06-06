import wx

from ui.echo.main_frame import EchoMainFrame


class EchoApp(wx.App):
    dispatch = staticmethod(wx.CallAfter)

    def __init__(self, controller):
        self.controller = controller
        super().__init__(False)

    def OnInit(self):
        frame = EchoMainFrame(controller=self.controller)
        frame.Show()
        self.SetTopWindow(frame)
        return True

    def OnExit(self):
        if self.controller is not None and hasattr(self.controller, "shutdown"):
            self.controller.shutdown()
        elif self.controller is not None and hasattr(self.controller, "stop_echo"):
            self.controller.stop_echo()
        return 0
