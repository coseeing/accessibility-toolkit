import importlib
import sys
import types

import pytest

import accessibility_toolkit.runtime.platform
import accessibility_toolkit.runtime.environment
from accessibility_toolkit.events import ErrorRaised, SpeechEngineChanged
from accessibility_toolkit.output.speech import SpeechEngineOption, SpeechNumericSetting
from apps.key_echo.events import EchoStateChanged
from apps.nvda_remote.events import RemoteConnectionChanged
from apps.nvda_remote.connections import ConnectionManager, JsonConnectionStore
from accessibility_toolkit.input import HID


UI_MODULES = (
    "ui.app",
    "ui.main",
    "ui.main_frame",
    "ui.nvda_remote.app",
    "ui.nvda_remote.main_frame",
    "ui.nvda_remote.connection_editor",
    "ui.nvda_remote.group_manager_dialog",
    "ui.nvda_remote.connection_manager_dialog",
    "ui.echo.app",
    "ui.echo.main_frame",
    "accessibility_toolkit_wx.speech.speech_controls",
    "accessibility_toolkit_wx.speech.speech_settings_frame",
    "apps.nvda_remote.main",
    "apps.key_echo.main",
    "accessibility_toolkit_wx.shell.tool_app_shell",
    "accessibility_toolkit_wx.tray.tray_icon",
    "accessibility_toolkit_wx.shell.panel_controller",
)


class FakeBootstrapSpeechOutput:
    def speak(self, sequence):
        del sequence

    def cancel(self):
        pass

    def pause(self, is_paused):
        del is_paused

    def list_voices(self):
        return ()

    def get_voice(self):
        return None

    def set_voice(self, voice_id):
        del voice_id

    def get_rate(self):
        return None

    def set_rate(self, value):
        del value

    def get_pitch(self):
        return None

    def set_pitch(self, value):
        del value

    def get_volume(self):
        return None

    def set_volume(self, value):
        del value

    def get_supported_numeric_settings(self):
        return ()


def fake_bootstrap_speech_engine_options(scheduler):
    del scheduler
    return (
        SpeechEngineOption(
            engine_id="Pyttsx3",
            label="Pyttsx3",
            factory=FakeBootstrapSpeechOutput,
        ),
    )


def clear_ui_modules():
    for module_name in UI_MODULES:
        sys.modules.pop(module_name, None)


@pytest.fixture(autouse=True)
def clean_app_wx_module_cache():
    clear_ui_modules()
    yield
    clear_ui_modules()


def install_fake_wx(monkeypatch):
    fake_wx = types.ModuleType("wx")
    fake_wx.ID_ANY = -1
    fake_wx.ID_EXIT = 5000
    fake_wx.ID_OK = 5100
    fake_wx.ID_CANCEL = 5101
    fake_wx.ID_CLOSE = 5102
    fake_wx.VERTICAL = 1
    fake_wx.HORIZONTAL = 2
    fake_wx.EXPAND = 2
    fake_wx.ALL = 4
    fake_wx.ALIGN_CENTER_VERTICAL = 8
    fake_wx.EVT_BUTTON = object()
    fake_wx.EVT_CHOICE = object()
    fake_wx.EVT_TEXT = object()
    fake_wx.EVT_SLIDER = object()
    fake_wx.EVT_CLOSE = object()
    fake_wx.EVT_MENU = object()
    fake_wx.EVT_CHECKBOX = object()
    fake_wx.EVT_LISTBOX = object()
    fake_wx.EVT_LIST_ITEM_ACTIVATED = object()
    fake_wx.EVT_LIST_ITEM_SELECTED = object()
    fake_wx.EVT_LIST_ITEM_DESELECTED = object()
    fake_wx.EVT_CONTEXT_MENU = object()
    fake_wx.EVT_CHAR_HOOK = object()
    fake_wx.LC_REPORT = 2048
    fake_wx.LIST_AUTOSIZE = 4096
    fake_wx.LIST_AUTOSIZE_USEHEADER = 8192
    fake_wx.WXK_RETURN = 13
    fake_wx.WXK_NUMPAD_ENTER = 271
    fake_wx.WXK_UP = 315
    fake_wx.WXK_DOWN = 317
    fake_wx.WXK_F2 = 113
    fake_wx.WXK_DELETE = 127
    fake_wx.OK = 16
    fake_wx.ICON_ERROR = 32
    fake_wx.YES = 64
    fake_wx.NO = 128
    fake_wx.YES_NO = fake_wx.YES | fake_wx.NO
    fake_wx.ICON_WARNING = 256
    fake_wx.TE_PASSWORD = 512
    fake_wx.LB_EXTENDED = 1024
    fake_wx.ART_INFORMATION = 1
    fake_wx.ART_OTHER = 2

    class ArtProvider:
        @staticmethod
        def GetIcon(art_id, client, size):
            return "fake_icon"

    fake_wx.ArtProvider = ArtProvider

    fake_wx.message_box_calls = []
    fake_wx.call_after_calls = []

    class Frame:
        def __init__(self, parent=None, title=""):
            self.parent = parent
            self._title = title
            self.shown = False
            self.bindings = {}
            self.raised = False

        def GetTitle(self):
            return self._title

        def Show(self, show=True):
            self.shown = show

        def Hide(self):
            self.shown = False

        def Raise(self):
            self.raised = True

        def Bind(self, event, handler):
            self.bindings[event] = handler

        def SetFocus(self):
            self.has_focus = True

        def SetName(self, name):
            self.name = name

    class Panel:
        def __init__(self, parent):
            self.parent = parent
            self.sizer = None

        def SetSizer(self, sizer):
            self.sizer = sizer

    class StaticText:
        def __init__(self, parent, label=""):
            self.parent = parent
            self._label = label

        def GetLabel(self):
            return self._label

        def SetLabel(self, label):
            self._label = label

    class BoxSizer:
        def __init__(self, orient):
            self.orient = orient
            self.children = []

        def Add(self, widget, proportion, flags, border):
            self.children.append((widget, proportion, flags, border))

    class TextCtrl:
        def __init__(self, parent, value="", style=0):
            self.parent = parent
            self._value = value
            self.style = style
            self.enabled = True
            self.bindings = {}
            self.name = ""
            self.has_focus = False

        def GetValue(self):
            return self._value

        def SetValue(self, value):
            self._value = value

        def Enable(self, enabled=True):
            self.enabled = enabled

        def Disable(self):
            self.enabled = False

        def Bind(self, event, handler):
            self.bindings[event] = handler

        def SetFocus(self):
            self.has_focus = True

        def SetName(self, name):
            self.name = name

    class Dialog(Frame):
        def __init__(self, parent=None, title="", size=None):
            super().__init__(parent=parent, title=title)
            self.size = size
            self.modal_result = fake_wx.ID_CANCEL
            self.closed = False

        def ShowModal(self):
            return self.modal_result

        def EndModal(self, result):
            self.modal_result = result
            self.closed = True

        def Close(self):
            self.closed = True

        def Destroy(self):
            self.closed = True

        def SetEscapeId(self, id_):
            self.escape_id = id_

    class Slider:
        def __init__(self, parent, value=0, minValue=0, maxValue=100):
            self.parent = parent
            self._value = value
            self.minValue = minValue
            self.maxValue = maxValue
            self.enabled = True
            self.bindings = {}
            self.line_size = 1
            self.page_size = 10

        def GetValue(self):
            return self._value

        def SetValue(self, value):
            self._value = value

        def Enable(self, enabled=True):
            self.enabled = enabled

        def Disable(self):
            self.enabled = False

        def Bind(self, event, handler):
            self.bindings[event] = handler

        def SetLineSize(self, size):
            self.line_size = size

        def SetPageSize(self, size):
            self.page_size = size

    class Button:
        def __init__(self, parent, id=fake_wx.ID_ANY, label=""):
            if isinstance(id, str) and not label:
                label = id
                id = fake_wx.ID_ANY
            self.parent = parent
            self.id = id
            self._label = label
            self.bindings = {}
            self.enabled = True
            self.is_default = False

        def GetLabel(self):
            return self._label

        def SetLabel(self, label):
            self._label = label

        def Enable(self, enabled=True):
            self.enabled = enabled

        def Disable(self):
            self.enabled = False

        def Bind(self, event, handler):
            self.bindings[event] = handler

        def SetFocus(self):
            self.has_focus = True

        def SetName(self, name):
            self.name = name

        def SetDefault(self):
            self.is_default = True

    class SpinCtrl(TextCtrl):
        def __init__(self, parent, value="6837", min=1, max=65535):
            super().__init__(parent, value=value)
            self.minimum = min
            self.maximum = max

        def GetValue(self):
            return int(super().GetValue())

    class CheckBox(Button):
        def __init__(self, parent, label=""):
            super().__init__(parent, label)
            self.value = False

        def SetValue(self, value):
            self.value = bool(value)

        def GetValue(self):
            return self.value

    class Choice:
        def __init__(self, parent, choices):
            self.parent = parent
            self.choices = list(choices)
            self.bindings = {}
            self.enabled = True
            self.selection = 0 if self.choices else -1

        def GetString(self, index):
            return self.choices[index]

        def GetCount(self):
            return len(self.choices)

        def GetSelection(self):
            return self.selection

        def SetSelection(self, index):
            self.selection = index

        def GetStringSelection(self):
            return self.choices[self.selection] if self.selection >= 0 else ""

        def SetStringSelection(self, value):
            self.selection = self.choices.index(value)

        def Set(self, choices):
            self.choices = list(choices)
            self.selection = 0 if self.choices else -1

        def Clear(self):
            self.choices = []
            self.selection = -1

        def Append(self, label):
            self.choices.append(label)
            if self.selection < 0:
                self.selection = 0

        def Enable(self, enabled=True):
            self.enabled = enabled

        def Disable(self):
            self.enabled = False

        def Bind(self, event, handler):
            self.bindings[event] = handler

        def SetName(self, name):
            self.name = name

    class ListBox:
        def __init__(self, parent, choices=(), style=0):
            self.parent = parent
            self.choices = list(choices)
            self.style = style
            self.selections = []
            self.selection = -1
            self.bindings = {}
            self.enabled = True
            self.name = ""
            self.has_focus = False

        def Set(self, choices):
            self.choices = list(choices)
            self.selections = []
            self.selection = -1

        def GetSelections(self):
            return tuple(self.selections)

        def GetString(self, index):
            return self.choices[index]

        def SetSelection(self, index, select=True):
            self.selection = index
            if select:
                if self.style & fake_wx.LB_EXTENDED:
                    if index not in self.selections:
                        self.selections.append(index)
                else:
                    self.selections = [index]
            elif index in self.selections:
                self.selections.remove(index)

        def FindString(self, value):
            try:
                return self.choices.index(value)
            except ValueError:
                return -1

        def Bind(self, event, handler):
            self.bindings[event] = handler

        def Enable(self, enabled=True):
            self.enabled = enabled

        def Disable(self):
            self.enabled = False

        def SetFocus(self):
            self.has_focus = True

        def SetName(self, name):
            self.name = name

    class ListCtrl:
        def __init__(self, parent, style=0):
            self.parent = parent
            self.style = style
            self.rows = []
            self.columns = []
            self.selected = []
            self.focused = -1
            self.bindings = {}
            self.name = ""
            self.has_focus = False

        def InsertColumn(self, index, label):
            self.columns.insert(index, label)

        def InsertItem(self, index, text):
            self.rows.insert(index, [text])
            return index

        def SetItem(self, row, column, text):
            while len(self.rows[row]) <= column:
                self.rows[row].append("")
            self.rows[row][column] = text

        def DeleteAllItems(self):
            self.rows.clear()
            self.selected.clear()
            self.focused = -1

        def GetItemCount(self):
            return len(self.rows)

        def GetFirstSelected(self):
            return min(self.selected) if self.selected else -1

        def GetNextSelected(self, index):
            return next((item for item in sorted(self.selected) if item > index), -1)

        def Select(self, index, select=True):
            if select and index not in self.selected:
                self.selected.append(index)
            elif not select and index in self.selected:
                self.selected.remove(index)

        def Focus(self, index):
            self.focused = index

        def Bind(self, event, handler):
            self.bindings[event] = handler

        def SetFocus(self):
            self.has_focus = True

        def SetName(self, name):
            self.name = name

    class Menu:
        def __init__(self):
            self.items = []
            self.bindings = {}
            self.destroyed = False

        def Append(self, id_, label):
            if id_ == fake_wx.ID_ANY:
                id_ = fake_wx.NewIdRef()
            item = type("MenuItem", (), {})()
            item.id = id_
            item.label = label
            item.enabled = True
            item.GetId = lambda: item.id
            item.GetItemLabelText = lambda: item.label
            item.Enable = lambda enabled=True: setattr(item, "enabled", enabled)
            self.items.append(item)
            return item

        def AppendSeparator(self):
            self.items.append(None)

        def Bind(self, event, handler, id=None):
            self.bindings[id] = handler

        def Enable(self, id_, enabled):
            for item in self.items:
                if item is not None and item.id == id_:
                    item.Enable(enabled)

        def Destroy(self):
            self.destroyed = True

        def GetMenuItems(self):
            return self.items

    class App:
        def __init__(self, redirect=False):
            self.redirect = redirect
            self.top_window = None

        def SetTopWindow(self, frame):
            self.top_window = frame

        def MainLoop(self):
            return 0

        def ExitMainLoop(self):
            pass

    fake_wx.App = App

    class _FakeExitApp:
        def ExitMainLoop(self):
            pass

    _app_instance = _FakeExitApp()

    def GetApp():
        return _app_instance

    fake_wx.GetApp = GetApp

    fake_wx.message_box_result = 0

    def MessageBox(message, caption, style):
        fake_wx.message_box_calls.append((message, caption, style))
        return fake_wx.message_box_result

    def GetTextFromUser(message, caption, default_value="", parent=None):
        del message, caption, parent
        return default_value

    def CallAfter(callback, *args, **kwargs):
        fake_wx.call_after_calls.append((callback, args, kwargs))
        return callback(*args, **kwargs)

    fake_wx.Frame = Frame
    fake_wx.Dialog = Dialog
    fake_wx.Panel = Panel
    fake_wx.StaticText = StaticText
    fake_wx.BoxSizer = BoxSizer
    fake_wx.TextCtrl = TextCtrl
    fake_wx.SpinCtrl = SpinCtrl
    fake_wx.CheckBox = CheckBox
    fake_wx.Slider = Slider
    fake_wx.Button = Button
    fake_wx.Choice = Choice
    fake_wx.ListBox = ListBox
    fake_wx.Menu = Menu
    fake_wx.ListCtrl = ListCtrl
    fake_wx.App = App
    fake_wx.MessageBox = MessageBox
    fake_wx.GetTextFromUser = GetTextFromUser
    fake_wx.CallAfter = CallAfter

    next_menu_id = 6000

    def NewIdRef():
        nonlocal next_menu_id
        next_menu_id += 1
        return next_menu_id

    fake_wx.NewIdRef = NewIdRef

    fake_adv = types.ModuleType("wx.adv")
    fake_adv.EVT_TASKBAR_LEFT_DOWN = object()
    fake_adv.EVT_TASKBAR_RIGHT_DOWN = object()

    class TaskBarIcon:
        def __init__(self, iconType=None):
            self.iconType = iconType
            self.destroyed = False
            self.bindings = {}

        def Destroy(self):
            self.destroyed = True

        def SetIcon(self, icon, tooltip=""):
            return True

        def Bind(self, event, handler):
            self.bindings[event] = handler

        def PopupMenu(self, menu):
            return True

    fake_adv.TaskBarIcon = TaskBarIcon
    monkeypatch.setitem(sys.modules, "wx.adv", fake_adv)
    fake_wx.adv = fake_adv

    monkeypatch.setitem(sys.modules, "wx", fake_wx)
    clear_ui_modules()
    return fake_wx


class FakeController:
    def __init__(self, connection_manager=None):
        self.connected_to = None
        self.connect_calls = []
        self.connect_quick_calls = 0
        self.disconnect_calls = 0
        self.started_control = 0
        self.stopped_control = 0
        self.pushed_clipboard = 0
        self.state = types.SimpleNamespace(
            connection_state="idle",
            control_state="idle",
        )
        self.status_listener = None
        self.speech_engine_id = "NvdaController"
        self.speech_engine_calls = []
        self.engine_switch_error = None
        self.available_voices = ()
        self.selected_voice = None
        self.rate = None
        self.pitch = None
        self.volume = None
        self.voice_calls = []
        self.rate_calls = []
        self.pitch_calls = []
        self.volume_calls = []
        self.clipboard_available = True
        self.connection_manager = connection_manager

    def connect(self, host, port, key, insecure=False):
        self.connect_calls.append((host, port, key, insecure))
        self.connected_to = (host, port, key, insecure)
        self.state.connection_state = "connected"
        self.state.control_state = "connected"
        if self.status_listener is not None:
            self.status_listener(RemoteConnectionChanged("connected"))

    def connect_quick(self):
        self.connect_quick_calls += 1

    def disconnect(self):
        if self.state.control_state == "controlling":
            self.stop_control()
        self.disconnect_calls += 1
        self.state.connection_state = "idle"
        self.state.control_state = "idle"
        if self.status_listener is not None:
            self.status_listener(RemoteConnectionChanged("idle"))

    def start_control(self):
        self.started_control += 1
        self.state.control_state = "controlling"
        if self.status_listener is not None:
            self.status_listener(RemoteConnectionChanged("connected"))

    def stop_control(self):
        self.stopped_control += 1
        self.state.control_state = "connected" if self.state.connection_state != "idle" else "idle"
        if self.status_listener is not None:
            self.status_listener(RemoteConnectionChanged(self.state.connection_state))

    def push_clipboard(self):
        self.pushed_clipboard += 1

    def is_clipboard_available(self):
        return self.clipboard_available

    def set_status_listener(self, listener):
        self.status_listener = listener

    def get_speech_engine_options(self):
        return (
            ("NvdaController", "Nvda Controller"),
            ("Pyttsx3", "Pyttsx3"),
        )

    def get_selected_speech_engine(self):
        return self.speech_engine_id

    def set_speech_engine(self, engine_id):
        self.speech_engine_calls.append(engine_id)
        if self.engine_switch_error is not None:
            raise self.engine_switch_error
        self.speech_engine_id = engine_id
        if self.status_listener is not None:
            self.status_listener(SpeechEngineChanged(engine_id))

    def get_available_voices(self):
        return self.available_voices

    def get_selected_voice(self):
        return self.selected_voice

    def set_selected_voice(self, voice_id):
        self.voice_calls.append(voice_id)
        self.selected_voice = voice_id

    def get_rate(self):
        return self.rate

    def set_rate(self, value):
        self.rate_calls.append(value)
        self.rate = value

    def get_pitch(self):
        return self.pitch

    def set_pitch(self, value):
        self.pitch_calls.append(value)
        self.pitch = value

    def get_volume(self):
        return self.volume

    def set_volume(self, value):
        self.volume_calls.append(value)
        self.volume = value


class FakeEchoController:
    def __init__(self):
        self.status_listener = None
        self.running = False
        self.started = 0
        self.stopped = 0
        self.speech_engine_id = "Pyttsx3"
        self.speech_engine_calls = []
        self.engine_switch_error = None
        self.available_voices = ()
        self.selected_voice = None
        self.rate = None
        self.pitch = None
        self.volume = None
        self.voice_calls = []
        self.rate_calls = []
        self.pitch_calls = []
        self.volume_calls = []

    def set_status_listener(self, listener):
        self.status_listener = listener

    def start_echo(self):
        self.started += 1
        self.running = True
        if self.status_listener is not None:
            self.status_listener(EchoStateChanged(running=True))

    def stop_echo(self):
        self.stopped += 1
        self.running = False
        if self.status_listener is not None:
            self.status_listener(EchoStateChanged(running=False))

    def is_echo_running(self):
        return self.running

    def get_speech_engine_options(self):
        return (
            ("NvdaController", "Nvda Controller"),
            ("Pyttsx3", "Pyttsx3"),
        )

    def get_selected_speech_engine(self):
        return self.speech_engine_id

    def set_speech_engine(self, engine_id):
        self.speech_engine_calls.append(engine_id)
        if self.engine_switch_error is not None:
            raise self.engine_switch_error
        self.speech_engine_id = engine_id
        if self.status_listener is not None:
            self.status_listener(SpeechEngineChanged(engine_id))

    def get_available_voices(self):
        return self.available_voices

    def get_selected_voice(self):
        return self.selected_voice

    def set_selected_voice(self, voice_id):
        self.voice_calls.append(voice_id)
        self.selected_voice = voice_id

    def get_rate(self):
        return self.rate

    def set_rate(self, value):
        self.rate_calls.append(value)
        self.rate = value

    def get_pitch(self):
        return self.pitch

    def set_pitch(self, value):
        self.pitch_calls.append(value)
        self.pitch = value

    def get_volume(self):
        return self.volume

    def set_volume(self, value):
        self.volume_calls.append(value)
        self.volume = value


def build_manager(tmp_path):
    return ConnectionManager(JsonConnectionStore(tmp_path / "connections.json"))


def test_main_frame_exposes_saved_connection_actions_not_manual_fields(monkeypatch, tmp_path):
    install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("ui.nvda_remote.main_frame").MainFrame

    controller = FakeController(connection_manager=build_manager(tmp_path))
    frame = MainFrame(controller=controller)

    assert frame.GetTitle() == "NVDA Remote Client"
    assert not hasattr(frame, "host_ctrl")
    assert not hasattr(frame, "port_ctrl")
    assert not hasattr(frame, "key_ctrl")
    assert frame.manage_connections_button.GetLabel() == "Manage Connections..."
    assert frame.quick_connect_button.GetLabel() == "Quick Connect"
    assert frame.disconnect_button.GetLabel() == "Disconnect"
    assert frame.quick_connect_button.enabled is False
    assert frame.disconnect_button.enabled is False
    assert frame.control_button.GetLabel() == "Start Control"
    assert frame.control_button.enabled is False
    assert frame.clipboard_button.GetLabel() == "Push Clipboard"
    assert frame.clipboard_button.enabled is False


def test_main_frame_enables_quick_only_for_valid_default_while_idle(monkeypatch, tmp_path):
    install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("ui.nvda_remote.main_frame").MainFrame
    manager = build_manager(tmp_path)
    saved = manager.add_connection(
        "Default", name="Office", host="relay.example", port=6837, key="secret"
    )
    manager.set_quick_connect(saved.id)
    controller = FakeController(connection_manager=manager)
    frame = MainFrame(controller=controller)

    assert frame.quick_connect_button.enabled is True
    frame._on_quick_connect(None)
    assert controller.connect_quick_calls == 1


def test_main_frame_action_states_for_connecting_connected_and_idle(monkeypatch, tmp_path):
    install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("ui.nvda_remote.main_frame").MainFrame
    controller = FakeController(connection_manager=build_manager(tmp_path))
    frame = MainFrame(controller=controller)

    controller.state.connection_state = "connecting"
    frame._sync_connection_actions()
    assert frame.manage_connections_button.enabled is False
    assert frame.quick_connect_button.enabled is False
    assert frame.disconnect_button.enabled is True
    controller.state.connection_state = "connected"
    frame._sync_connection_actions()
    assert frame.manage_connections_button.enabled is True
    assert frame.quick_connect_button.enabled is False
    assert frame.disconnect_button.enabled is True


def test_main_frame_control_button_toggles_start_and_stop(monkeypatch):
    install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("ui.nvda_remote.main_frame").MainFrame
    controller = FakeController()
    frame = MainFrame(controller=controller)

    controller.state.connection_state = "connected"
    frame._sync_all_controls()
    frame._on_start_control(None)
    frame._on_start_control(None)

    assert controller.started_control == 1
    assert controller.stopped_control == 1
    assert frame.control_button.GetLabel() == "Start Control"
    assert frame.control_button.enabled is True


def test_main_frame_disables_clipboard_button_when_clipboard_unavailable(monkeypatch):
    install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("ui.nvda_remote.main_frame").MainFrame
    controller = FakeController()
    controller.clipboard_available = False
    frame = MainFrame(controller=controller)

    controller.state.connection_state = "connected"
    frame._sync_all_controls()
    assert frame.control_button.enabled is True
    assert frame.clipboard_button.enabled is False


def test_main_frame_shows_input_error_from_controller_status(monkeypatch):
    fake_wx = install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("ui.nvda_remote.main_frame").MainFrame
    controller = FakeController()
    frame = MainFrame(controller=controller)

    controller.status_listener(ErrorRaised("permissions missing"))

    assert fake_wx.message_box_calls == [
        ("permissions missing", "Input Error", fake_wx.OK | fake_wx.ICON_ERROR)
    ]


def test_nvda_remote_app_creates_and_shows_main_frame(monkeypatch):
    install_fake_wx(monkeypatch)
    NvdaRemoteApp = importlib.import_module("ui.nvda_remote.app").NvdaRemoteApp
    controller = FakeController()
    app = NvdaRemoteApp(controller=controller)

    assert app.OnInit() is True
    assert "main" in app.shell.panel_controller._panels


def test_echo_main_frame_exposes_start_stop_controls(monkeypatch):
    install_fake_wx(monkeypatch)
    EchoMainFrame = importlib.import_module("ui.echo.main_frame").EchoMainFrame
    controller = FakeEchoController()
    frame = EchoMainFrame(controller=controller)

    assert frame.GetTitle() == "Key Echo Demo"
    assert frame.control_button.GetLabel() == "Start"
    assert frame.status_label.GetLabel() == "Stopped"


def test_echo_main_frame_toggles_start_and_stop(monkeypatch):
    install_fake_wx(monkeypatch)
    EchoMainFrame = importlib.import_module("ui.echo.main_frame").EchoMainFrame
    controller = FakeEchoController()
    frame = EchoMainFrame(controller=controller)

    frame._on_toggle_echo(None)
    frame._on_toggle_echo(None)

    assert controller.started == 1
    assert controller.stopped == 1
    assert frame.control_button.GetLabel() == "Start"
    assert frame.status_label.GetLabel() == "Stopped"


def test_echo_app_creates_and_shows_main_frame(monkeypatch):
    install_fake_wx(monkeypatch)
    EchoApp = importlib.import_module("ui.echo.app").EchoApp
    controller = FakeEchoController()
    app = EchoApp(controller=controller)

    assert app.OnInit() is True
    assert "main" in app.shell.panel_controller._panels


def test_nvda_remote_main_build_runtime_composes_app_service_and_gui(monkeypatch):
    install_fake_wx(monkeypatch)
    nvda_remote_main = importlib.import_module("apps.nvda_remote.main")

    class FakeConfigStore:
        def __init__(self, path):
            self.path = path
            self.saved = []

        def load_engine_id(self, *, default_engine_id):
            self.default_engine_id = default_engine_id
            return "Pyttsx3"

        def save_engine_id(self, engine_id):
            self.saved.append(engine_id)

        def load_voice(self, engine_id):
            return None

        def save_voice(self, engine_id, voice_id):
            self.saved.append((engine_id, voice_id))

        def load_numeric_setting(self, engine_id, setting_id):
            return None

        def save_numeric_setting(self, engine_id, setting_id, value):
            self.saved.append((engine_id, setting_id, value))

    class FakeSpeechService:
        def __init__(self, *, engine_options, selected_engine_id, scheduler=None):
            self.engine_options = engine_options
            self.selected_engine_id = selected_engine_id
            self.scheduler = scheduler
            self.voice = None
            self.rate = None
            self.pitch = None
            self.volume = None

        def get_selected_engine(self):
            return self.selected_engine_id

        def list_voices(self):
            return ()

        def set_voice(self, voice_id):
            self.voice = voice_id

        def get_supported_numeric_settings(self):
            return ()

        def set_rate(self, value):
            self.rate = value

        def set_pitch(self, value):
            self.pitch = value

        def set_volume(self, value):
            self.volume = value

    class FakeScheduler:
        pass

    class FakeQueuedService:
        def __init__(self, *, speech):
            self.speech = speech

        def get_selected_engine(self):
            return self.speech.get_selected_engine()

    class FakeTransport:
        def __init__(self, serializer):
            self.serializer = serializer

    class FakeKeyboardCapture:
        pass

    class FakeHotkeyCapture:
        pass

    class FakeClipboard:
        pass

    class FakeToneOutput:
        def __init__(self) -> None:
            self.calls = []

        def beep(self, hz, length, left=50, right=50):
            self.calls.append((hz, length, left, right))

    class FakeKeyboardInputService:
        def __init__(self, capture, handler):
            self.capture = capture
            self.handler = handler
            self.bind_calls = 0

        def bind(self):
            self.bind_calls += 1

    class FakeAppService:
        enter_usage = HID.F11

        def __init__(
            self,
            *,
            connection_manager,
            transport,
            input_capture,
            hotkey_capture,
            clipboard,
            capabilities,
            main_thread_dispatch,
            use_windows_native_key_payload,
        ):
            self.connection_manager = connection_manager
            self.transport = transport
            self.input_capture = input_capture
            self.hotkey_capture = hotkey_capture
            self.clipboard = clipboard
            self.capabilities = capabilities
            self.main_thread_dispatch = main_thread_dispatch
            self.use_windows_native_key_payload = use_windows_native_key_payload
            self.bind_calls = 0

        def notify_speech_engine_changed(self, engine_id):
            pass

        def bind(self):
            self.bind_calls += 1

    class FakeApp:
        dispatch = staticmethod(lambda callback: callback())

        def __init__(self, controller, **kwargs):
            self.controller = controller
            self.speech_controller = kwargs.get("speech_controller")

        def MainLoop(self):
            return 77

    monkeypatch.setitem(
        nvda_remote_main.build_runtime.__globals__,
        "JsonSpeechSettingsStore",
        FakeConfigStore,
    )
    monkeypatch.setattr(nvda_remote_main, "RelayTransport", FakeTransport)
    monkeypatch.setattr(accessibility_toolkit.runtime.platform.sys, "platform", "win32")
    input_capture = FakeKeyboardCapture()
    hotkey_capture = FakeHotkeyCapture()
    clipboard = FakeClipboard()
    tone_output = FakeToneOutput()
    scheduler = FakeScheduler()
    speech = FakeSpeechService(
        engine_options=("engine",),
        selected_engine_id="Pyttsx3",
        scheduler=scheduler,
    )
    speaker = FakeQueuedService(speech=speech)
    capabilities = types.SimpleNamespace(speech=speaker, tone=tone_output)

    def fake_build_app_runtime_parts(**kwargs):
        assert kwargs["hotkey_usage"] == FakeAppService.enter_usage
        assert kwargs["selected_engine_id"] == "Pyttsx3"
        assert kwargs["fallback_engine_id"] == "NvdaController"
        assert kwargs["include_clipboard"] is True
        assert callable(kwargs["on_engine_fallback"])
        return types.SimpleNamespace(
            input_capture=input_capture,
            hotkey_capture=hotkey_capture,
            clipboard=clipboard,
            tone_output=tone_output,
            output=types.SimpleNamespace(
                scheduler=scheduler,
                speech=speech,
                speaker=speaker,
                capabilities=capabilities,
            ),
        )

    monkeypatch.setattr(
        nvda_remote_main,
        "build_app_runtime_parts",
        fake_build_app_runtime_parts,
    )
    monkeypatch.setattr(nvda_remote_main, "KeyboardInputService", FakeKeyboardInputService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteAppService", FakeAppService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteApp", FakeApp)
    monkeypatch.setattr(
        nvda_remote_main,
        "default_config_path",
        lambda app_name="accessibility-toolkit": f"{app_name}.json",
    )

    runtime = nvda_remote_main.build_runtime()

    assert isinstance(runtime.transport, FakeTransport)
    assert runtime.transport.serializer.__class__.__name__ == "JSONSerializer"
    assert runtime.input_capture is input_capture
    assert runtime.hotkey_capture is hotkey_capture
    assert runtime.clipboard is clipboard
    assert runtime.scheduler is scheduler
    assert runtime.speech is speech
    assert runtime.speaker is speaker
    assert runtime.speech.selected_engine_id == "Pyttsx3"
    assert runtime.speaker.speech is runtime.speech
    assert runtime.app_service.capabilities.speech is runtime.speaker
    assert runtime.app_service.capabilities.tone is tone_output
    assert runtime.app_service.main_thread_dispatch is FakeApp.dispatch
    assert runtime.app_service.connection_manager is runtime.connection_manager
    assert runtime.config_store.path == "accessibility-toolkit.json"
    assert runtime.connection_manager._store.path.name == "nvda_remote_connections.json"
    assert runtime.app_service.bind_calls == 1
    assert runtime.input_service.capture is runtime.input_capture
    assert runtime.input_service.handler is runtime.app_service
    assert runtime.input_service.bind_calls == 1
    assert runtime.app.controller is runtime.app_service
    assert runtime.app.speech_controller is not None
    assert runtime.app.speech_controller.get_selected_speech_engine() == "Pyttsx3"


def test_nvda_remote_main_build_runtime_reloads_saved_settings_when_engine_changes(
    monkeypatch,
):
    install_fake_wx(monkeypatch)
    nvda_remote_main = importlib.import_module("apps.nvda_remote.main")

    class FakeConfigStore:
        def __init__(self, path):
            self.path = path
            self.saved_engine_ids = []

        def load_engine_id(self, *, default_engine_id):
            self.default_engine_id = default_engine_id
            return "Pyttsx3"

        def save_engine_id(self, engine_id):
            self.saved_engine_ids.append(engine_id)

        def load_voice(self, engine_id):
            return {
                "Pyttsx3": "voice-p",
                "NvdaController": "voice-n",
            }.get(engine_id)

        def save_voice(self, engine_id, voice_id):
            return None

        def load_numeric_setting(self, engine_id, setting_id):
            return {
                ("Pyttsx3", "rate"): 25,
                ("Pyttsx3", "volume"): 40,
                ("NvdaController", "rate"): 80,
                ("NvdaController", "pitch"): 65,
            }.get((engine_id, setting_id))

        def save_numeric_setting(self, engine_id, setting_id, value):
            return None

    class FakeSpeechService:
        def __init__(self):
            self.selected_engine_id = "Pyttsx3"
            self.voice_calls = []
            self.rate_calls = []
            self.pitch_calls = []
            self.volume_calls = []

        def get_selected_engine(self):
            return self.selected_engine_id

        def set_engine(self, engine_id):
            self.selected_engine_id = engine_id

        def get_engine_options(self):
            return (("Pyttsx3", "Pyttsx3"), ("NvdaController", "Nvda Controller"))

        def list_voices(self):
            return (
                ("voice-p", "Voice P"),
                ("voice-n", "Voice N"),
            )

        def get_voice(self):
            return None

        def set_voice(self, voice_id):
            self.voice_calls.append((self.selected_engine_id, voice_id))

        def get_supported_numeric_settings(self):
            return (
                SpeechNumericSetting(id="rate", label="Rate"),
                SpeechNumericSetting(id="pitch", label="Pitch"),
            )

        def get_rate(self):
            return None

        def set_rate(self, value):
            self.rate_calls.append((self.selected_engine_id, value))

        def get_pitch(self):
            return None

        def set_pitch(self, value):
            self.pitch_calls.append((self.selected_engine_id, value))

        def get_volume(self):
            return None

        def set_volume(self, value):
            self.volume_calls.append((self.selected_engine_id, value))

    class FakeKeyboardInputService:
        def __init__(self, capture, handler):
            self.capture = capture
            self.handler = handler

        def bind(self):
            return None

    class FakeAppService:
        enter_usage = HID.F11

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        def notify_speech_engine_changed(self, engine_id):
            pass

        def bind(self):
            return None

    class FakeTransport:
        def __init__(self, serializer):
            self.serializer = serializer

    class FakeApp:
        dispatch = staticmethod(lambda callback: callback())

        def __init__(self, controller, **kwargs):
            self.controller = controller
            self.speech_controller = kwargs.get("speech_controller")

        def MainLoop(self):
            return 0

    speech = FakeSpeechService()
    speaker = types.SimpleNamespace(speech=speech)

    def fake_build_app_runtime_parts(**kwargs):
        return types.SimpleNamespace(
            input_capture=object(),
            hotkey_capture=object(),
            clipboard=object(),
            tone_output=None,
            output=types.SimpleNamespace(
                scheduler=object(),
                speech=speech,
                speaker=speaker,
                capabilities=types.SimpleNamespace(speech=speaker, tone=None),
            ),
        )

    monkeypatch.setitem(
        nvda_remote_main.build_runtime.__globals__,
        "JsonSpeechSettingsStore",
        FakeConfigStore,
    )
    monkeypatch.setattr(nvda_remote_main, "RelayTransport", FakeTransport)
    monkeypatch.setattr(nvda_remote_main, "build_app_runtime_parts", fake_build_app_runtime_parts)
    monkeypatch.setattr(nvda_remote_main, "KeyboardInputService", FakeKeyboardInputService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteAppService", FakeAppService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteApp", FakeApp)
    monkeypatch.setattr(
        nvda_remote_main,
        "default_config_path",
        lambda app_name="accessibility-toolkit": f"{app_name}.json",
    )

    runtime = nvda_remote_main.build_runtime()

    assert speech.voice_calls == [("Pyttsx3", "voice-p")]
    assert speech.rate_calls == [("Pyttsx3", 25)]
    assert speech.pitch_calls == []
    assert speech.volume_calls == []

    runtime.app.speech_controller.set_speech_engine("NvdaController")

    assert runtime.config_store.saved_engine_ids == ["NvdaController"]
    assert speech.voice_calls == [
        ("Pyttsx3", "voice-p"),
        ("NvdaController", "voice-n"),
    ]
    assert speech.rate_calls == [
        ("Pyttsx3", 25),
        ("NvdaController", 80),
    ]
    assert speech.pitch_calls == [("NvdaController", 65)]
    assert speech.volume_calls == []


def test_nvda_remote_build_runtime_uses_mode_enter_hotkey_as_single_source_of_truth(
    monkeypatch,
):
    install_fake_wx(monkeypatch)
    nvda_remote_main = importlib.import_module("apps.nvda_remote.main")

    requested_hotkeys: list[int] = []

    class FakeConfigStore:
        def __init__(self, path):
            self.path = path

        def load_engine_id(self, *, default_engine_id):
            return "Pyttsx3"

        def save_engine_id(self, engine_id):
            return None

        def load_voice(self, engine_id):
            return None

        def save_voice(self, engine_id, voice_id):
            return None

        def load_numeric_setting(self, engine_id, setting_id):
            return None

        def save_numeric_setting(self, engine_id, setting_id, value):
            return None

    class FakeSpeechService:
        def __init__(self, *, engine_options, selected_engine_id, scheduler=None):
            self.engine_options = engine_options
            self.selected_engine_id = selected_engine_id

        def get_selected_engine(self):
            return self.selected_engine_id

        def list_voices(self):
            return ()

        def set_voice(self, voice_id):
            return None

        def get_supported_numeric_settings(self):
            return ()

        def set_rate(self, value):
            return None

        def set_pitch(self, value):
            return None

        def set_volume(self, value):
            return None

    class FakeScheduler:
        pass

    class FakeQueuedService:
        def __init__(self, *, speech):
            self.speech = speech

    class FakeTransport:
        def __init__(self, serializer):
            self.serializer = serializer

    class FakeKeyboardCapture:
        pass

    class FakeHotkeyCapture:
        pass

    class FakeClipboard:
        pass

    class FakeKeyboardInputService:
        def __init__(self, capture, handler):
            self.capture = capture
            self.handler = handler

        def bind(self):
            return None

    class FakeAppService:
        enter_usage = HID.F11

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        def bind(self):
            return None

    class FakeApp:
        dispatch = staticmethod(lambda callback: callback())

        def __init__(self, controller, **kwargs):
            self.controller = controller

        def MainLoop(self):
            return 0

    monkeypatch.setitem(
        nvda_remote_main.build_runtime.__globals__,
        "JsonSpeechSettingsStore",
        FakeConfigStore,
    )
    monkeypatch.setattr(nvda_remote_main, "RelayTransport", FakeTransport)
    scheduler = FakeScheduler()
    speech = FakeSpeechService(
        engine_options=("engine",),
        selected_engine_id="Pyttsx3",
        scheduler=scheduler,
    )
    speaker = FakeQueuedService(speech=speech)

    def fake_build_app_runtime_parts(**kwargs):
        requested_hotkeys.append(kwargs["hotkey_usage"])
        assert kwargs["include_clipboard"] is True
        return types.SimpleNamespace(
            input_capture=FakeKeyboardCapture(),
            hotkey_capture=FakeHotkeyCapture(),
            clipboard=FakeClipboard(),
            tone_output=None,
            output=types.SimpleNamespace(
                scheduler=scheduler,
                speech=speech,
                speaker=speaker,
                capabilities=types.SimpleNamespace(speech=speaker, tone=None),
            ),
        )

    monkeypatch.setattr(
        nvda_remote_main,
        "build_app_runtime_parts",
        fake_build_app_runtime_parts,
    )
    monkeypatch.setattr(nvda_remote_main, "KeyboardInputService", FakeKeyboardInputService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteAppService", FakeAppService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteApp", FakeApp)
    monkeypatch.setattr(
        nvda_remote_main,
        "default_config_path",
        lambda app_name="accessibility-toolkit": f"{app_name}.json",
    )

    nvda_remote_main.build_runtime()

    assert requested_hotkeys == [HID.F11]


def test_build_runtime_uses_macos_input_and_hotkey_on_darwin(monkeypatch):
    install_fake_wx(monkeypatch)
    nvda_remote_main = importlib.import_module("apps.nvda_remote.main")

    class FakeConfigStore:
        def __init__(self, path):
            self.path = path

        def load_engine_id(self, *, default_engine_id):
            self.default_engine_id = default_engine_id
            return "Pyttsx3"

        def save_engine_id(self, engine_id):
            self.saved_engine_id = engine_id

        def load_voice(self, engine_id):
            return None

        def save_voice(self, engine_id, voice_id):
            return None

        def load_numeric_setting(self, engine_id, setting_id):
            return None

        def save_numeric_setting(self, engine_id, setting_id, value):
            return None

    class FakeSpeechService:
        def __init__(self, *, engine_options, selected_engine_id, scheduler=None):
            self.engine_options = engine_options
            self.selected_engine_id = selected_engine_id

        def get_selected_engine(self):
            return self.selected_engine_id

        def list_voices(self):
            return ()

        def set_voice(self, voice_id):
            return None

        def get_supported_numeric_settings(self):
            return ()

        def set_rate(self, value):
            return None

        def set_pitch(self, value):
            return None

        def set_volume(self, value):
            return None

    class FakeScheduler:
        pass

    class FakeQueuedService:
        def __init__(self, *, speech):
            self.speech = speech

    class FakeTransport:
        def __init__(self, serializer):
            self.serializer = serializer

    fake_permissions = object()
    fake_backend = object()
    fake_manager = object()

    class FakeMacKeyboardCapture:
        def __init__(self, *, manager):
            self.manager = manager

    class FakeMacHotkeyCapture:
        def __init__(self, *, manager, key_code=103):
            self.manager = manager
            self.key_code = key_code

    class FakeManager:
        def __init__(self, *, permissions, backend):
            self.permissions = permissions
            self.backend = backend

    class FakeClipboard:
        pass

    class FakeKeyboardInputService:
        def __init__(self, capture, handler):
            self.capture = capture
            self.handler = handler

        def bind(self):
            return None

    class FakeAppService:
        enter_usage = HID.F11

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        def bind(self):
            return None

    class FakeApp:
        dispatch = staticmethod(lambda callback: callback())

        def __init__(self, controller, **kwargs):
            self.controller = controller

        def MainLoop(self):
            return 0

    monkeypatch.setitem(
        nvda_remote_main.build_runtime.__globals__,
        "JsonSpeechSettingsStore",
        FakeConfigStore,
    )
    monkeypatch.setattr(nvda_remote_main, "RelayTransport", FakeTransport)
    monkeypatch.setattr(accessibility_toolkit.runtime.platform, "_MacOSEventTapManager", FakeManager)
    monkeypatch.setattr(accessibility_toolkit.runtime.platform, "_MacOSEventTapBackend", lambda: fake_backend)
    monkeypatch.setattr(accessibility_toolkit.runtime.platform, "_MacOSKeyboardCapture", FakeMacKeyboardCapture)
    monkeypatch.setattr(accessibility_toolkit.runtime.platform, "_MacOSHotkeyCapture", FakeMacHotkeyCapture)
    monkeypatch.setattr(
        accessibility_toolkit.runtime.platform,
        "_AccessibilityPermissions",
        type(
            "FakePermissionsType",
            (),
            {"load_default": classmethod(lambda cls: fake_permissions)},
        ),
    )
    monkeypatch.setattr(accessibility_toolkit.runtime.platform, "create_clipboard_service", lambda: FakeClipboard())
    monkeypatch.setattr(
        accessibility_toolkit.runtime.platform,
        "default_speech_engine_options",
        fake_bootstrap_speech_engine_options,
    )
    monkeypatch.setattr(nvda_remote_main, "KeyboardInputService", FakeKeyboardInputService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteAppService", FakeAppService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteApp", FakeApp)
    monkeypatch.setattr(
        nvda_remote_main,
        "default_config_path",
        lambda app_name="accessibility-toolkit": f"{app_name}.json",
    )
    monkeypatch.setattr(accessibility_toolkit.runtime.platform.sys, "platform", "darwin")

    runtime = nvda_remote_main.build_runtime()

    assert isinstance(runtime.input_capture, FakeMacKeyboardCapture)
    assert isinstance(runtime.hotkey_capture, FakeMacHotkeyCapture)
    assert isinstance(runtime.input_capture.manager, FakeManager)
    assert runtime.input_capture.manager is runtime.hotkey_capture.manager
    assert runtime.input_capture.manager.permissions is fake_permissions
    assert runtime.input_capture.manager.backend is fake_backend
    assert isinstance(runtime.clipboard, FakeClipboard)


def test_build_runtime_uses_safe_clipboard_on_darwin(monkeypatch):
    install_fake_wx(monkeypatch)
    nvda_remote_main = importlib.import_module("apps.nvda_remote.main")

    class FakeConfigStore:
        def __init__(self, path):
            self.path = path

        def load_engine_id(self, *, default_engine_id):
            return "Pyttsx3"

        def save_engine_id(self, engine_id):
            return None

        def load_voice(self, engine_id):
            return None

        def save_voice(self, engine_id, voice_id):
            return None

        def load_numeric_setting(self, engine_id, setting_id):
            return None

        def save_numeric_setting(self, engine_id, setting_id, value):
            return None

    class FakeSpeechService:
        def __init__(self, *, engine_options, selected_engine_id, scheduler=None):
            self.engine_options = engine_options
            self.selected_engine_id = selected_engine_id

        def get_selected_engine(self):
            return self.selected_engine_id

        def list_voices(self):
            return ()

        def set_voice(self, voice_id):
            return None

        def get_supported_numeric_settings(self):
            return ()

        def set_rate(self, value):
            return None

        def set_pitch(self, value):
            return None

        def set_volume(self, value):
            return None

    class FakeScheduler:
        pass

    class FakeQueuedService:
        def __init__(self, *, speech):
            self.speech = speech

    class FakeTransport:
        def __init__(self, serializer):
            self.serializer = serializer

    class FakeMacKeyboardCapture:
        def __init__(self, *, manager):
            self.manager = manager

    class FakeMacHotkeyCapture:
        def __init__(self, *, manager, key_code=103):
            self.manager = manager
            self.key_code = key_code

    class FakeManager:
        def __init__(self, *, permissions, backend):
            self.permissions = permissions
            self.backend = backend

    class FakeKeyboardInputService:
        def __init__(self, capture, handler):
            self.capture = capture
            self.handler = handler

        def bind(self):
            return None

    class FakeAppService:
        enter_usage = HID.F11

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        def bind(self):
            return None

    class FakeApp:
        dispatch = staticmethod(lambda callback: callback())

        def __init__(self, controller, **kwargs):
            self.controller = controller

        def MainLoop(self):
            return 0

    monkeypatch.setitem(
        nvda_remote_main.build_runtime.__globals__,
        "JsonSpeechSettingsStore",
        FakeConfigStore,
    )
    monkeypatch.setattr(nvda_remote_main, "RelayTransport", FakeTransport)
    monkeypatch.setattr(accessibility_toolkit.runtime.platform, "_MacOSEventTapManager", FakeManager)
    monkeypatch.setattr(accessibility_toolkit.runtime.platform, "_MacOSEventTapBackend", lambda: object())
    monkeypatch.setattr(accessibility_toolkit.runtime.platform, "_MacOSKeyboardCapture", FakeMacKeyboardCapture)
    monkeypatch.setattr(accessibility_toolkit.runtime.platform, "_MacOSHotkeyCapture", FakeMacHotkeyCapture)
    monkeypatch.setattr(
        accessibility_toolkit.runtime.platform,
        "_AccessibilityPermissions",
        type(
            "FakePermissionsType",
            (),
            {"load_default": classmethod(lambda cls: object())},
        ),
    )
    monkeypatch.setattr(
        accessibility_toolkit.runtime.platform,
        "default_speech_engine_options",
        fake_bootstrap_speech_engine_options,
    )
    monkeypatch.setattr(nvda_remote_main, "KeyboardInputService", FakeKeyboardInputService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteAppService", FakeAppService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteApp", FakeApp)
    monkeypatch.setattr(
        nvda_remote_main,
        "default_config_path",
        lambda app_name="accessibility-toolkit": f"{app_name}.json",
    )
    monkeypatch.setattr(accessibility_toolkit.runtime.platform.sys, "platform", "darwin")

    runtime = nvda_remote_main.build_runtime()

    runtime.clipboard.set_text("hello")
    assert runtime.clipboard.get_text() == ""


def test_unavailable_macos_permissions_exposes_input_monitoring_error(monkeypatch):
    install_fake_wx(monkeypatch)
    permissions = accessibility_toolkit.runtime.platform._UnavailableMacOSPermissions()

    with pytest.raises(
        RuntimeError,
        match="macOS input monitoring permission wiring is unavailable",
    ):
        permissions.has_listen_event_access(prompt=False)


def test_nvda_remote_main_build_runtime_falls_back_for_unknown_engine(monkeypatch):
    install_fake_wx(monkeypatch)
    nvda_remote_main = importlib.import_module("apps.nvda_remote.main")

    class FakeConfigStore:
        def __init__(self, path):
            self.path = path
            self.saved = []

        def load_engine_id(self, *, default_engine_id):
            self.default_engine_id = default_engine_id
            return "missing"

        def save_engine_id(self, engine_id):
            self.saved.append(engine_id)

        def load_voice(self, engine_id):
            return None

        def save_voice(self, engine_id, voice_id):
            return None

        def load_numeric_setting(self, engine_id, setting_id):
            return None

        def save_numeric_setting(self, engine_id, setting_id, value):
            return None

    class FakeSpeechService:
        init_calls = []

        def __init__(self, *, engine_options, selected_engine_id, scheduler=None):
            self.engine_options = engine_options
            self.selected_engine_id = selected_engine_id
            type(self).init_calls.append(selected_engine_id)
            if selected_engine_id == "missing":
                raise ValueError("Unknown speech engine: missing")

        def get_selected_engine(self):
            return self.selected_engine_id

        def list_voices(self):
            return ()

        def set_voice(self, voice_id):
            return None

        def get_supported_numeric_settings(self):
            return ()

        def set_rate(self, value):
            return None

        def set_pitch(self, value):
            return None

        def set_volume(self, value):
            return None

    class FakeScheduler:
        pass

    class FakeQueuedService:
        def __init__(self, *, speech):
            self.speech = speech

    class FakeTransport:
        def __init__(self, serializer):
            self.serializer = serializer

    class FakeKeyboardCapture:
        pass

    class FakeHotkeyCapture:
        pass

    class FakeClipboard:
        pass

    class FakeKeyboardInputService:
        def __init__(self, capture, handler):
            self.capture = capture
            self.handler = handler

        def bind(self):
            return None

    class FakeAppService:
        enter_usage = HID.F11

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        def bind(self):
            return None

    class FakeApp:
        dispatch = staticmethod(lambda callback: callback())

        def __init__(self, controller, **kwargs):
            self.controller = controller

        def MainLoop(self):
            return 0

    monkeypatch.setitem(
        nvda_remote_main.build_runtime.__globals__,
        "JsonSpeechSettingsStore",
        FakeConfigStore,
    )
    monkeypatch.setattr(nvda_remote_main, "RelayTransport", FakeTransport)
    monkeypatch.setattr(accessibility_toolkit.runtime.platform.sys, "platform", "win32")
    scheduler = FakeScheduler()
    speech = FakeSpeechService(
        engine_options=("engine",),
        selected_engine_id="NvdaController",
        scheduler=scheduler,
    )
    speaker = FakeQueuedService(speech=speech)
    build_calls = []

    def fake_build_app_runtime_parts(**kwargs):
        build_calls.append(kwargs)
        assert kwargs["selected_engine_id"] == "missing"
        assert kwargs["fallback_engine_id"] == "NvdaController"
        assert kwargs["include_clipboard"] is True
        kwargs["on_engine_fallback"]("NvdaController")
        return types.SimpleNamespace(
            input_capture=FakeKeyboardCapture(),
            hotkey_capture=FakeHotkeyCapture(),
            clipboard=FakeClipboard(),
            tone_output=None,
            output=types.SimpleNamespace(
                scheduler=scheduler,
                speech=speech,
                speaker=speaker,
                capabilities=types.SimpleNamespace(speech=speaker, tone=None),
            ),
        )

    monkeypatch.setattr(
        nvda_remote_main,
        "build_app_runtime_parts",
        fake_build_app_runtime_parts,
    )
    monkeypatch.setattr(nvda_remote_main, "KeyboardInputService", FakeKeyboardInputService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteAppService", FakeAppService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteApp", FakeApp)
    monkeypatch.setattr(
        nvda_remote_main,
        "default_config_path",
        lambda app_name="accessibility-toolkit": f"{app_name}.json",
    )

    runtime = nvda_remote_main.build_runtime()

    assert len(build_calls) == 1
    assert runtime.config_store.saved == ["NvdaController"]
    assert runtime.scheduler is scheduler
    assert runtime.speech.selected_engine_id == "NvdaController"
    assert runtime.speaker.speech is runtime.speech
    assert runtime.app_service.use_windows_native_key_payload is False


def test_nvda_remote_main_build_runtime_enables_windows_native_payload_from_env(monkeypatch):
    install_fake_wx(monkeypatch)
    nvda_remote_main = importlib.import_module("apps.nvda_remote.main")

    class FakeConfigStore:
        def __init__(self, path):
            self.path = path

        def load_engine_id(self, *, default_engine_id):
            self.default_engine_id = default_engine_id
            return default_engine_id

        def save_engine_id(self, engine_id):
            self.saved_engine_id = engine_id

        def load_voice(self, engine_id):
            return None

        def save_voice(self, engine_id, voice_id):
            return None

        def load_numeric_setting(self, engine_id, setting_id):
            return None

        def save_numeric_setting(self, engine_id, setting_id, value):
            return None

    class FakeTransport:
        def __init__(self, serializer):
            self.serializer = serializer

    class FakeKeyboardCapture:
        def start(self):
            return None

        def stop(self):
            return None

    class FakeHotkeyCapture(FakeKeyboardCapture):
        pass

    class FakeClipboard:
        def get_text(self):
            return ""

        def set_text(self, text):
            del text

    class FakeScheduler:
        pass

    class FakeSpeechService:
        def __init__(self):
            self.selected_engine_id = "NvdaController"

        def get_selected_engine(self):
            return self.selected_engine_id

        def list_voices(self):
            return ()

        def set_voice(self, voice_id):
            return None

        def get_supported_numeric_settings(self):
            return ()

        def set_rate(self, value):
            return None

        def set_pitch(self, value):
            return None

        def set_volume(self, value):
            return None

    class FakeQueuedService:
        def __init__(self, speech):
            self.speech = speech

    class FakeKeyboardInputService:
        def __init__(self, capture, handler):
            self.capture = capture
            self.handler = handler

        def bind(self):
            return None

    class FakeAppService:
        enter_usage = HID.F11

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        def bind(self):
            return None

    class FakeApp:
        dispatch = staticmethod(lambda callback: callback())

        def __init__(self, controller, **kwargs):
            self.controller = controller

        def MainLoop(self):
            return 0

    monkeypatch.setitem(
        nvda_remote_main.build_runtime.__globals__,
        "JsonSpeechSettingsStore",
        FakeConfigStore,
    )
    monkeypatch.setattr(nvda_remote_main, "RelayTransport", FakeTransport)
    monkeypatch.setattr(accessibility_toolkit.runtime.platform.sys, "platform", "win32")
    scheduler = FakeScheduler()
    speech = FakeSpeechService()
    speaker = FakeQueuedService(speech=speech)

    monkeypatch.setattr(
        nvda_remote_main,
        "build_app_runtime_parts",
        lambda **kwargs: types.SimpleNamespace(
            input_capture=FakeKeyboardCapture(),
            hotkey_capture=FakeHotkeyCapture(),
            clipboard=FakeClipboard(),
            tone_output=None,
            output=types.SimpleNamespace(
                scheduler=scheduler,
                speech=speech,
                speaker=speaker,
                capabilities=types.SimpleNamespace(speech=speaker, tone=None),
            ),
        ),
    )
    monkeypatch.setattr(nvda_remote_main, "KeyboardInputService", FakeKeyboardInputService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteAppService", FakeAppService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteApp", FakeApp)
    monkeypatch.setattr(
        nvda_remote_main,
        "default_config_path",
        lambda app_name="accessibility-toolkit": f"{app_name}.json",
    )
    monkeypatch.setenv("NVDA_REMOTE_USE_WINDOWS_NATIVE_KEY_PAYLOAD", "1")

    runtime = nvda_remote_main.build_runtime()

    assert runtime.app_service.use_windows_native_key_payload is True


def test_nvda_remote_main_continues_startup_when_logging_setup_fails(monkeypatch):
    install_fake_wx(monkeypatch)
    nvda_remote_main = importlib.import_module("apps.nvda_remote.main")
    runtime = types.SimpleNamespace(app=types.SimpleNamespace(MainLoop=lambda: 91))

    def fail_logging(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(nvda_remote_main, "configure_logging", fail_logging)
    monkeypatch.setattr(nvda_remote_main, "build_runtime", lambda: runtime)

    assert nvda_remote_main.main() == 91


def test_nvda_remote_configure_logging_preserves_existing_handlers(monkeypatch):
    install_fake_wx(monkeypatch)
    nvda_remote_main = importlib.import_module("apps.nvda_remote.main")
    root_logger = nvda_remote_main.logging.getLogger()
    original_handlers = list(root_logger.handlers)
    sentinel_handler = nvda_remote_main.logging.NullHandler()
    root_logger.addHandler(sentinel_handler)
    added_handlers = []

    class FakeFileHandler:
        def __init__(self, path, mode="a", encoding=None):
            self.path = path
            self.mode = mode
            self.encoding = encoding
            self.formatter = None
            self.level = None

        def setFormatter(self, formatter):
            self.formatter = formatter

        def setLevel(self, level):
            self.level = level

    monkeypatch.setattr(accessibility_toolkit.runtime.environment, "default_log_path", lambda _app_name=None: "nvda.log")
    monkeypatch.setattr(nvda_remote_main.logging, "FileHandler", FakeFileHandler)
    monkeypatch.setenv("ACCESSIBILITY_TOOLKIT_LOGGING", "1")
    monkeypatch.setattr(
        root_logger,
        "addHandler",
        lambda handler: added_handlers.append(handler),
    )

    basic_config_calls = []

    def fake_basic_config(**kwargs):
        basic_config_calls.append(kwargs)

    monkeypatch.setattr(nvda_remote_main.logging, "basicConfig", fake_basic_config)

    try:
        log_path = nvda_remote_main.configure_logging()
    finally:
        root_logger.handlers[:] = original_handlers

    assert log_path == "nvda.log"
    assert basic_config_calls == []
    assert len(added_handlers) == 1
    handler = added_handlers[0]
    assert handler.path == "nvda.log"
    assert handler.mode == "a"


def test_nvda_remote_main_main_runs_gui_app(monkeypatch):
    install_fake_wx(monkeypatch)
    nvda_remote_main = importlib.import_module("apps.nvda_remote.main")

    class FakeApp:
        def MainLoop(self):
            return 55

    runtime = types.SimpleNamespace(app=FakeApp())
    monkeypatch.setattr(nvda_remote_main, "build_runtime", lambda: runtime)

    assert nvda_remote_main.main() == 55


def test_nvda_remote_main_configures_named_logging_before_building_runtime(monkeypatch):
    install_fake_wx(monkeypatch)
    nvda_remote_main = importlib.import_module("apps.nvda_remote.main")
    calls = []

    class FakeApp:
        def MainLoop(self):
            calls.append(("mainloop", None))
            return 55

    runtime = types.SimpleNamespace(app=FakeApp())
    monkeypatch.setattr(
        nvda_remote_main,
        "configure_logging",
        lambda app_name="": calls.append(("configure_logging", app_name)),
    )
    monkeypatch.setattr(
        nvda_remote_main,
        "build_runtime",
        lambda: calls.append(("build_runtime", None)) or runtime,
    )

    assert nvda_remote_main.main() == 55
    assert calls == [
        ("configure_logging", "nvda_remote"),
        ("build_runtime", None),
        ("mainloop", None),
    ]


def test_default_config_path_uses_executable_parent_for_frozen_macos(monkeypatch):
    install_fake_wx(monkeypatch)
    nvda_remote_main = importlib.import_module("apps.nvda_remote.main")

    monkeypatch.setattr(accessibility_toolkit.runtime.environment.sys, "frozen", True, raising=False)
    monkeypatch.setattr(accessibility_toolkit.runtime.environment.sys, "executable", "/Applications/NVDARemote.app/Contents/MacOS/NVDARemote")
    monkeypatch.setattr(accessibility_toolkit.runtime.environment.sys, "platform", "darwin")

    assert (
        nvda_remote_main.default_config_path()
        == accessibility_toolkit.runtime.environment.Path("/Applications/NVDARemote.app/Contents/MacOS/accessibility-toolkit.json")
    )


def test_default_log_path_uses_executable_parent_for_frozen_macos(monkeypatch):
    install_fake_wx(monkeypatch)
    nvda_remote_main = importlib.import_module("apps.nvda_remote.main")

    monkeypatch.setattr(accessibility_toolkit.runtime.environment.sys, "frozen", True, raising=False)
    monkeypatch.setattr(accessibility_toolkit.runtime.environment.sys, "executable", "/Applications/NVDARemote.app/Contents/MacOS/NVDARemote")
    monkeypatch.setattr(accessibility_toolkit.runtime.environment.sys, "platform", "darwin")

    assert (
        accessibility_toolkit.runtime.environment.default_log_path()
        == accessibility_toolkit.runtime.environment.Path("/Applications/NVDARemote.app/Contents/MacOS/accessibility-toolkit.log")
    )


def test_speech_settings_frame_reads_and_writes_controller_values(monkeypatch):
    fake_wx = install_fake_wx(monkeypatch)

    class FakeController:
        def __init__(self):
            self.speech_engine_id = "Pyttsx3"
            self.speech_engine_calls = []
            self.available_voices = ()
            self.selected_voice = None
            self.rate = 60
            self.pitch = 50
            self.volume = 80
            self.voice_calls = []

        def get_speech_engine_options(self):
            return (("NvdaController", "Nvda Controller"), ("Pyttsx3", "Pyttsx3"))

        def get_selected_speech_engine(self):
            return self.speech_engine_id

        def set_speech_engine(self, engine_id):
            self.speech_engine_calls.append(engine_id)
            self.speech_engine_id = engine_id

        def get_available_voices(self):
            return self.available_voices

        def get_selected_voice(self):
            return self.selected_voice

        def set_selected_voice(self, voice_id):
            self.voice_calls.append(voice_id)
            self.selected_voice = voice_id

        def get_rate(self):
            return self.rate

        def set_rate(self, value):
            self.rate = value

        def get_pitch(self):
            return self.pitch

        def set_pitch(self, value):
            self.pitch = value

        def get_volume(self):
            return self.volume

        def set_volume(self, value):
            self.volume = value

        def get_supported_numeric_settings(self):
            return (
                SpeechNumericSetting("rate", "Rate"),
                SpeechNumericSetting("pitch", "Pitch"),
                SpeechNumericSetting("volume", "Volume"),
            )

    SpeechSettingsFrame = importlib.import_module("accessibility_toolkit_wx.speech.speech_settings_frame").SpeechSettingsFrame
    controller = FakeController()
    frame = SpeechSettingsFrame(controller=controller)

    assert frame.speech_engine_choice.GetString(0) == "Nvda Controller"
    assert frame.voice_choice.enabled is False
    assert frame.rate_slider.GetValue() == 60
    assert frame.pitch_slider.GetValue() == 50
    assert frame.volume_slider.GetValue() == 80
    assert frame.GetTitle() == "Speech Settings"

    frame.speech_engine_choice.SetSelection(1)
    frame._on_speech_engine_change(None)
    assert controller.speech_engine_calls == ["Pyttsx3"]


def test_access8graph_main_build_runtime_injects_tone_output(monkeypatch):
    install_fake_wx(monkeypatch)
    access8graph_main = importlib.import_module("apps.access8graph.main")

    class FakeScheduler:
        pass

    class FakeSpeechService:
        def __init__(self, *, engine_options, selected_engine_id, scheduler=None):
            self.engine_options = engine_options
            self.selected_engine_id = selected_engine_id
            self.scheduler = scheduler

        def get_selected_engine(self):
            return self.selected_engine_id

        def list_voices(self):
            return ()

        def get_supported_numeric_settings(self):
            return ()

        def set_voice(self, voice_id):
            return None

        def set_rate(self, value):
            return None

        def set_pitch(self, value):
            return None

        def set_volume(self, value):
            return None

    class FakeQueuedService:
        def __init__(self, *, speech):
            self.speech = speech

    class FakeConfigStore:
        def __init__(self, path):
            self.path = path

        def load_engine_id(self, *, default_engine_id):
            return "Pyttsx3"

        def save_engine_id(self, engine_id):
            return None

        def load_voice(self, engine_id):
            return None

        def save_voice(self, engine_id, voice_id):
            return None

        def load_numeric_setting(self, engine_id, setting_id):
            return None

        def save_numeric_setting(self, engine_id, setting_id, value):
            return None

    class FakeKeyboardCapture:
        pass

    class FakeHotkeyCapture:
        def __init__(self) -> None:
            self.started = 0

        def start(self):
            self.started += 1

    class FakeToneOutput:
        def __init__(self) -> None:
            self.calls = []

        def beep(self, hz, length, left=50, right=50):
            self.calls.append((hz, length, left, right))

    class FakeKeyboardInputService:
        def __init__(self, capture, handler):
            self.capture = capture
            self.handler = handler

    class FakeAppService:
        enter_usage = HID.F11

        def __init__(self, *, hotkey_capture, input_capture, capabilities,
                     main_thread_dispatch=None):
            self.hotkey_capture = hotkey_capture
            self.input_capture = input_capture
            self._capabilities = capabilities
            self.main_thread_dispatch = main_thread_dispatch
            self.attached_input_service = None
            self.bind_calls = 0

        def notify_speech_engine_changed(self, engine_id):
            pass

        def attach_input_service(self, input_service):
            self.attached_input_service = input_service

        def bind(self):
            self.bind_calls += 1

    class FakeApp:
        dispatch = staticmethod(lambda callback: callback())

        def __init__(self, controller, **kwargs):
            self.controller = controller
            self.speech_controller = kwargs.get("speech_controller")

    tone_output = FakeToneOutput()
    keyboard_capture = FakeKeyboardCapture()
    hotkey_capture = FakeHotkeyCapture()
    scheduler = FakeScheduler()
    speech = FakeSpeechService(
        engine_options=("engine",),
        selected_engine_id="pyttsx3",
        scheduler=scheduler,
    )
    speaker = FakeQueuedService(speech=speech)
    capabilities = types.SimpleNamespace(speech=speaker, tone=tone_output)

    def fake_build_app_runtime_parts(*, hotkey_usage, selected_engine_id,
                                     fallback_engine_id=None, on_engine_fallback=None, **kwargs):
        assert hotkey_usage == FakeAppService.enter_usage
        assert selected_engine_id == "Pyttsx3"
        assert kwargs == {}
        return types.SimpleNamespace(
            input_capture=keyboard_capture,
            hotkey_capture=hotkey_capture,
            tone_output=tone_output,
            output=types.SimpleNamespace(
                scheduler=scheduler,
                speech=speech,
                speaker=speaker,
                capabilities=capabilities,
            ),
        )

    monkeypatch.setattr(access8graph_main, "JsonSpeechSettingsStore", FakeConfigStore)
    monkeypatch.setattr(access8graph_main, "KeyboardInputService", FakeKeyboardInputService)
    monkeypatch.setattr(access8graph_main, "Access8GraphAppService", FakeAppService)
    monkeypatch.setattr(
        access8graph_main,
        "build_app_runtime_parts",
        fake_build_app_runtime_parts,
    )
    monkeypatch.setitem(
        sys.modules,
        "ui.access8graph.app",
        types.SimpleNamespace(Access8GraphApp=FakeApp),
    )

    runtime = access8graph_main.build_runtime()

    assert runtime.app_service._capabilities.speech is runtime.speaker
    assert runtime.app_service._capabilities.tone is tone_output
    assert runtime.tone_output is tone_output
    assert runtime.hotkey_capture is hotkey_capture
    assert runtime.hotkey_capture.started == 1
    assert runtime.scheduler is scheduler
    assert runtime.speech is speech
    assert runtime.speaker is speaker
    assert runtime.app_service.bind_calls == 1
    assert runtime.app.controller is runtime.app_service
    assert runtime.config_store is not None
