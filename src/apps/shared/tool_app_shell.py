import wx

from apps.shared.panel_controller import PanelController
from apps.shared.tray_icon import ToolTrayIcon


class ToolAppShell:
    def __init__(
        self,
        *,
        controller,
        main_frame_factory,
        speech_frame_factory,
        speech_controller=None,
        app_name="NVDA Remote",
    ):
        self.controller = controller
        self.speech_controller = speech_controller if speech_controller is not None else controller
        self.main_frame_factory = main_frame_factory
        self.speech_frame_factory = speech_frame_factory
        self.app_name = app_name
        self.panel_controller = PanelController()
        self.tray_icon = None

    def initialize(self):
        if self.tray_icon is not None:
            return
        main_frame = self.main_frame_factory(self.controller)
        speech_frame = self.speech_frame_factory(self.speech_controller)
        self.panel_controller.register("main", main_frame)
        self.panel_controller.register("speech", speech_frame)
        self.tray_icon = ToolTrayIcon(
            on_open_main=lambda: self.panel_controller.show("main"),
            on_open_speech=lambda: self.panel_controller.show("speech"),
            on_exit=self.shutdown,
            app_name=self.app_name,
        )
        self.panel_controller.show("main")

    def shutdown(self):
        if self.tray_icon is not None:
            self.tray_icon.Destroy()
        if self.controller is not None and hasattr(self.controller, "shutdown"):
            self.controller.shutdown()
        wx.GetApp().ExitMainLoop()
