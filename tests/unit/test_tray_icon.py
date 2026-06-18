import importlib
import sys
import types

import pytest


UI_MODULES = (
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
    fake_wx.ART_INFORMATION = 1
    fake_wx.ART_OTHER = 2

    class ArtProvider:
        @staticmethod
        def GetIcon(art_id, client, size):
            return "fake_icon"

    fake_wx.ArtProvider = ArtProvider

    class Menu:
        def __init__(self):
            self.items = []
            self.bindings = {}

        def Append(self, id_, label):
            item = MenuItem(id_, label)
            self.items.append(item)
            return item

        def Bind(self, event, handler, id_=None):
            self.bindings[event] = (handler, id_)

        def GetMenuItems(self):
            return self.items

    class MenuItem:
        def __init__(self, id_, label):
            self.id = id_
            self.label = label

        def GetItemLabelText(self):
            return self.label

    fake_adv = types.ModuleType("wx.adv")
    fake_adv.EVT_TASKBAR_LEFT_DOWN = object()
    fake_adv.EVT_TASKBAR_RIGHT_DOWN = object()

    class TaskBarIcon:
        def __init__(self, iconType=None):
            self.iconType = iconType
            self.destroyed = False
            self.bindings = {}
            self.popup_menus = []

        def Destroy(self):
            self.destroyed = True

        def SetIcon(self, icon, tooltip=""):
            self.icon = icon
            self.tooltip = tooltip
            return True

        def Bind(self, event, handler):
            self.bindings[event] = handler

        def PopupMenu(self, menu):
            self.popup_menus.append(menu)
            return True

    fake_adv.TaskBarIcon = TaskBarIcon
    fake_wx.Menu = Menu
    fake_wx.MenuItem = MenuItem
    monkeypatch.setitem(sys.modules, "wx", fake_wx)
    monkeypatch.setitem(sys.modules, "wx.adv", fake_adv)
    fake_wx.adv = fake_adv
    clear_ui_modules()
    return fake_wx


def test_tray_icon_builds_main_menu_items(monkeypatch):
    install_fake_wx(monkeypatch)
    from apps.shared.tray_icon import ToolTrayIcon

    seen = []
    tray = ToolTrayIcon(
        on_open_main=lambda: seen.append("main"),
        on_open_speech=lambda: seen.append("speech"),
        on_exit=lambda: seen.append("exit"),
    )

    menu = tray.CreatePopupMenu()
    labels = [item.GetItemLabelText() for item in menu.GetMenuItems()]
    assert labels == ["Main Panel", "Speech Settings", "Exit"]


def test_tray_icon_left_and_right_down_open_popup_menu(monkeypatch):
    fake_wx = install_fake_wx(monkeypatch)
    from apps.shared.tray_icon import ToolTrayIcon

    tray = ToolTrayIcon(
        on_open_main=lambda: None,
        on_open_speech=lambda: None,
        on_exit=lambda: None,
    )

    tray.bindings[fake_wx.adv.EVT_TASKBAR_LEFT_DOWN](None)
    tray.bindings[fake_wx.adv.EVT_TASKBAR_RIGHT_DOWN](None)

    assert len(tray.popup_menus) == 2
    assert [item.GetItemLabelText() for item in tray.popup_menus[0].GetMenuItems()] == [
        "Main Panel",
        "Speech Settings",
        "Exit",
    ]
