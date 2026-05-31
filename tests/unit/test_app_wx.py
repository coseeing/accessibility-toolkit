import importlib
import sys
import types


def install_fake_wx(monkeypatch):
    fake_wx = types.ModuleType("wx")
    fake_wx.VERTICAL = 1
    fake_wx.EXPAND = 2
    fake_wx.ALL = 4
    fake_wx.EVT_BUTTON = object()

    class Frame:
        def __init__(self, parent=None, title=""):
            self.parent = parent
            self._title = title
            self.shown = False

        def GetTitle(self):
            return self._title

        def Show(self):
            self.shown = True

    class Panel:
        def __init__(self, parent):
            self.parent = parent
            self.sizer = None

        def SetSizer(self, sizer):
            self.sizer = sizer

    class BoxSizer:
        def __init__(self, orient):
            self.orient = orient
            self.children = []

        def Add(self, widget, proportion, flags, border):
            self.children.append((widget, proportion, flags, border))

    class TextCtrl:
        def __init__(self, parent, value=""):
            self.parent = parent
            self._value = value

        def GetValue(self):
            return self._value

        def SetValue(self, value):
            self._value = value

    class Button:
        def __init__(self, parent, label):
            self.parent = parent
            self._label = label
            self.bindings = {}

        def GetLabel(self):
            return self._label

        def Bind(self, event, handler):
            self.bindings[event] = handler

    class App:
        def __init__(self, redirect=False):
            self.redirect = redirect
            self.top_window = None

        def SetTopWindow(self, frame):
            self.top_window = frame

        def MainLoop(self):
            return 0

    fake_wx.Frame = Frame
    fake_wx.Panel = Panel
    fake_wx.BoxSizer = BoxSizer
    fake_wx.TextCtrl = TextCtrl
    fake_wx.Button = Button
    fake_wx.App = App
    monkeypatch.setitem(sys.modules, "wx", fake_wx)
    sys.modules.pop("app_wx.app", None)
    sys.modules.pop("app_wx.main_frame", None)
    return fake_wx


class FakeController:
    def __init__(self):
        self.connected_to = None
        self.started_control = 0
        self.pushed_clipboard = 0

    def connect(self, host, port, key):
        self.connected_to = (host, port, key)

    def start_control(self):
        self.started_control += 1

    def push_clipboard(self):
        self.pushed_clipboard += 1


def test_main_frame_exposes_connect_controls(monkeypatch):
    install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("app_wx.main_frame").MainFrame

    frame = MainFrame(controller=None)

    assert frame.GetTitle() == "NVDA Remote Client"
    assert frame.host_ctrl.GetValue() == ""
    assert frame.port_ctrl.GetValue() == "6837"
    assert frame.key_ctrl.GetValue() == ""
    assert frame.connect_button.GetLabel() == "Connect"
    assert frame.control_button.GetLabel() == "Start Control"
    assert frame.clipboard_button.GetLabel() == "Push Clipboard"


def test_main_frame_dispatches_button_actions(monkeypatch):
    install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("app_wx.main_frame").MainFrame
    controller = FakeController()
    frame = MainFrame(controller=controller)
    frame.host_ctrl.SetValue("relay.example")
    frame.port_ctrl.SetValue("7000")
    frame.key_ctrl.SetValue("secret")

    frame._on_connect(None)
    frame._on_start_control(None)
    frame._on_push_clipboard(None)

    assert controller.connected_to == ("relay.example", 7000, "secret")
    assert controller.started_control == 1
    assert controller.pushed_clipboard == 1


def test_nvda_remote_app_creates_and_shows_main_frame(monkeypatch):
    install_fake_wx(monkeypatch)
    NvdaRemoteApp = importlib.import_module("app_wx.app").NvdaRemoteApp
    controller = FakeController()
    app = NvdaRemoteApp(controller=controller)

    assert app.OnInit() is True
    assert app.top_window.GetTitle() == "NVDA Remote Client"
    assert app.top_window.shown is True
