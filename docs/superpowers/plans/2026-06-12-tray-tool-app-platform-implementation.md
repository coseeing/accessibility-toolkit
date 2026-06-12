# Tray Tool App Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a shared cross-platform tray/status-icon app platform for `key_echo` and `nvda_remote`, including shared speech settings control, hide-on-close panels, resident icon-menu app startup, and a reusable mode manager for active/inactive keyboard features.

**Architecture:** Introduce a shared app-platform layer under `src/apps/shared/` and migrate behavior in stages. First converge shared capabilities with low-risk refactors, then move the wx app lifecycle to a resident status-icon shell, then validate the reusable mode model in `key_echo` before connecting the same lifecycle contract to `nvda_remote`.

**Tech Stack:** Python, wxPython, pytest, protocol-driven application layer, existing `InputCapture` / `HotkeyCapture` abstractions

---

## File Structure

### New files

- `src/apps/shared/__init__.py`
  - shared app-platform package marker
- `src/apps/shared/speech_settings_controller.py`
  - shared speech backend / voice / rate / pitch / volume controller
- `src/apps/shared/panel_controller.py`
  - shared show/hide/focus panel lifecycle and close-to-hide behavior
- `src/apps/shared/tray_icon.py`
  - cross-platform `wx.adv.TaskBarIcon` wrapper and menu wiring
- `src/apps/shared/tool_app_shell.py`
  - resident app shell that composes tray icon, panels, and shutdown behavior
- `src/apps/shared/mode_types.py`
  - `ActivationMode` protocol and small hotkey/mode data types
- `src/apps/shared/mode_manager.py`
  - mode registration, activation, capture switching, active key routing
- `src/ui/shared/speech_settings_frame.py`
  - standalone speech settings panel
- `tests/unit/test_speech_settings_controller.py`
  - unit tests for shared speech settings controller
- `tests/unit/test_panel_controller.py`
  - unit tests for hide-on-close panel lifecycle
- `tests/unit/test_tray_icon.py`
  - unit tests for shared tray icon wrapper
- `tests/unit/test_tool_app_shell.py`
  - unit tests for app-shell startup and menu actions
- `tests/unit/test_mode_manager.py`
  - unit tests for mode registration and transitions

### Existing files to modify

- `src/apps/key_echo/facade.py`
  - replace app-specific speech settings plumbing and later adopt mode manager
- `src/apps/nvda_remote/facade.py`
  - replace app-specific speech settings plumbing and later connect mode lifecycle
- `src/apps/key_echo/use_cases/speech_settings.py`
  - remove or collapse into compatibility wrapper
- `src/apps/nvda_remote/use_cases/speech_settings.py`
  - remove or collapse into compatibility wrapper
- `src/application/input/activation.py`
  - evolve into mode-aware activation helper or keep as lower-level collaborator used by `ModeManager`
- `src/application/input/active_key_policy.py`
  - evolve into active-mode-aware routing
- `src/ui/echo/app.py`
  - stop directly showing main frame at startup and adopt shell
- `src/ui/nvda_remote/app.py`
  - stop directly showing main frame at startup and adopt shell
- `src/ui/echo/main_frame.py`
  - remove embedded speech settings UI and support hide-on-close
- `src/ui/nvda_remote/main_frame.py`
  - remove embedded speech settings UI and support hide-on-close
- `src/ui/shared/speech_controls.py`
  - narrow or retire once speech settings move to a standalone panel
- `tests/unit/test_app_wx.py`
  - expand fake wx coverage for frame close, tray icon, and shell integration
- `tests/unit/test_key_echo_app_service.py`
  - update for shared controller and later mode-manager wiring
- `tests/unit/test_nvda_remote_app_service.py`
  - update for shared controller and later mode-manager wiring

### Existing files to read before implementation

- `src/ui/echo/app.py`
- `src/ui/nvda_remote/app.py`
- `src/ui/echo/main_frame.py`
- `src/ui/nvda_remote/main_frame.py`
- `src/ui/shared/speech_controls.py`
- `src/apps/key_echo/facade.py`
- `src/apps/nvda_remote/facade.py`
- `src/application/input/activation.py`
- `src/application/input/active_key_policy.py`
- `tests/unit/test_app_wx.py`
- `tests/unit/test_key_echo_app_service.py`
- `tests/unit/test_nvda_remote_app_service.py`

## Task 1: Extract Shared SpeechSettingsController

**Files:**
- Create: `src/apps/shared/__init__.py`
- Create: `src/apps/shared/speech_settings_controller.py`
- Create: `tests/unit/test_speech_settings_controller.py`
- Modify: `src/apps/key_echo/facade.py`
- Modify: `src/apps/nvda_remote/facade.py`
- Modify: `src/apps/key_echo/use_cases/speech_settings.py`
- Modify: `src/apps/nvda_remote/use_cases/speech_settings.py`
- Test: `tests/unit/test_speech_settings_controller.py`
- Test: `tests/unit/test_key_echo_app_service.py`
- Test: `tests/unit/test_nvda_remote_app_service.py`

- [ ] **Step 1: Write the failing controller tests**

```python
from apps.shared.speech_settings_controller import SpeechSettingsController


class FakeSpeech:
    def __init__(self):
        self.backend_id = "default"
        self.voice_id = "voice-1"
        self.rate = 50
        self.pitch = 40
        self.volume = 90
        self.backend_calls = []

    def get_backend_options(self):
        return (("default", "Default"), ("alt", "Alt"))

    def get_selected_backend(self):
        return self.backend_id

    def set_backend(self, backend_id):
        self.backend_calls.append(backend_id)
        self.backend_id = backend_id

    def list_voices(self):
        return (("voice-1", "Voice 1"), ("voice-2", "Voice 2"))

    def get_voice(self):
        return self.voice_id

    def set_voice(self, voice_id):
        self.voice_id = voice_id

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


def test_speech_settings_controller_proxies_backend_and_voice_settings():
    speech = FakeSpeech()
    controller = SpeechSettingsController(speech=speech)

    controller.set_backend("alt")
    controller.set_voice("voice-2")
    controller.set_rate(60)
    controller.set_pitch(55)
    controller.set_volume(80)

    assert controller.get_selected_backend() == "alt"
    assert controller.get_voice() == "voice-2"
    assert controller.get_rate() == 60
    assert controller.get_pitch() == 55
    assert controller.get_volume() == 80


def test_speech_settings_controller_calls_backend_changed_callback():
    seen = []
    speech = FakeSpeech()
    controller = SpeechSettingsController(
        speech=speech,
        on_backend_changed=seen.append,
    )

    controller.set_backend("alt")

    assert seen == ["alt"]
```

- [ ] **Step 2: Run the controller tests to verify they fail**

Run: `pytest tests/unit/test_speech_settings_controller.py -v`
Expected: FAIL with `ModuleNotFoundError` for `apps.shared.speech_settings_controller`

- [ ] **Step 3: Write the minimal shared controller**

```python
from collections.abc import Callable

from application.output_service import SpeechOutputService


class SpeechSettingsController:
    def __init__(
        self,
        *,
        speech: SpeechOutputService,
        on_backend_changed: Callable[[str], None] | None = None,
    ) -> None:
        self._speech = speech
        self._on_backend_changed = on_backend_changed

    def get_backend_options(self) -> tuple[tuple[str, str], ...]:
        return self._speech.get_backend_options()

    def get_selected_backend(self) -> str:
        return self._speech.get_selected_backend()

    def set_backend(self, backend_id: str) -> None:
        self._speech.set_backend(backend_id)
        if self._on_backend_changed is not None:
            self._on_backend_changed(backend_id)

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return self._speech.list_voices()

    def get_voice(self) -> str | None:
        return self._speech.get_voice()

    def set_voice(self, voice_id: str) -> None:
        self._speech.set_voice(voice_id)

    def get_rate(self) -> int | None:
        return self._speech.get_rate()

    def set_rate(self, value: int) -> None:
        self._speech.set_rate(value)

    def get_pitch(self) -> int | None:
        return self._speech.get_pitch()

    def set_pitch(self, value: int) -> None:
        self._speech.set_pitch(value)

    def get_volume(self) -> int | None:
        return self._speech.get_volume()

    def set_volume(self, value: int) -> None:
        self._speech.set_volume(value)
```

- [ ] **Step 4: Rewire both app facades to use the shared controller**

```python
from apps.shared.speech_settings_controller import SpeechSettingsController


self._speech_settings = SpeechSettingsController(
    speech=speech,
    on_backend_changed=_on_backend_changed_wrapper,
)
```

```python
from apps.shared.speech_settings_controller import SpeechSettingsController


self._speech_settings = SpeechSettingsController(speech=outputs.speech)
```

For the app-specific `speech_settings.py` files, either:

```python
from apps.shared.speech_settings_controller import SpeechSettingsController as NvdaRemoteSpeechSettingsUseCase
```

and

```python
from apps.shared.speech_settings_controller import SpeechSettingsController as KeyEchoSpeechSettingsUseCase
```

or remove them in a later cleanup task after all imports are updated.

- [ ] **Step 5: Run focused tests**

Run:

```bash
pytest tests/unit/test_speech_settings_controller.py \
  tests/unit/test_key_echo_app_service.py \
  tests/unit/test_nvda_remote_app_service.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add \
  src/apps/shared/__init__.py \
  src/apps/shared/speech_settings_controller.py \
  src/apps/key_echo/facade.py \
  src/apps/nvda_remote/facade.py \
  src/apps/key_echo/use_cases/speech_settings.py \
  src/apps/nvda_remote/use_cases/speech_settings.py \
  tests/unit/test_speech_settings_controller.py
git commit -m "refactor: extract shared speech settings controller"
```

## Task 2: Introduce PanelController and Hide-on-Close Panels

**Files:**
- Create: `src/apps/shared/panel_controller.py`
- Create: `tests/unit/test_panel_controller.py`
- Modify: `src/ui/echo/main_frame.py`
- Modify: `src/ui/nvda_remote/main_frame.py`
- Modify: `tests/unit/test_app_wx.py`
- Test: `tests/unit/test_panel_controller.py`
- Test: `tests/unit/test_app_wx.py`

- [ ] **Step 1: Write the failing panel lifecycle tests**

```python
from apps.shared.panel_controller import PanelController


class FakeFrame:
    def __init__(self):
        self.hidden = 0
        self.shown = 0
        self.raised = 0

    def Show(self, show=True):
        if show:
            self.shown += 1

    def Hide(self):
        self.hidden += 1

    def Raise(self):
        self.raised += 1


def test_show_panel_shows_and_raises_existing_frame():
    frame = FakeFrame()
    controller = PanelController()
    controller.register("main", frame)

    controller.show("main")

    assert frame.shown == 1
    assert frame.raised == 1


def test_close_handler_hides_panel_instead_of_exiting():
    frame = FakeFrame()
    controller = PanelController()
    controller.register("main", frame)

    controller.hide("main")

    assert frame.hidden == 1
```

- [ ] **Step 2: Run the panel tests to verify they fail**

Run: `pytest tests/unit/test_panel_controller.py -v`
Expected: FAIL with `ModuleNotFoundError` for `apps.shared.panel_controller`

- [ ] **Step 3: Implement the minimal panel controller**

```python
class PanelController:
    def __init__(self) -> None:
        self._panels: dict[str, object] = {}

    def register(self, panel_id: str, frame: object) -> None:
        self._panels[panel_id] = frame

    def show(self, panel_id: str) -> None:
        frame = self._panels[panel_id]
        frame.Show(True)
        if hasattr(frame, "Raise"):
            frame.Raise()

    def hide(self, panel_id: str) -> None:
        frame = self._panels[panel_id]
        frame.Hide()
```

- [ ] **Step 4: Update wx frames to hide on close**

Add a close handler to each frame:

```python
def _on_close(self, event) -> None:
    self.Hide()
    if hasattr(event, "Veto"):
        event.Veto()
```

Bind it:

```python
self.Bind(wx.EVT_CLOSE, self._on_close)
```

Extend the fake `wx.Frame` in `tests/unit/test_app_wx.py` with:

```python
def Hide(self):
    self.shown = False

def Raise(self):
    self.raised = True

def Bind(self, event, handler):
    self.bindings[event] = handler
```

- [ ] **Step 5: Run focused tests**

Run:

```bash
pytest tests/unit/test_panel_controller.py tests/unit/test_app_wx.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add \
  src/apps/shared/panel_controller.py \
  src/ui/echo/main_frame.py \
  src/ui/nvda_remote/main_frame.py \
  tests/unit/test_panel_controller.py \
  tests/unit/test_app_wx.py
git commit -m "feat: add shared panel hide-on-close controller"
```

## Task 3: Add Standalone Speech Settings Panel and Remove Embedded Controls

**Files:**
- Create: `src/ui/shared/speech_settings_frame.py`
- Modify: `src/ui/shared/speech_controls.py`
- Modify: `src/ui/echo/main_frame.py`
- Modify: `src/ui/nvda_remote/main_frame.py`
- Modify: `tests/unit/test_app_wx.py`
- Test: `tests/unit/test_app_wx.py`

- [ ] **Step 1: Write the failing speech settings frame test**

```python
def test_speech_settings_frame_reads_and_writes_controller_values():
    from ui.shared.speech_settings_frame import SpeechSettingsFrame

    controller = FakeController()
    controller.available_voices = (("voice-1", "Voice 1"),)

    frame = SpeechSettingsFrame(controller=controller)

    assert frame.speech_backend_choice.GetCount() >= 1
    assert frame.voice_choice.GetCount() == 1
```

- [ ] **Step 2: Run the speech settings frame test to verify it fails**

Run: `pytest tests/unit/test_app_wx.py::test_speech_settings_frame_reads_and_writes_controller_values -v`
Expected: FAIL with `ModuleNotFoundError` for `ui.shared.speech_settings_frame`

- [ ] **Step 3: Implement a standalone speech settings frame**

```python
import wx

from ui.shared.speech_controls import SpeechControlsMixin


class SpeechSettingsFrame(wx.Frame, SpeechControlsMixin):
    def __init__(self, controller):
        super().__init__(parent=None, title="Speech Settings")
        self.controller = controller
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self._build_speech_controls(panel, sizer, wx)
        panel.SetSizer(sizer)
        self._bind_speech_control_events(wx)
        self._sync_speech_backend_choice()
        self._sync_speech_controls()
        self.Bind(wx.EVT_CLOSE, self._on_close)

    def _show_error(self, message: str, caption: str) -> None:
        wx.MessageBox(message, caption, wx.OK | wx.ICON_ERROR)

    def _on_close(self, event) -> None:
        self.Hide()
        if hasattr(event, "Veto"):
            event.Veto()
```

- [ ] **Step 4: Remove embedded speech controls from both main frames**

Delete these lines from both main-frame classes:

```python
self._build_speech_controls(panel, sizer, wx)
self._bind_speech_control_events(wx)
self._sync_speech_backend_choice()
self._sync_speech_controls()
```

Keep only app-specific controls in the main panel.

- [ ] **Step 5: Run focused tests**

Run:

```bash
pytest tests/unit/test_app_wx.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add \
  src/ui/shared/speech_settings_frame.py \
  src/ui/shared/speech_controls.py \
  src/ui/echo/main_frame.py \
  src/ui/nvda_remote/main_frame.py \
  tests/unit/test_app_wx.py
git commit -m "feat: move speech settings into shared panel"
```

## Task 4: Add Cross-Platform TrayIcon and ToolAppShell

**Files:**
- Create: `src/apps/shared/tray_icon.py`
- Create: `src/apps/shared/tool_app_shell.py`
- Create: `tests/unit/test_tray_icon.py`
- Create: `tests/unit/test_tool_app_shell.py`
- Modify: `src/ui/echo/app.py`
- Modify: `src/ui/nvda_remote/app.py`
- Modify: `tests/unit/test_app_wx.py`
- Test: `tests/unit/test_tray_icon.py`
- Test: `tests/unit/test_tool_app_shell.py`
- Test: `tests/unit/test_app_wx.py`

- [ ] **Step 1: Write failing tray icon tests**

```python
def test_tray_icon_builds_main_menu_items():
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
```

```python
def test_tool_app_shell_creates_hidden_main_and_speech_panels():
    from apps.shared.tool_app_shell import ToolAppShell

    shell = ToolAppShell(
        controller=FakeController(),
        main_frame_factory=lambda controller: FakeFrame(),
        speech_frame_factory=lambda controller: FakeFrame(),
    )

    shell.initialize()

    assert shell.panel_controller is not None
    assert shell.tray_icon is not None
```

- [ ] **Step 2: Run the new shell tests to verify they fail**

Run:

```bash
pytest tests/unit/test_tray_icon.py tests/unit/test_tool_app_shell.py -v
```

Expected: FAIL with missing modules and/or missing fake wx `adv` APIs

- [ ] **Step 3: Extend fake wx with `wx.adv.TaskBarIcon`, `Menu`, and `MenuItem`**

Add to `tests/unit/test_app_wx.py` fake wx installation:

```python
fake_adv = types.ModuleType("wx.adv")

class TaskBarIcon:
    def __init__(self, iconType=None):
        self.iconType = iconType
        self.destroyed = False

    def Destroy(self):
        self.destroyed = True

    def SetIcon(self, icon, tooltip=""):
        self.icon = icon
        self.tooltip = tooltip
        return True

fake_adv.TaskBarIcon = TaskBarIcon
monkeypatch.setitem(sys.modules, "wx.adv", fake_adv)
fake_wx.adv = fake_adv
```

- [ ] **Step 4: Implement `ToolTrayIcon` and `ToolAppShell`**

`src/apps/shared/tray_icon.py`:

```python
import wx
import wx.adv


class ToolTrayIcon(wx.adv.TaskBarIcon):
    def __init__(self, *, on_open_main, on_open_speech, on_exit):
        super().__init__()
        self._on_open_main = on_open_main
        self._on_open_speech = on_open_speech
        self._on_exit = on_exit

    def CreatePopupMenu(self):
        menu = wx.Menu()
        main_item = menu.Append(wx.ID_ANY, "Main Panel")
        speech_item = menu.Append(wx.ID_ANY, "Speech Settings")
        exit_item = menu.Append(wx.ID_EXIT, "Exit")
        menu.Bind(wx.EVT_MENU, lambda _event: self._on_open_main(), main_item)
        menu.Bind(wx.EVT_MENU, lambda _event: self._on_open_speech(), speech_item)
        menu.Bind(wx.EVT_MENU, lambda _event: self._on_exit(), exit_item)
        return menu
```

`src/apps/shared/tool_app_shell.py`:

```python
from apps.shared.panel_controller import PanelController
from apps.shared.tray_icon import ToolTrayIcon


class ToolAppShell:
    def __init__(self, *, controller, main_frame_factory, speech_frame_factory):
        self.controller = controller
        self.main_frame_factory = main_frame_factory
        self.speech_frame_factory = speech_frame_factory
        self.panel_controller = PanelController()
        self.tray_icon = None

    def initialize(self):
        main_frame = self.main_frame_factory(self.controller)
        speech_frame = self.speech_frame_factory(self.controller)
        self.panel_controller.register("main", main_frame)
        self.panel_controller.register("speech", speech_frame)
        self.tray_icon = ToolTrayIcon(
            on_open_main=lambda: self.panel_controller.show("main"),
            on_open_speech=lambda: self.panel_controller.show("speech"),
            on_exit=self.shutdown,
        )

    def shutdown(self):
        if self.tray_icon is not None:
            self.tray_icon.Destroy()
        if self.controller is not None and hasattr(self.controller, "shutdown"):
            self.controller.shutdown()
```

- [ ] **Step 5: Rewire both wx app entrypoints to use the shell**

Replace direct frame startup with shell initialization:

```python
from apps.shared.tool_app_shell import ToolAppShell
from ui.echo.main_frame import EchoMainFrame
from ui.shared.speech_settings_frame import SpeechSettingsFrame


def OnInit(self):
    self.shell = ToolAppShell(
        controller=self.controller,
        main_frame_factory=lambda controller: EchoMainFrame(controller=controller),
        speech_frame_factory=lambda controller: SpeechSettingsFrame(controller=controller),
    )
    self.shell.initialize()
    return True
```

Mirror the same shape for `src/ui/nvda_remote/app.py`.

- [ ] **Step 6: Run focused tests**

Run:

```bash
pytest tests/unit/test_tray_icon.py \
  tests/unit/test_tool_app_shell.py \
  tests/unit/test_app_wx.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add \
  src/apps/shared/tray_icon.py \
  src/apps/shared/tool_app_shell.py \
  src/ui/echo/app.py \
  src/ui/nvda_remote/app.py \
  tests/unit/test_tray_icon.py \
  tests/unit/test_tool_app_shell.py \
  tests/unit/test_app_wx.py
git commit -m "feat: add shared tray app shell"
```

## Task 5: Introduce Mode Types and ModeManager

**Files:**
- Create: `src/apps/shared/mode_types.py`
- Create: `src/apps/shared/mode_manager.py`
- Create: `tests/unit/test_mode_manager.py`
- Modify: `src/application/input/activation.py`
- Modify: `src/application/input/active_key_policy.py`
- Test: `tests/unit/test_mode_manager.py`
- Test: `tests/unit/test_input_activation.py`
- Test: `tests/unit/test_input_policies.py`

- [ ] **Step 1: Write failing mode-manager tests**

```python
from adapters.inputs.base import KeyEventDecision
from interop.key.key_event import KeyEvent

from apps.shared.mode_manager import ModeManager


class FakeMode:
    mode_id = "echo"
    enter_hotkey = "enter"
    exit_hotkey = 27

    def __init__(self):
        self.entered = 0
        self.exited = 0
        self.events = []

    def can_enter(self):
        return True

    def enter(self):
        self.entered += 1
        return True

    def exit(self):
        self.exited += 1
        return True

    def handle_key_event(self, event):
        self.events.append(event.vk)
        return KeyEventDecision.SUPPRESS


def test_mode_manager_enters_mode_on_hotkey():
    mode = FakeMode()
    manager = ModeManager(...)

    manager.register(mode)
    manager.activate_mode("echo")

    assert mode.entered == 1
    assert manager.active_mode_id == "echo"


def test_mode_manager_routes_non_exit_keys_to_active_mode():
    mode = FakeMode()
    manager = ModeManager(...)
    manager.register(mode)
    manager.activate_mode("echo")

    decision = manager.handle_key_event(KeyEvent(vk=65, scan_code=0, extended=False, pressed=True))

    assert decision == KeyEventDecision.SUPPRESS
    assert mode.events == [65]
```

- [ ] **Step 2: Run the new mode-manager tests to verify they fail**

Run: `pytest tests/unit/test_mode_manager.py -v`
Expected: FAIL with missing `ModeManager` and `ActivationMode`

- [ ] **Step 3: Define the mode protocol and minimal manager**

`src/apps/shared/mode_types.py`:

```python
from typing import Protocol

from adapters.inputs.base import KeyEventDecision
from interop.key.key_event import KeyEvent


class ActivationMode(Protocol):
    mode_id: str
    enter_hotkey: object
    exit_hotkey: int

    def can_enter(self) -> bool: ...
    def enter(self) -> bool: ...
    def exit(self) -> bool: ...
    def handle_key_event(self, event: KeyEvent) -> KeyEventDecision: ...
```

`src/apps/shared/mode_manager.py`:

```python
from adapters.inputs.base import KeyEventDecision


class ModeManager:
    def __init__(self, *, activation, notify_status):
        self._activation = activation
        self._notify_status = notify_status
        self._modes = {}
        self.active_mode_id = None

    def register(self, mode):
        self._modes[mode.mode_id] = mode

    def activate_mode(self, mode_id: str) -> bool:
        mode = self._modes[mode_id]
        if not mode.can_enter():
            return False
        if not self._activation.enter_active():
            return False
        if not mode.enter():
            self._activation.exit_active()
            return False
        self.active_mode_id = mode_id
        self._notify_status({"kind": "mode", "mode_id": mode_id, "state": "active"})
        return True

    def handle_key_event(self, event):
        if self.active_mode_id is None:
            return KeyEventDecision.PASS_THROUGH
        mode = self._modes[self.active_mode_id]
        if event.pressed and event.vk == mode.exit_hotkey:
            return self.exit_active_mode()
        return mode.handle_key_event(event)

    def exit_active_mode(self):
        mode = self._modes[self.active_mode_id]
        mode.exit()
        self._activation.exit_active()
        self._notify_status({"kind": "mode", "mode_id": mode.mode_id, "state": "idle"})
        self.active_mode_id = None
        return KeyEventDecision.SUPPRESS
```

- [ ] **Step 4: Update shared input helpers for mode-aware usage**

Keep `InputActivationUseCase` mostly intact, but make its API clean for `ModeManager` reuse.

If needed, refactor signatures toward:

```python
class InputActivationUseCase:
    def enter_active(self) -> bool: ...
    def exit_active(self) -> bool: ...
```

and update `ActiveKeyEventPolicy` toward:

```python
class ActiveKeyEventPolicy:
    def __init__(self, *, get_exit_vk, on_exit, on_key): ...
```

so the exit key can come from the current mode.

- [ ] **Step 5: Run focused tests**

Run:

```bash
pytest tests/unit/test_mode_manager.py \
  tests/unit/test_input_activation.py \
  tests/unit/test_input_policies.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add \
  src/apps/shared/mode_types.py \
  src/apps/shared/mode_manager.py \
  src/application/input/activation.py \
  src/application/input/active_key_policy.py \
  tests/unit/test_mode_manager.py
git commit -m "feat: add shared mode manager"
```

## Task 6: Migrate key_echo to ToolAppShell + ModeManager

**Files:**
- Modify: `src/apps/key_echo/facade.py`
- Modify: `src/ui/echo/app.py`
- Modify: `src/ui/echo/main_frame.py`
- Modify: `tests/unit/test_key_echo_app_service.py`
- Modify: `tests/unit/test_app_wx.py`
- Test: `tests/unit/test_key_echo_app_service.py`
- Test: `tests/unit/test_app_wx.py`

- [ ] **Step 1: Write failing `key_echo` mode tests**

```python
def test_key_echo_hotkey_activates_echo_mode():
    facade = build_key_echo_facade()

    facade.handle_idle_hotkey("enter")

    assert facade.is_echo_running() is True


def test_key_echo_escape_exits_echo_mode():
    facade = build_key_echo_facade()
    facade.start_echo()

    decision = facade.handle_key_event(KeyEvent(vk=27, scan_code=0, extended=False, pressed=True))

    assert decision.name == "SUPPRESS"
    assert facade.is_echo_running() is False
```

- [ ] **Step 2: Run the key echo tests to verify they fail**

Run:

```bash
pytest tests/unit/test_key_echo_app_service.py -v
```

Expected: FAIL because `key_echo` is still using direct activation wiring

- [ ] **Step 3: Define `echo_keys_mode` inside `KeyEchoAppFacade`**

Add a small app-specific mode object:

```python
class EchoKeysMode:
    mode_id = "echo_keys"
    enter_hotkey = "enter"
    exit_hotkey = 0x1B

    def __init__(self, control, echo_input):
        self._control = control
        self._echo_input = echo_input

    def can_enter(self) -> bool:
        return True

    def enter(self) -> bool:
        self._control.start_echo()
        return True

    def exit(self) -> bool:
        self._control.stop_echo()
        return True

    def handle_key_event(self, event):
        return self._echo_input.handle(event)
```

- [ ] **Step 4: Replace direct active-key wiring with `ModeManager`**

Inside `KeyEchoAppFacade.__init__()`:

```python
self._mode_manager = ModeManager(
    activation=self._activation,
    notify_status=self._notify_status_listener,
)
self._mode_manager.register(EchoKeysMode(self._echo_control, self._echo_input))
```

Update:

```python
def handle_key_event(self, event):
    return self._mode_manager.handle_key_event(event)
```

and route idle hotkey entry through `activate_mode("echo_keys")`.

- [ ] **Step 5: Run focused tests**

Run:

```bash
pytest tests/unit/test_key_echo_app_service.py tests/unit/test_app_wx.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add \
  src/apps/key_echo/facade.py \
  src/ui/echo/app.py \
  src/ui/echo/main_frame.py \
  tests/unit/test_key_echo_app_service.py \
  tests/unit/test_app_wx.py
git commit -m "feat: migrate key echo to shared mode platform"
```

## Task 7: Connect nvda_remote to ToolAppShell and ModeManager Lifecycle

**Files:**
- Modify: `src/apps/nvda_remote/facade.py`
- Modify: `src/ui/nvda_remote/app.py`
- Modify: `src/ui/nvda_remote/main_frame.py`
- Modify: `tests/unit/test_nvda_remote_app_service.py`
- Modify: `tests/unit/test_app_wx.py`
- Test: `tests/unit/test_nvda_remote_app_service.py`
- Test: `tests/unit/test_app_wx.py`

- [ ] **Step 1: Write failing `nvda_remote` mode-lifecycle tests**

```python
def test_f11_enters_remote_control_mode_through_mode_manager():
    facade = build_nvda_remote_facade(connected=True)

    facade.handle_idle_hotkey("f11")

    assert facade.state.control_state == "controlling"


def test_f11_exits_remote_control_mode_through_active_key_route():
    facade = build_nvda_remote_facade(connected=True)
    facade.start_control()

    decision = facade.handle_key_event(KeyEvent(vk=0x7A, scan_code=0, extended=False, pressed=True))

    assert decision.name == "SUPPRESS"
    assert facade.state.control_state == "connected"
```

- [ ] **Step 2: Run the `nvda_remote` tests to verify they fail**

Run:

```bash
pytest tests/unit/test_nvda_remote_app_service.py -v
```

Expected: FAIL because control-mode lifecycle is still facade-owned

- [ ] **Step 3: Define a remote-control mode that reuses existing app-specific logic**

Inside `src/apps/nvda_remote/facade.py`:

```python
class RemoteControlMode:
    mode_id = "remote_control"
    enter_hotkey = "f11"
    exit_hotkey = 0x7A

    def __init__(self, control_mode, input_forwarding):
        self._control_mode = control_mode
        self._input_forwarding = input_forwarding

    def can_enter(self) -> bool:
        return True

    def enter(self) -> bool:
        self._control_mode.start_control()
        return True

    def exit(self) -> bool:
        self._control_mode.stop_control()
        self._input_forwarding.clear()
        return True

    def handle_key_event(self, event):
        return self._input_forwarding.handle(event)
```

- [ ] **Step 4: Connect only the shared mode lifecycle, not remote session logic**

Wire `ModeManager` into `NvdaRemoteAppFacade` for:

- idle hotkey entry
- active key exit
- capture switching

Do **not** move these responsibilities out of the facade in this task:

- `RemoteSession`
- `MessageRouter`
- connection/disconnection orchestration
- clipboard transport behavior

- [ ] **Step 5: Run focused tests**

Run:

```bash
pytest tests/unit/test_nvda_remote_app_service.py tests/unit/test_app_wx.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add \
  src/apps/nvda_remote/facade.py \
  src/ui/nvda_remote/app.py \
  src/ui/nvda_remote/main_frame.py \
  tests/unit/test_nvda_remote_app_service.py \
  tests/unit/test_app_wx.py
git commit -m "feat: connect nvda remote to shared mode lifecycle"
```

## Task 8: Full Regression Pass and Cleanup

**Files:**
- Modify: `src/apps/key_echo/use_cases/speech_settings.py`
- Modify: `src/apps/nvda_remote/use_cases/speech_settings.py`
- Modify: `src/ui/shared/speech_controls.py`
- Modify: `tests/unit/test_app_wx.py`
- Modify: `docs/superpowers/specs/2026-06-12-tray-tool-app-platform-design.md`
- Modify: `docs/superpowers/specs/2026-06-12-tray-tool-app-platform-design_zh-TW.md`
- Test: `tests/unit`
- Test: `tests/integration`

- [ ] **Step 1: Remove or collapse compatibility shims only after all callers have moved**

If no imports remain, delete app-specific speech settings wrappers. If compatibility imports are still useful, keep them as one-line aliases:

```python
from apps.shared.speech_settings_controller import SpeechSettingsController as KeyEchoSpeechSettingsUseCase
```

and

```python
from apps.shared.speech_settings_controller import SpeechSettingsController as NvdaRemoteSpeechSettingsUseCase
```

- [ ] **Step 2: Run the full unit suite**

Run:

```bash
pytest tests/unit -v
```

Expected: PASS

- [ ] **Step 3: Run the integration suite**

Run:

```bash
pytest tests/integration -v
```

Expected: PASS

- [ ] **Step 4: Run a full combined regression command**

Run:

```bash
pytest tests/unit tests/integration -v
```

Expected: PASS

- [ ] **Step 5: Final cleanup commit**

```bash
git add src tests docs
git commit -m "refactor: complete tray tool app platform migration"
```

## Spec Coverage Check

- Shared speech settings controller: covered by Task 1.
- Shared hide-on-close panel lifecycle: covered by Task 2.
- Standalone speech settings panel: covered by Task 3.
- Resident cross-platform tray/status-icon shell: covered by Task 4.
- Shared mode model with per-mode enter/exit hotkeys: covered by Task 5.
- `key_echo` as first full mode-platform validation app: covered by Task 6.
- `nvda_remote` as second, more complex mode-lifecycle validation app: covered by Task 7.
- Two-app staged validation plus regression: covered by Task 8.

## Placeholder Scan

- No `TODO`, `TBD`, or deferred implementation markers are intentionally left in this plan.
- Each task names exact files and concrete test commands.
- Each implementation step includes concrete code to anchor the intended shape.

## Type Consistency Check

- Shared speech API names use `SpeechSettingsController` consistently.
- Mode abstraction names use `ActivationMode` and `ModeManager` consistently.
- Shared app shell names use `ToolAppShell`, `ToolTrayIcon`, and `PanelController` consistently.
- Existing lower-level input helpers remain named `InputActivationUseCase` and `ActiveKeyEventPolicy`.

Plan complete and saved to `docs/superpowers/plans/2026-06-12-tray-tool-app-platform-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
