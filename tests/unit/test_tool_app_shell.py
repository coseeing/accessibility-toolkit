import importlib
import sys
import types

import pytest


UI_MODULES = (
    "apps.shared.tool_app_shell",
    "apps.shared.panel_controller",
    "apps.shared.tray_icon",
)


def clear_ui_modules():
    for module_name in UI_MODULES:
        sys.modules.pop(module_name, None)


@pytest.fixture(autouse=True)
def clean_cache():
    clear_ui_modules()
    yield
    clear_ui_modules()


def install_fake_wx(monkeypatch):
    fake_wx = types.ModuleType("wx")
    fake_wx.ID_ANY = -1
    fake_wx.ID_EXIT = 5000
    fake_wx.EVT_MENU = object()

    class Menu:
        def __init__(self):
            self.items = []

        def Append(self, id_, label):
            item = types.SimpleNamespace(id=id_, label=label, GetItemLabelText=lambda: label)
            self.items.append(item)
            return item

        def Bind(self, event, handler, id_=None):
            pass

        def GetMenuItems(self):
            return self.items

    fake_adv = types.ModuleType("wx.adv")

    class TaskBarIcon:
        def __init__(self, iconType=None):
            self.iconType = iconType
            self.destroyed = False

        def Destroy(self):
            self.destroyed = True

        def SetIcon(self, icon, tooltip=""):
            return True

    fake_adv.TaskBarIcon = TaskBarIcon
    fake_wx.Menu = Menu
    monkeypatch.setitem(sys.modules, "wx", fake_wx)
    monkeypatch.setitem(sys.modules, "wx.adv", fake_adv)
    fake_wx.adv = fake_adv
    clear_ui_modules()
    return fake_wx


class FakeController:
    def __init__(self):
        self.shutdown_calls = 0

    def shutdown(self):
        self.shutdown_calls += 1


class FakeFrame:
    def __init__(self, controller):
        self.controller = controller
        self.shown = 0
        self.hidden = 0
        self.raised = 0

    def Show(self, show=True):
        if show:
            self.shown += 1

    def Hide(self):
        self.hidden += 1

    def Raise(self):
        self.raised += 1


def test_tool_app_shell_creates_hidden_main_and_speech_panels(monkeypatch):
    install_fake_wx(monkeypatch)
    from apps.shared.tool_app_shell import ToolAppShell

    controller = FakeController()
    shell = ToolAppShell(
        controller=controller,
        main_frame_factory=lambda ctrl: FakeFrame(ctrl),
        speech_frame_factory=lambda ctrl: FakeFrame(ctrl),
    )

    shell.initialize()

    assert shell.panel_controller is not None
    assert shell.tray_icon is not None


def test_tool_app_shell_menu_triggers_show_main(monkeypatch):
    install_fake_wx(monkeypatch)
    from apps.shared.tool_app_shell import ToolAppShell

    controller = FakeController()
    main_frame = FakeFrame(controller)
    speech_frame = FakeFrame(controller)
    shell = ToolAppShell(
        controller=controller,
        main_frame_factory=lambda ctrl: main_frame,
        speech_frame_factory=lambda ctrl: speech_frame,
    )
    shell.initialize()
    shell.panel_controller.show("main")

    assert main_frame.shown == 1
    assert main_frame.raised == 1


def test_tool_app_shell_shutdown_destroys_tray_and_calls_controller(monkeypatch):
    install_fake_wx(monkeypatch)
    from apps.shared.tool_app_shell import ToolAppShell

    controller = FakeController()
    shell = ToolAppShell(
        controller=controller,
        main_frame_factory=lambda ctrl: FakeFrame(ctrl),
        speech_frame_factory=lambda ctrl: FakeFrame(ctrl),
    )
    shell.initialize()

    shell.shutdown()

    assert shell.tray_icon.destroyed is True
    assert controller.shutdown_calls == 1
