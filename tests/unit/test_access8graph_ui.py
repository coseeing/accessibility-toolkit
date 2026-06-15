import importlib
import sys
import types

import pytest


def install_fake_wx(monkeypatch):
    fake_wx = types.ModuleType("wx")
    fake_wx.VERTICAL = 1
    fake_wx.EXPAND = 2
    fake_wx.ALL = 4
    fake_wx.EVT_BUTTON = object()
    fake_wx.EVT_CLOSE = object()
    fake_wx.OK = 16
    fake_wx.ICON_ERROR = 32
    fake_wx.FD_OPEN = 64
    fake_wx.FD_FILE_MUST_EXIST = 128
    fake_wx.ID_OK = 5100
    fake_wx.message_box_calls = []

    def MessageBox(message, caption, style):
        fake_wx.message_box_calls.append((message, caption, style))

    fake_wx.MessageBox = MessageBox

    class Frame:
        def __init__(self, parent=None, title=""):
            self.parent = parent
            self.title = title
            self.hidden = False
            self.destroyed = False
            self.bindings = {}

        def Bind(self, event, handler):
            self.bindings[event] = handler

        def Hide(self):
            self.hidden = True

        def Destroy(self):
            self.destroyed = True

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

    class StaticText:
        def __init__(self, parent, label=""):
            self.parent = parent
            self._label = label

        def GetLabel(self):
            return self._label

        def SetLabel(self, label):
            self._label = label

    class Button:
        def __init__(self, parent, label):
            self.parent = parent
            self._label = label
            self.enabled = True
            self.bindings = {}

        def GetLabel(self):
            return self._label

        def SetLabel(self, label):
            self._label = label

        def Enable(self, enabled=True):
            self.enabled = enabled

        def IsEnabled(self):
            return self.enabled

        def Bind(self, event, handler):
            self.bindings[event] = handler

    class FileDialog:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def ShowModal(self):
            return fake_wx.ID_OK

        def GetPath(self):
            return "/tmp/map.graphml"

    fake_wx.Frame = Frame
    fake_wx.Panel = Panel
    fake_wx.BoxSizer = BoxSizer
    fake_wx.StaticText = StaticText
    fake_wx.Button = Button
    fake_wx.FileDialog = FileDialog

    monkeypatch.setitem(sys.modules, "wx", fake_wx)
    sys.modules.pop("ui.access8graph.main_frame", None)
    return fake_wx


class FakeController:
    def __init__(self) -> None:
        self.listener = None
        self.selected_path = None
        self.running = False
        self.start_calls = 0
        self.stop_calls = 0
        self.start_error: str | None = None

    def set_status_listener(self, listener) -> None:
        self.listener = listener

    def choose_graphml(self, path: str) -> None:
        self.selected_path = path

    def get_selected_graphml_path(self) -> str | None:
        return self.selected_path

    def start_navigation(self) -> None:
        self.start_calls += 1
        if self.start_error:
            if self.listener:
                self.listener({"kind": "error", "message": self.start_error})
            raise RuntimeError("Failed to start navigation")
        self.running = True

    def stop_navigation(self) -> None:
        self.stop_calls += 1
        self.running = False

    def is_navigation_running(self) -> bool:
        return self.running


@pytest.fixture
def main_frame_type(monkeypatch):
    install_fake_wx(monkeypatch)
    module = importlib.import_module("ui.access8graph.main_frame")
    return module.Access8GraphMainFrame


def test_main_frame_initial_state_disables_start(main_frame_type) -> None:
    controller = FakeController()
    frame = main_frame_type(controller=controller)

    assert frame.status_label.GetLabel() == "No file selected"
    assert frame.navigation_button.IsEnabled() is False
    assert frame.navigation_button.GetLabel() == "Start Navigation"

    frame.Destroy()


def test_main_frame_syncs_selected_file_status(main_frame_type, tmp_path) -> None:
    controller = FakeController()
    frame = main_frame_type(controller=controller)
    path = tmp_path / "map.graphml"
    path.write_text("<graphml />", encoding="utf-8")
    controller.choose_graphml(str(path))

    frame._sync_controls()

    assert frame.status_label.GetLabel() == "map.graphml"
    assert frame.navigation_button.IsEnabled() is True

    frame.Destroy()


def test_main_frame_start_stop_button_calls_controller(main_frame_type, tmp_path) -> None:
    controller = FakeController()
    path = tmp_path / "map.graphml"
    path.write_text("<graphml />", encoding="utf-8")
    controller.choose_graphml(str(path))
    frame = main_frame_type(controller=controller)
    frame._sync_controls()

    frame._on_toggle_navigation(None)
    assert controller.start_calls == 1

    frame._on_toggle_navigation(None)
    assert controller.stop_calls == 1

    frame.Destroy()


def test_main_frame_preserves_error_label_from_controller_status(
    main_frame_type,
) -> None:
    controller = FakeController()
    frame = main_frame_type(controller=controller)

    assert controller.listener is not None
    controller.listener({"kind": "error", "message": "Something went wrong"})

    assert frame.status_label.GetLabel() == "Something went wrong"

    frame.Destroy()


def test_main_frame_preserves_error_after_failed_start(
    main_frame_type, tmp_path
) -> None:
    controller = FakeController()
    controller.start_error = "parse failed"
    path = tmp_path / "bad.graphml"
    path.write_text("<graphml />", encoding="utf-8")
    controller.choose_graphml(str(path))
    frame = main_frame_type(controller=controller)
    frame._sync_controls()

    frame._on_toggle_navigation(None)

    assert frame.status_label.GetLabel() == "parse failed"

    frame.Destroy()
