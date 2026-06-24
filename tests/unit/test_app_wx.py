import importlib
import ssl
import sys
import types

import pytest

import bootstrap.platform
import bootstrap.runtime
from application.events import ErrorRaised, SpeechEngineChanged
from application.output.speech import SpeechEngineOption, SpeechNumericSetting
from apps.key_echo.events import EchoStateChanged
from apps.nvda_remote.events import RemoteConnectionChanged
from interop.key import HID


UI_MODULES = (
    "ui.app",
    "ui.main",
    "ui.main_frame",
    "ui.nvda_remote.app",
    "ui.nvda_remote.main_frame",
    "ui.echo.app",
    "ui.echo.main_frame",
    "ui.shared.speech_controls",
    "ui.shared.speech_settings_frame",
    "apps.nvda_remote.main",
    "apps.key_echo.main",
    "apps.shared.tool_app_shell",
    "apps.shared.tray_icon",
    "apps.shared.panel_controller",
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
    fake_wx.VERTICAL = 1
    fake_wx.EXPAND = 2
    fake_wx.ALL = 4
    fake_wx.EVT_BUTTON = object()
    fake_wx.EVT_CHOICE = object()
    fake_wx.EVT_TEXT = object()
    fake_wx.EVT_SLIDER = object()
    fake_wx.EVT_CLOSE = object()
    fake_wx.EVT_MENU = object()
    fake_wx.OK = 16
    fake_wx.ICON_ERROR = 32
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
        def __init__(self, parent, value=""):
            self.parent = parent
            self._value = value
            self.enabled = True
            self.bindings = {}

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
        def __init__(self, parent, label):
            self.parent = parent
            self._label = label
            self.bindings = {}
            self.enabled = True

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

    class Menu:
        def __init__(self):
            self.items = []

        def Append(self, id_, label):
            item = type("MenuItem", (), {"id": id_, "label": label, "GetItemLabelText": lambda s=label: s})()
            self.items.append(item)
            return item

        def Bind(self, event, handler, id_=None):
            pass

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

    def MessageBox(message, caption, style):
        fake_wx.message_box_calls.append((message, caption, style))
        return 0

    def CallAfter(callback, *args, **kwargs):
        fake_wx.call_after_calls.append((callback, args, kwargs))
        return callback(*args, **kwargs)

    fake_wx.Frame = Frame
    fake_wx.Panel = Panel
    fake_wx.StaticText = StaticText
    fake_wx.BoxSizer = BoxSizer
    fake_wx.TextCtrl = TextCtrl
    fake_wx.Slider = Slider
    fake_wx.Button = Button
    fake_wx.Choice = Choice
    fake_wx.Menu = Menu
    fake_wx.App = App
    fake_wx.MessageBox = MessageBox
    fake_wx.CallAfter = CallAfter

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
    def __init__(self):
        self.connected_to = None
        self.connect_calls = []
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

    def connect(self, host, port, key, insecure=False):
        self.connect_calls.append((host, port, key, insecure))
        self.connected_to = (host, port, key, insecure)
        self.state.connection_state = "connected"
        self.state.control_state = "connected"
        if self.status_listener is not None:
            self.status_listener(RemoteConnectionChanged("connected"))

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


def test_main_frame_exposes_connect_controls(monkeypatch):
    install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("ui.nvda_remote.main_frame").MainFrame

    frame = MainFrame(controller=None)

    assert frame.GetTitle() == "NVDA Remote Client"
    assert frame.host_ctrl.GetValue() == ""
    assert frame.port_ctrl.GetValue() == "6837"
    assert frame.key_ctrl.GetValue() == ""
    assert frame.connect_button.GetLabel() == "Connect"
    assert frame.control_button.GetLabel() == "Start Control"
    assert frame.control_button.enabled is False
    assert frame.clipboard_button.GetLabel() == "Push Clipboard"
    assert frame.clipboard_button.enabled is False
    assert frame.host_ctrl.enabled is True
    assert frame.port_ctrl.enabled is True
    assert frame.key_ctrl.enabled is True


def test_main_frame_dispatches_button_actions(monkeypatch):
    install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("ui.nvda_remote.main_frame").MainFrame
    controller = FakeController()
    frame = MainFrame(controller=controller)
    frame.host_ctrl.SetValue("relay.example")
    frame.port_ctrl.SetValue("7000")
    frame.key_ctrl.SetValue("secret")

    frame._on_connect(None)
    frame._on_start_control(None)
    frame._on_push_clipboard(None)

    assert controller.connected_to == ("relay.example", 7000, "secret", False)
    assert controller.started_control == 1
    assert controller.pushed_clipboard == 1
    assert frame.connect_button.GetLabel() == "Disconnect"
    assert frame.control_button.GetLabel() == "Stop Control"
    assert frame.control_button.enabled is True
    assert frame.clipboard_button.enabled is True
    assert frame.host_ctrl.enabled is False
    assert frame.port_ctrl.enabled is False
    assert frame.key_ctrl.enabled is False


def test_main_frame_toggles_disconnect_when_already_connected(monkeypatch):
    install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("ui.nvda_remote.main_frame").MainFrame
    controller = FakeController()
    frame = MainFrame(controller=controller)

    frame._on_connect(None)
    frame._on_connect(None)

    assert controller.connect_calls == [("", 6837, "", False)]
    assert controller.disconnect_calls == 1
    assert frame.connect_button.GetLabel() == "Connect"
    assert frame.control_button.GetLabel() == "Start Control"
    assert frame.control_button.enabled is False
    assert frame.clipboard_button.enabled is False
    assert frame.host_ctrl.enabled is True
    assert frame.port_ctrl.enabled is True
    assert frame.key_ctrl.enabled is True


def test_main_frame_control_button_is_disabled_until_connected(monkeypatch):
    install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("ui.nvda_remote.main_frame").MainFrame
    controller = FakeController()
    frame = MainFrame(controller=controller)

    assert frame.control_button.enabled is False

    frame._on_connect(None)

    assert frame.control_button.enabled is True
    assert frame.control_button.GetLabel() == "Start Control"
    assert frame.clipboard_button.enabled is True


def test_main_frame_disables_clipboard_button_when_clipboard_unavailable(monkeypatch):
    install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("ui.nvda_remote.main_frame").MainFrame
    controller = FakeController()
    controller.clipboard_available = False
    frame = MainFrame(controller=controller)

    frame._on_connect(None)

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


def test_main_frame_locks_connection_fields_while_connected(monkeypatch):
    install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("ui.nvda_remote.main_frame").MainFrame
    controller = FakeController()
    frame = MainFrame(controller=controller)

    frame._on_connect(None)

    assert frame.host_ctrl.enabled is False
    assert frame.port_ctrl.enabled is False
    assert frame.key_ctrl.enabled is False

    frame._on_connect(None)

    assert frame.host_ctrl.enabled is True
    assert frame.port_ctrl.enabled is True
    assert frame.key_ctrl.enabled is True


def test_main_frame_control_button_toggles_start_and_stop(monkeypatch):
    install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("ui.nvda_remote.main_frame").MainFrame
    controller = FakeController()
    frame = MainFrame(controller=controller)

    frame._on_connect(None)
    frame._on_start_control(None)
    frame._on_start_control(None)

    assert controller.started_control == 1
    assert controller.stopped_control == 1
    assert frame.control_button.GetLabel() == "Start Control"
    assert frame.control_button.enabled is True


def test_main_frame_disconnect_stops_control_first(monkeypatch):
    install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("ui.nvda_remote.main_frame").MainFrame
    controller = FakeController()
    frame = MainFrame(controller=controller)

    frame._on_connect(None)
    frame._on_start_control(None)
    frame._on_connect(None)

    assert controller.stopped_control == 1
    assert controller.disconnect_calls == 1
    assert frame.control_button.GetLabel() == "Start Control"
    assert frame.control_button.enabled is False


def test_main_frame_syncs_buttons_after_control_stops_outside_ui(monkeypatch):
    install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("ui.nvda_remote.main_frame").MainFrame
    controller = FakeController()
    frame = MainFrame(controller=controller)

    frame._on_connect(None)
    frame._on_start_control(None)
    controller.stop_control()

    assert frame.connect_button.GetLabel() == "Disconnect"
    assert frame.control_button.GetLabel() == "Start Control"
    assert frame.control_button.enabled is True


def test_main_frame_retries_self_signed_certificate_in_insecure_mode(monkeypatch):
    fake_wx = install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("ui.nvda_remote.main_frame").MainFrame

    class SelfSignedController(FakeController):
        def connect(self, host, port, key, insecure=False):
            self.connect_calls.append((host, port, key, insecure))
            if not insecure:
                raise ssl.SSLCertVerificationError("self-signed certificate")
            self.connected_to = (host, port, key, insecure)

    controller = SelfSignedController()
    frame = MainFrame(controller=controller)
    frame.host_ctrl.SetValue("114.34.83.41")
    frame.port_ctrl.SetValue("6837")
    frame.key_ctrl.SetValue("secret")

    frame._on_connect(None)

    assert controller.connect_calls == [
        ("114.34.83.41", 6837, "secret", False),
        ("114.34.83.41", 6837, "secret", True),
    ]
    assert controller.connected_to == ("114.34.83.41", 6837, "secret", True)
    assert fake_wx.message_box_calls == []


def test_main_frame_shows_connection_error_for_invalid_port(monkeypatch):
    fake_wx = install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("ui.nvda_remote.main_frame").MainFrame
    controller = FakeController()
    frame = MainFrame(controller=controller)
    frame.host_ctrl.SetValue("relay.example")
    frame.port_ctrl.SetValue("bad-port")
    frame.key_ctrl.SetValue("secret")

    frame._on_connect(None)

    assert controller.connect_calls == []
    assert fake_wx.message_box_calls == [
        ("invalid literal for int() with base 10: 'bad-port'", "Connection Error", fake_wx.OK | fake_wx.ICON_ERROR)
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
            transport,
            input_capture,
            hotkey_capture,
            clipboard,
            capabilities,
            on_speech_engine_changed,
            on_voice_changed,
            on_numeric_setting_changed,
            main_thread_dispatch,
            use_windows_native_key_payload,
        ):
            self.transport = transport
            self.input_capture = input_capture
            self.hotkey_capture = hotkey_capture
            self.clipboard = clipboard
            self.capabilities = capabilities
            self.on_speech_engine_changed = on_speech_engine_changed
            self.on_voice_changed = on_voice_changed
            self.on_numeric_setting_changed = on_numeric_setting_changed
            self.main_thread_dispatch = main_thread_dispatch
            self.use_windows_native_key_payload = use_windows_native_key_payload
            self.bind_calls = 0

        def bind(self):
            self.bind_calls += 1

    class FakeApp:
        dispatch = staticmethod(lambda callback: callback())

        def __init__(self, controller):
            self.controller = controller

        def MainLoop(self):
            return 77

    monkeypatch.setitem(
        nvda_remote_main.build_runtime.__globals__,
        "SpeechEngineConfigStore",
        FakeConfigStore,
    )
    monkeypatch.setattr(nvda_remote_main, "RelayTransport", FakeTransport)
    monkeypatch.setattr(bootstrap.platform.sys, "platform", "win32")
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
    monkeypatch.setattr(nvda_remote_main, "default_config_path", lambda: "config.json")

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
    assert callable(runtime.app_service.on_speech_engine_changed)
    assert runtime.app_service.on_voice_changed == runtime.config_store.save_voice
    assert runtime.app_service.on_numeric_setting_changed == runtime.config_store.save_numeric_setting
    assert runtime.app_service.main_thread_dispatch is FakeApp.dispatch
    assert runtime.app_service.bind_calls == 1
    assert runtime.input_service.capture is runtime.input_capture
    assert runtime.input_service.handler is runtime.app_service
    assert runtime.input_service.bind_calls == 1
    assert runtime.app.controller is runtime.app_service


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

        def list_voices(self):
            return (
                ("voice-p", "Voice P"),
                ("voice-n", "Voice N"),
            )

        def set_voice(self, voice_id):
            self.voice_calls.append((self.selected_engine_id, voice_id))

        def get_supported_numeric_settings(self):
            return (
                SpeechNumericSetting(id="rate", label="Rate"),
                SpeechNumericSetting(id="pitch", label="Pitch"),
            )

        def set_rate(self, value):
            self.rate_calls.append((self.selected_engine_id, value))

        def set_pitch(self, value):
            self.pitch_calls.append((self.selected_engine_id, value))

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

        def bind(self):
            return None

    class FakeTransport:
        def __init__(self, serializer):
            self.serializer = serializer

    class FakeApp:
        dispatch = staticmethod(lambda callback: callback())

        def __init__(self, controller):
            self.controller = controller

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
        "SpeechEngineConfigStore",
        FakeConfigStore,
    )
    monkeypatch.setattr(nvda_remote_main, "RelayTransport", FakeTransport)
    monkeypatch.setattr(nvda_remote_main, "build_app_runtime_parts", fake_build_app_runtime_parts)
    monkeypatch.setattr(nvda_remote_main, "KeyboardInputService", FakeKeyboardInputService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteAppService", FakeAppService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteApp", FakeApp)
    monkeypatch.setattr(nvda_remote_main, "default_config_path", lambda: "config.json")

    runtime = nvda_remote_main.build_runtime()

    assert speech.voice_calls == [("Pyttsx3", "voice-p")]
    assert speech.rate_calls == [("Pyttsx3", 25)]
    assert speech.pitch_calls == []
    assert speech.volume_calls == []

    speech.selected_engine_id = "NvdaController"
    runtime.app_service.on_speech_engine_changed("NvdaController")

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

        def __init__(self, controller):
            self.controller = controller

        def MainLoop(self):
            return 0

    monkeypatch.setitem(
        nvda_remote_main.build_runtime.__globals__,
        "SpeechEngineConfigStore",
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
    monkeypatch.setattr(nvda_remote_main, "default_config_path", lambda: "config.json")

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

        def __init__(self, controller):
            self.controller = controller

        def MainLoop(self):
            return 0

    monkeypatch.setitem(
        nvda_remote_main.build_runtime.__globals__,
        "SpeechEngineConfigStore",
        FakeConfigStore,
    )
    monkeypatch.setattr(nvda_remote_main, "RelayTransport", FakeTransport)
    monkeypatch.setattr(bootstrap.platform, "_MacOSEventTapManager", FakeManager)
    monkeypatch.setattr(bootstrap.platform, "_MacOSEventTapBackend", lambda: fake_backend)
    monkeypatch.setattr(bootstrap.platform, "_MacOSKeyboardCapture", FakeMacKeyboardCapture)
    monkeypatch.setattr(bootstrap.platform, "_MacOSHotkeyCapture", FakeMacHotkeyCapture)
    monkeypatch.setattr(
        bootstrap.platform,
        "_AccessibilityPermissions",
        type(
            "FakePermissionsType",
            (),
            {"load_default": classmethod(lambda cls: fake_permissions)},
        ),
    )
    monkeypatch.setattr(bootstrap.platform, "create_clipboard_service", lambda: FakeClipboard())
    monkeypatch.setattr(
        bootstrap.platform,
        "default_speech_engine_options",
        fake_bootstrap_speech_engine_options,
    )
    monkeypatch.setattr(nvda_remote_main, "KeyboardInputService", FakeKeyboardInputService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteAppService", FakeAppService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteApp", FakeApp)
    monkeypatch.setattr(nvda_remote_main, "default_config_path", lambda: "config.json")
    monkeypatch.setattr(bootstrap.platform.sys, "platform", "darwin")

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

        def __init__(self, controller):
            self.controller = controller

        def MainLoop(self):
            return 0

    monkeypatch.setitem(
        nvda_remote_main.build_runtime.__globals__,
        "SpeechEngineConfigStore",
        FakeConfigStore,
    )
    monkeypatch.setattr(nvda_remote_main, "RelayTransport", FakeTransport)
    monkeypatch.setattr(bootstrap.platform, "_MacOSEventTapManager", FakeManager)
    monkeypatch.setattr(bootstrap.platform, "_MacOSEventTapBackend", lambda: object())
    monkeypatch.setattr(bootstrap.platform, "_MacOSKeyboardCapture", FakeMacKeyboardCapture)
    monkeypatch.setattr(bootstrap.platform, "_MacOSHotkeyCapture", FakeMacHotkeyCapture)
    monkeypatch.setattr(
        bootstrap.platform,
        "_AccessibilityPermissions",
        type(
            "FakePermissionsType",
            (),
            {"load_default": classmethod(lambda cls: object())},
        ),
    )
    monkeypatch.setattr(
        bootstrap.platform,
        "default_speech_engine_options",
        fake_bootstrap_speech_engine_options,
    )
    monkeypatch.setattr(nvda_remote_main, "KeyboardInputService", FakeKeyboardInputService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteAppService", FakeAppService)
    monkeypatch.setattr(nvda_remote_main, "NvdaRemoteApp", FakeApp)
    monkeypatch.setattr(nvda_remote_main, "default_config_path", lambda: "config.json")
    monkeypatch.setattr(bootstrap.platform.sys, "platform", "darwin")

    runtime = nvda_remote_main.build_runtime()

    runtime.clipboard.set_text("hello")
    assert runtime.clipboard.get_text() == ""


def test_unavailable_macos_permissions_exposes_input_monitoring_error(monkeypatch):
    install_fake_wx(monkeypatch)
    permissions = bootstrap.platform._UnavailableMacOSPermissions()

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

        def __init__(self, controller):
            self.controller = controller

        def MainLoop(self):
            return 0

    monkeypatch.setitem(
        nvda_remote_main.build_runtime.__globals__,
        "SpeechEngineConfigStore",
        FakeConfigStore,
    )
    monkeypatch.setattr(nvda_remote_main, "RelayTransport", FakeTransport)
    monkeypatch.setattr(bootstrap.platform.sys, "platform", "win32")
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
    monkeypatch.setattr(nvda_remote_main, "default_config_path", lambda: "config.json")

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

        def __init__(self, controller):
            self.controller = controller

        def MainLoop(self):
            return 0

    monkeypatch.setitem(
        nvda_remote_main.build_runtime.__globals__,
        "SpeechEngineConfigStore",
        FakeConfigStore,
    )
    monkeypatch.setattr(nvda_remote_main, "RelayTransport", FakeTransport)
    monkeypatch.setattr(bootstrap.platform.sys, "platform", "win32")
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
    monkeypatch.setattr(nvda_remote_main, "default_config_path", lambda: "config.json")
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

    monkeypatch.setattr(bootstrap.runtime, "default_log_path", lambda _app_name=None: "nvda.log")
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


def test_default_config_path_uses_app_support_for_frozen_macos(monkeypatch):
    install_fake_wx(monkeypatch)
    nvda_remote_main = importlib.import_module("apps.nvda_remote.main")

    monkeypatch.setattr(bootstrap.runtime.sys, "frozen", True, raising=False)
    monkeypatch.setattr(bootstrap.runtime.sys, "executable", "/Applications/NVDARemote.app/Contents/MacOS/NVDARemote")
    monkeypatch.setattr(bootstrap.runtime.sys, "platform", "darwin")
    monkeypatch.setattr(bootstrap.runtime.Path, "home", classmethod(lambda cls: cls("/Users/tester")))

    assert (
        nvda_remote_main.default_config_path()
        == bootstrap.runtime.Path("/Users/tester/Library/Application Support/accessibility-toolkit/accessibility-toolkit.json")
    )


def test_default_log_path_uses_library_logs_for_frozen_macos(monkeypatch):
    install_fake_wx(monkeypatch)
    nvda_remote_main = importlib.import_module("apps.nvda_remote.main")

    monkeypatch.setattr(bootstrap.runtime.sys, "frozen", True, raising=False)
    monkeypatch.setattr(bootstrap.runtime.sys, "executable", "/Applications/NVDARemote.app/Contents/MacOS/NVDARemote")
    monkeypatch.setattr(bootstrap.runtime.sys, "platform", "darwin")
    monkeypatch.setattr(bootstrap.runtime.Path, "home", classmethod(lambda cls: cls("/Users/tester")))

    assert (
        bootstrap.runtime.default_log_path()
        == bootstrap.runtime.Path("/Users/tester/Library/Logs/accessibility-toolkit/accessibility-toolkit.log")
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

    SpeechSettingsFrame = importlib.import_module("ui.shared.speech_settings_frame").SpeechSettingsFrame
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
                     on_speech_engine_changed=None, on_voice_changed=None,
                     on_numeric_setting_changed=None, main_thread_dispatch=None):
            self.hotkey_capture = hotkey_capture
            self.input_capture = input_capture
            self._capabilities = capabilities
            self.on_speech_engine_changed = on_speech_engine_changed
            self.main_thread_dispatch = main_thread_dispatch
            self.attached_input_service = None
            self.bind_calls = 0

        def attach_input_service(self, input_service):
            self.attached_input_service = input_service

        def bind(self):
            self.bind_calls += 1

    class FakeApp:
        dispatch = staticmethod(lambda callback: callback())

        def __init__(self, controller):
            self.controller = controller

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

    monkeypatch.setattr(access8graph_main, "SpeechEngineConfigStore", FakeConfigStore)
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
