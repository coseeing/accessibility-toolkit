import wx
import wx.adv


class ToolTrayIcon(wx.adv.TaskBarIcon):
    def __init__(self, *, on_open_main, on_open_speech, on_exit, app_name="NVDA Remote"):
        super().__init__()
        self._on_open_main = on_open_main
        self._on_open_speech = on_open_speech
        self._on_exit = on_exit
        self.SetIcon(
            wx.ArtProvider.GetIcon(
                wx.ART_INFORMATION, wx.ART_OTHER, (16, 16)
            ),
            app_name,
        )

    def CreatePopupMenu(self):
        menu = wx.Menu()
        main_item = menu.Append(wx.ID_ANY, "Main Panel")
        speech_item = menu.Append(wx.ID_ANY, "Speech Settings")
        exit_item = menu.Append(wx.ID_EXIT, "Exit")
        menu.Bind(wx.EVT_MENU, lambda _event: self._on_open_main(), main_item)
        menu.Bind(wx.EVT_MENU, lambda _event: self._on_open_speech(), speech_item)
        menu.Bind(wx.EVT_MENU, lambda _event: self._on_exit(), exit_item)
        return menu
