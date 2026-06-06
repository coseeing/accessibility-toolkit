import wx

from ui.nvda_remote.main_frame import MainFrame


class NvdaRemoteApp(wx.App):
    dispatch = staticmethod(wx.CallAfter)

    def __init__(self, controller):
        self.controller = controller
        super().__init__(False)

    def OnInit(self):
        frame = MainFrame(controller=self.controller)
        frame.Show()
        self.SetTopWindow(frame)
        return True

    def OnExit(self):
        if self.controller is not None and hasattr(self.controller, "shutdown"):
            self.controller.shutdown()
        return 0
