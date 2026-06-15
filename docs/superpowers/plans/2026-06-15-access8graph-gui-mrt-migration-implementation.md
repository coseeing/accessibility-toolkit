# Access8Graph GUI MRT Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `key_echo`-style Access8Graph GUI app that selects a `.graphml` file and runs MRT navigation through this project's keyboard input pipeline and speech output.

**Architecture:** Migrate Access8Graph's pure GraphML/MRT parser and navigator into `apps.access8graph.graphml`, then adapt the MRT flow state machine to explicit output callbacks instead of NVDA runtime APIs. Wire the flow through an app service, HID key translator, wx main frame, shared tray shell, and shared speech settings.

**Tech Stack:** Python, wxPython, pytest, existing `KeyboardInputService`, `InputActivationUseCase`, `OutputCapabilities`, `SpeechSequence`, and `BreakCommand`.

---

## File Structure

Create these application files:

- `src/apps/access8graph/__init__.py`: package marker.
- `src/apps/access8graph/main.py`: runtime builder, matching `apps.key_echo.main`.
- `src/apps/access8graph/service.py`: app controller, selected file state, navigation lifecycle, keyboard pipeline handler, speech settings proxy.
- `src/apps/access8graph/input.py`: HID `KeyEvent` to Access8Graph command translator.
- `src/apps/access8graph/output.py`: `OutputCapabilities` adapter for flow speech and failure beep.
- `src/apps/access8graph/flow.py`: de-NVDA MRT flow and state machine adapted from Access8Graph `mrtView.py`.
- `src/apps/access8graph/graphml/__init__.py`: GraphML package exports.
- `src/apps/access8graph/graphml/model.py`: migrated `GraphML/model.py`.
- `src/apps/access8graph/graphml/mrt_model.py`: migrated `GraphML/mrtModel.py`.
- `src/apps/access8graph/graphml/mrt_navigator.py`: migrated `GraphML/mrtNavigator.py`.

Create these UI files:

- `src/ui/access8graph/__init__.py`: package marker.
- `src/ui/access8graph/app.py`: wx app shell, matching `ui.echo.app`.
- `src/ui/access8graph/main_frame.py`: `.graphml` picker, status label, start/stop button.

Create these tests:

- `tests/unit/test_access8graph_input.py`: HID translator coverage.
- `tests/unit/test_access8graph_output.py`: speech sequence and `BreakCommand` coverage.
- `tests/unit/test_access8graph_graphml.py`: pure parser/model import and fixture load coverage.
- `tests/unit/test_access8graph_flow.py`: portable flow startup and command dispatch coverage.
- `tests/unit/test_access8graph_app_service.py`: controller state, start/stop, pipeline result, error coverage.
- `tests/unit/test_access8graph_ui.py`: main frame UI state coverage.
- `tests/integration/test_access8graph_mrt_flow.py`: GraphML -> MrtModel -> navigators -> flow smoke coverage.

Do not import the root-level `Access8Graph/` source tree at runtime. It is only the migration source and fixture location.

## Task 1: Migrate Pure GraphML And MRT Core

**Files:**

- Create: `src/apps/access8graph/__init__.py`
- Create: `src/apps/access8graph/graphml/__init__.py`
- Create: `src/apps/access8graph/graphml/model.py`
- Create: `src/apps/access8graph/graphml/mrt_model.py`
- Create: `src/apps/access8graph/graphml/mrt_navigator.py`
- Test: `tests/unit/test_access8graph_graphml.py`

- [ ] **Step 1: Create failing tests for NVDA-free GraphML imports and fixture loading**

Create `tests/unit/test_access8graph_graphml.py`:

```python
from pathlib import Path

from apps.access8graph.graphml import (
    Graph,
    MrtDirectionNavigator,
    MrtModel,
    MrtUndirectionNavigator,
)


FIXTURE = Path("Access8Graph/addon/globalPlugins/Access8Graph/graph.graphml")


def test_access8graph_graphml_core_imports_without_nvda_modules() -> None:
    assert Graph is not None
    assert MrtModel is not None
    assert MrtDirectionNavigator is not None
    assert MrtUndirectionNavigator is not None


def test_access8graph_graphml_fixture_builds_mrt_model() -> None:
    graph = Graph(path=str(FIXTURE))
    model = MrtModel(graph)

    assert model.get_all_stations()
    assert model.get_all_lines()


def test_access8graph_navigators_expose_station_and_line_displays() -> None:
    graph = Graph(path=str(FIXTURE))
    model = MrtModel(graph)

    direction = MrtDirectionNavigator(model)
    undirection = MrtUndirectionNavigator(model)

    assert direction.stations_display
    assert direction.lines_display
    assert undirection.stations_display
    assert undirection.lines_display
```

- [ ] **Step 2: Run tests to verify they fail before migration**

Run:

```bash
pytest tests/unit/test_access8graph_graphml.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'apps.access8graph'`.

- [ ] **Step 3: Create package markers and copy source modules**

Create empty package files:

```python
# src/apps/access8graph/__init__.py
```

```python
# src/apps/access8graph/graphml/__init__.py
from apps.access8graph.graphml.model import Edge, Graph, Label, Node, Path
from apps.access8graph.graphml.mrt_model import MrtModel
from apps.access8graph.graphml.mrt_navigator import (
    MrtDirectionNavigator,
    MrtNavigator,
    MrtUndirectionNavigator,
)

__all__ = [
    "Edge",
    "Graph",
    "Label",
    "Node",
    "Path",
    "MrtDirectionNavigator",
    "MrtModel",
    "MrtNavigator",
    "MrtUndirectionNavigator",
]
```

Copy the source modules mechanically:

```bash
cp Access8Graph/addon/globalPlugins/Access8Graph/GraphML/model.py src/apps/access8graph/graphml/model.py
cp Access8Graph/addon/globalPlugins/Access8Graph/GraphML/mrtModel.py src/apps/access8graph/graphml/mrt_model.py
cp Access8Graph/addon/globalPlugins/Access8Graph/GraphML/mrtNavigator.py src/apps/access8graph/graphml/mrt_navigator.py
```

- [ ] **Step 4: Patch migrated imports and translation fallback**

In `src/apps/access8graph/graphml/mrt_model.py`, replace source-relative imports:

```python
from apps.access8graph.graphml.model import Path
```

In `src/apps/access8graph/graphml/mrt_navigator.py`, add this near the top if `_` is referenced:

```python
try:
    _
except NameError:
    _ = lambda message: message
```

Do not import `addonHandler`, `api`, `speech`, `tones`, `globalVars`, `NVDAObjects`, or `scriptHandler` in any file under `src/apps/access8graph/graphml`.

- [ ] **Step 5: Run graphml tests**

Run:

```bash
pytest tests/unit/test_access8graph_graphml.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit pure core migration**

Run:

```bash
git add src/apps/access8graph tests/unit/test_access8graph_graphml.py
git commit -m "feat: migrate access8graph graphml core"
```

## Task 2: Add HID Command Translator

**Files:**

- Create: `src/apps/access8graph/input.py`
- Test: `tests/unit/test_access8graph_input.py`

- [ ] **Step 1: Write failing translator tests**

Create `tests/unit/test_access8graph_input.py`:

```python
import pytest

from apps.access8graph.input import Access8GraphKeyTranslator
from interop.key import HID, KeyEvent


@pytest.mark.parametrize(
    ("usage", "command"),
    [
        (HID.UP, "up"),
        (HID.DOWN, "down"),
        (HID.LEFT, "left"),
        (HID.RIGHT, "right"),
        (HID.ENTER, "enter"),
        (HID.KEYPAD_ENTER, "enter"),
        (HID.ESCAPE, "escape"),
        (HID.HOME, "home"),
        (HID.END, "end"),
        (HID.D, "d"),
        (HID.U, "u"),
        (HID.P, "p"),
        (HID.Q, "q"),
        (HID.H, "h"),
        (HID.M, "m"),
        (HID.V, "v"),
        (HID.S, "s"),
        (HID.L, "l"),
        (HID.E, "e"),
    ],
)
def test_translator_maps_supported_key_down_events(usage: int, command: str) -> None:
    translator = Access8GraphKeyTranslator()

    result = translator.translate(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=usage, pressed=True)
    )

    assert result == {
        "key": command,
        "repeat": 0,
        "pressing": 0,
    }


def test_translator_ignores_key_up_events() -> None:
    translator = Access8GraphKeyTranslator()

    result = translator.translate(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.UP, pressed=False)
    )

    assert result is None


def test_translator_ignores_unsupported_keyboard_keys() -> None:
    translator = Access8GraphKeyTranslator()

    result = translator.translate(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    )

    assert result is None


def test_translator_ignores_non_keyboard_usage_page() -> None:
    translator = Access8GraphKeyTranslator()

    result = translator.translate(
        KeyEvent(usage_page=0x01, usage=HID.UP, pressed=True)
    )

    assert result is None
```

- [ ] **Step 2: Run translator tests to verify failure**

Run:

```bash
pytest tests/unit/test_access8graph_input.py -v
```

Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `apps.access8graph.input`.

- [ ] **Step 3: Implement translator**

Create `src/apps/access8graph/input.py`:

```python
from interop.key import HID
from interop.key.key_event import KeyEvent


class Access8GraphKeyTranslator:
    _COMMAND_BY_USAGE = {
        HID.UP: "up",
        HID.DOWN: "down",
        HID.LEFT: "left",
        HID.RIGHT: "right",
        HID.ENTER: "enter",
        HID.KEYPAD_ENTER: "enter",
        HID.ESCAPE: "escape",
        HID.HOME: "home",
        HID.END: "end",
        HID.D: "d",
        HID.U: "u",
        HID.P: "p",
        HID.Q: "q",
        HID.H: "h",
        HID.M: "m",
        HID.V: "v",
        HID.S: "s",
        HID.L: "l",
        HID.E: "e",
    }

    def translate(self, event: KeyEvent) -> dict[str, int | str] | None:
        if event.usage_page != HID.KEYBOARD_PAGE or not event.pressed:
            return None
        command = self._COMMAND_BY_USAGE.get(event.usage)
        if command is None:
            return None
        return {
            "key": command,
            "repeat": 0,
            "pressing": 0,
        }
```

- [ ] **Step 4: Run translator tests**

Run:

```bash
pytest tests/unit/test_access8graph_input.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit translator**

Run:

```bash
git add src/apps/access8graph/input.py tests/unit/test_access8graph_input.py
git commit -m "feat: add access8graph key translator"
```

## Task 3: Add Flow Output Adapter

**Files:**

- Create: `src/apps/access8graph/output.py`
- Test: `tests/unit/test_access8graph_output.py`

- [ ] **Step 1: Write failing output adapter tests**

Create `tests/unit/test_access8graph_output.py`:

```python
from application.output_capabilities import OutputCapabilities
from apps.access8graph.output import Access8GraphFlowOutput
from interop.speech.speech_commands import BreakCommand
from interop.speech.speech_sequence import SpeechSequence


class FakeSpeech:
    def __init__(self) -> None:
        self.calls = []

    def speak(self, sequence: SpeechSequence) -> None:
        self.calls.append(("speak", sequence))

    def cancel(self) -> None:
        self.calls.append(("cancel", None))

    def pause(self, is_paused: bool) -> None:
        self.calls.append(("pause", is_paused))

    def get_backend_options(self):
        return ()

    def get_selected_backend(self):
        return "default"

    def set_backend(self, backend_id):
        self.calls.append(("set_backend", backend_id))

    def list_voices(self):
        return ()

    def get_voice(self):
        return None

    def set_voice(self, voice_id):
        self.calls.append(("set_voice", voice_id))

    def get_rate(self):
        return None

    def set_rate(self, value):
        self.calls.append(("set_rate", value))

    def get_pitch(self):
        return None

    def set_pitch(self, value):
        self.calls.append(("set_pitch", value))

    def get_volume(self):
        return None

    def set_volume(self, value):
        self.calls.append(("set_volume", value))

    def shutdown(self):
        self.calls.append(("shutdown", None))


class FakeTone:
    def __init__(self) -> None:
        self.calls = []

    def beep(self, frequency: int, duration: int) -> None:
        self.calls.append((frequency, duration))


def test_output_speaks_non_empty_items_with_breaks_between_them() -> None:
    speech = FakeSpeech()
    output = Access8GraphFlowOutput(OutputCapabilities(speech=speech))

    output.speak(["", "功能選單開啟", "方向探索", "", "3 之 1"])

    assert speech.calls == [
        ("speak", SpeechSequence(items=(
            "功能選單開啟",
            BreakCommand(time=1),
            "方向探索",
            BreakCommand(time=1),
            "3 之 1",
        ))),
    ]


def test_output_does_not_speak_when_all_items_are_empty() -> None:
    speech = FakeSpeech()
    output = Access8GraphFlowOutput(OutputCapabilities(speech=speech))

    output.speak(["", None, ""])

    assert speech.calls == []


def test_output_cancels_speech() -> None:
    speech = FakeSpeech()
    output = Access8GraphFlowOutput(OutputCapabilities(speech=speech))

    output.cancel_speech()

    assert speech.calls == [("cancel", None)]


def test_output_beep_failure_uses_tone_when_available() -> None:
    speech = FakeSpeech()
    tone = FakeTone()
    output = Access8GraphFlowOutput(OutputCapabilities(speech=speech, tone=tone))

    output.beep_failure()

    assert tone.calls == [(100, 100)]


def test_output_beep_failure_is_noop_without_tone() -> None:
    speech = FakeSpeech()
    output = Access8GraphFlowOutput(OutputCapabilities(speech=speech))

    output.beep_failure()

    assert speech.calls == []
```

- [ ] **Step 2: Run output tests to verify failure**

Run:

```bash
pytest tests/unit/test_access8graph_output.py -v
```

Expected: FAIL because `apps.access8graph.output` does not exist.

- [ ] **Step 3: Implement output adapter**

Create `src/apps/access8graph/output.py`:

```python
from collections.abc import Iterable
from typing import Protocol

from application.output_capabilities import OutputCapabilities
from interop.speech.speech_commands import BreakCommand
from interop.speech.speech_sequence import SpeechSequence


class FlowOutput(Protocol):
    def cancel_speech(self) -> None: ...
    def speak(self, items: Iterable[object]) -> None: ...
    def beep_failure(self) -> None: ...


class Access8GraphFlowOutput:
    def __init__(self, outputs: OutputCapabilities) -> None:
        self._outputs = outputs

    def cancel_speech(self) -> None:
        self._outputs.speech.cancel()

    def speak(self, items: Iterable[object]) -> None:
        filtered = tuple(str(item) for item in items if item)
        if not filtered:
            return
        sequence_items: list[object] = []
        for index, item in enumerate(filtered):
            if index > 0:
                sequence_items.append(BreakCommand(time=1))
            sequence_items.append(item)
        self._outputs.speech.speak(SpeechSequence(items=tuple(sequence_items)))

    def beep_failure(self) -> None:
        tone = self._outputs.tone
        if tone is None:
            return
        beep = getattr(tone, "beep", None)
        if callable(beep):
            beep(100, 100)
```

- [ ] **Step 4: Run output tests**

Run:

```bash
pytest tests/unit/test_access8graph_output.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit output adapter**

Run:

```bash
git add src/apps/access8graph/output.py tests/unit/test_access8graph_output.py
git commit -m "feat: add access8graph flow output adapter"
```

## Task 4: Port MRT Flow State Machine

**Files:**

- Create: `src/apps/access8graph/flow.py`
- Test: `tests/unit/test_access8graph_flow.py`

- [ ] **Step 1: Write failing flow tests**

Create `tests/unit/test_access8graph_flow.py`:

```python
from apps.access8graph.flow import MrtFlow


class FakeOutput:
    def __init__(self) -> None:
        self.calls = []

    def cancel_speech(self) -> None:
        self.calls.append(("cancel", None))

    def speak(self, items) -> None:
        self.calls.append(("speak", tuple(items)))

    def beep_failure(self) -> None:
        self.calls.append(("beep", None))


class FakeDirectionNavigator:
    def __init__(self) -> None:
        self.line = None
        self.station = None
        self.source = None
        self.destination = None
        self.current = None
        self.run = False
        self.lines_display = [
            {"id": "blue", "label": "板南線"},
            {"id": "red", "label": "淡水信義線"},
        ]
        self.stations_display = [
            {"id": "taipei", "label": "台北車站"},
            {"id": "ximen", "label": "西門"},
        ]
        self.end_points = [{"id": "nangang", "label": "南港展覽館"}]
        self.transfer_display = []
        self.current_display = {"id": "taipei", "label": "台北車站"}
        self.forward = []
        self.reverse = []


class FakeUndirectionNavigator:
    def __init__(self) -> None:
        self.line = None
        self.station = None
        self.current = None
        self.sub_line = None
        self.lines_display = [{"id": "blue", "label": "板南線"}]
        self.stations_display = [{"id": "taipei", "label": "台北車站"}]
        self.sub_lines_display = [{"id": ("taipei", "ximen"), "label": "台北車站往西門"}]
        self.transfer_display = []
        self.current_display = {"id": "taipei", "label": "台北車站"}
        self.previous = None
        self.next = None


def test_flow_startup_speaks_mode_menu() -> None:
    output = FakeOutput()

    MrtFlow(
        navigator={
            "direction": FakeDirectionNavigator(),
            "undirection": FakeUndirectionNavigator(),
        },
        output=output,
    )

    assert output.calls[0] == ("cancel", None)
    assert output.calls[1][0] == "speak"
    assert "功能選單開啟" in output.calls[1][1]
    assert "方向探索" in output.calls[1][1]


def test_flow_down_moves_mode_menu_selection() -> None:
    output = FakeOutput()
    flow = MrtFlow(
        navigator={
            "direction": FakeDirectionNavigator(),
            "undirection": FakeUndirectionNavigator(),
        },
        output=output,
    )
    output.calls.clear()

    assert flow.enter({"key": "down", "repeat": 0, "pressing": 0}) is True

    assert output.calls[0] == ("cancel", None)
    assert output.calls[1][0] == "speak"
    assert "線性探索" in output.calls[1][1]


def test_flow_unsupported_command_beeps_and_returns_false() -> None:
    output = FakeOutput()
    flow = MrtFlow(
        navigator={
            "direction": FakeDirectionNavigator(),
            "undirection": FakeUndirectionNavigator(),
        },
        output=output,
    )
    output.calls.clear()

    assert flow.enter({"key": "unknown", "repeat": 0, "pressing": 0}) is False

    assert ("beep", None) in output.calls
```

- [ ] **Step 2: Run flow tests to verify failure**

Run:

```bash
pytest tests/unit/test_access8graph_flow.py -v
```

Expected: FAIL because `apps.access8graph.flow` does not exist.

- [ ] **Step 3: Create portable flow module from `mrtView.py`**

Create `src/apps/access8graph/flow.py` by copying the relevant non-NVDA pieces from `Access8Graph/addon/globalPlugins/Access8Graph/GraphML/mrtView.py`:

- Keep `MrtFlow`, `State`, `ListState`, `HelpState`, all MRT state classes, `ListView`, and `RunView`.
- Remove imports of `addonHandler`, `api`, `eventHandler`, `NVDAObjects.window`, `scriptHandler`, `textInfos`, `tones`, `speech`, `BreakCommand` from NVDA, and `globalVars`.
- Add this module-level translation fallback:

```python
try:
    _
except NameError:
    _ = lambda message: message
```

- Change `MrtFlow.__init__` signature to:

```python
class MrtFlow:
    def __init__(self, navigator, output):
        self.pass_key = [f"numpad{i}" for i in range(1, 10)]
        self.navigator = navigator
        self.output = output
        self.message = []
        self.states = {
            "mode": ModeState(self),
            "stations": StationsState(self),
            "lines": LinesState(self),
            "direction_end_point": DirectionEndPointState(self),
            "direction_run": DirectionRunState(self),
            "undirection_run": UndirectionRunState(self),
            "plan_run": PlanRunState(self),
            "direction_transfer": DirectionTransferState(self),
            "undirection_transfer": UndirectionTransferState(self),
            "explore_neighbor": ExploreNeighborState(self),
            "explore_sub_line": ExploreSubLineState(self),
            "direction_stations": DirectionStationsState(self),
            "direction_lines": DirectionLinesState(self),
            "source_stations": SourceStationsState(self),
            "source_lines": SourceLinesState(self),
            "destination_stations": DestinationStationsState(self),
            "destination_lines": DestinationLinesState(self),
            "undirection_stations": UndirectionStationsState(self),
            "undirection_lines": UndirectionLinesState(self),
            "undirection_sub_lines": UndirectionSubLinesState(self),
        }
        self.background_state = None
        self._state = self.states["mode"]
        self._state.active = True
        self.state = self.states["mode"]
        self._speak_current_view()
```

- Replace NVDA speech block with:

```python
    def _collect_speech_items(self):
        speech_items = []
        speech_items.extend(self.message)
        self.message = []
        if self.state.hint and self.state.view.hint:
            speech_items.append(self.state.view.hint)
            self.state.hint = False
        speech_items.extend(self.state.view.display)
        return [item for item in speech_items if item]

    def _speak_current_view(self) -> None:
        speech_items = self._collect_speech_items()
        self.output.cancel_speech()
        self.output.speak(speech_items)
```

- Replace `MrtFlow.enter` with:

```python
    def enter(self, command):
        key = command["key"]
        result = True
        if key == "enter":
            self.state.onok()
        else:
            try:
                result = getattr(self.state, key)()
            except AttributeError:
                result = False

        if not result:
            self.output.beep_failure()

        self._speak_current_view()
        return bool(result)
```

- Remove `event_gainFocus`, `event_loseFocus`, `setFocus`, `exit`, `makeTextInfo`, `syncTextInfoPosition`, and `GraphViewTextInfo`.

- [ ] **Step 4: Run flow tests**

Run:

```bash
pytest tests/unit/test_access8graph_flow.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit flow port**

Run:

```bash
git add src/apps/access8graph/flow.py tests/unit/test_access8graph_flow.py
git commit -m "feat: port access8graph mrt flow"
```

## Task 5: Add Access8Graph App Service

**Files:**

- Create: `src/apps/access8graph/service.py`
- Test: `tests/unit/test_access8graph_app_service.py`

- [ ] **Step 1: Write failing service tests**

Create `tests/unit/test_access8graph_app_service.py`:

```python
from pathlib import Path

import pytest

from adapters.inputs.captured_event import CapturedKeyEvent
from application.input.results import AppKeyEventResult, KeyboardPipelineResult
from application.keyboard import KeyboardInputService
from application.output_capabilities import OutputCapabilities
from apps.access8graph.service import Access8GraphAppService
from interop.key import HID, KeyEvent
from interop.speech.speech_sequence import SpeechSequence


FIXTURE = Path("Access8Graph/addon/globalPlugins/Access8Graph/graph.graphml")


class FakeSpeech:
    def __init__(self) -> None:
        self.calls = []
        self.backend_id = "default"

    def speak(self, sequence: SpeechSequence) -> None:
        self.calls.append(("speak", sequence))

    def cancel(self) -> None:
        self.calls.append(("cancel", None))

    def pause(self, is_paused: bool) -> None:
        self.calls.append(("pause", is_paused))

    def get_backend_options(self):
        return (("default", "Default"),)

    def get_selected_backend(self):
        return self.backend_id

    def set_backend(self, backend_id):
        self.backend_id = backend_id

    def list_voices(self):
        return ()

    def get_voice(self):
        return None

    def set_voice(self, voice_id):
        self.calls.append(("set_voice", voice_id))

    def get_rate(self):
        return None

    def set_rate(self, value):
        self.calls.append(("set_rate", value))

    def get_pitch(self):
        return None

    def set_pitch(self, value):
        self.calls.append(("set_pitch", value))

    def get_volume(self):
        return None

    def set_volume(self, value):
        self.calls.append(("set_volume", value))

    def shutdown(self):
        self.calls.append(("shutdown", None))


class FakeCapture:
    def __init__(self) -> None:
        self.listener = None
        self.start_calls = 0
        self.stop_calls = 0

    @property
    def running(self) -> bool:
        return self.start_calls > self.stop_calls

    def set_listener(self, listener) -> None:
        self.listener = listener

    def start(self) -> None:
        self.start_calls += 1

    def stop(self) -> None:
        self.stop_calls += 1


class FakeHotkeyCapture(FakeCapture):
    def set_handler(self, handler) -> None:
        self.handler = handler


def build_service():
    input_capture = FakeCapture()
    hotkey_capture = FakeHotkeyCapture()
    speech = FakeSpeech()
    service = Access8GraphAppService(
        hotkey_capture=hotkey_capture,
        input_capture=input_capture,
        outputs=OutputCapabilities(speech=speech),
    )
    input_service = KeyboardInputService(input_capture, service)
    service.attach_input_service(input_service)
    service.bind()
    return service, input_capture, hotkey_capture, speech


def test_service_cannot_start_without_selected_graphml() -> None:
    service, input_capture, _hotkey_capture, _speech = build_service()

    with pytest.raises(RuntimeError, match="No GraphML file selected"):
        service.start_navigation()

    assert service.is_navigation_running() is False
    assert input_capture.running is False


def test_service_rejects_non_graphml_path(tmp_path: Path) -> None:
    service, _input_capture, _hotkey_capture, _speech = build_service()
    path = tmp_path / "graph.txt"
    path.write_text("<graphml />", encoding="utf-8")

    with pytest.raises(ValueError, match="\\.graphml"):
        service.choose_graphml(str(path))


def test_service_starts_and_stops_navigation() -> None:
    service, input_capture, _hotkey_capture, speech = build_service()

    service.choose_graphml(str(FIXTURE))
    service.start_navigation()

    assert service.is_navigation_running() is True
    assert input_capture.running is True
    assert any(call[0] == "speak" for call in speech.calls)

    service.stop_navigation()

    assert service.is_navigation_running() is False
    assert input_capture.running is False


def test_service_handles_key_event_while_navigation_running() -> None:
    service, _input_capture, _hotkey_capture, _speech = build_service()
    service.choose_graphml(str(FIXTURE))
    service.start_navigation()

    result = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(
                usage_page=HID.KEYBOARD_PAGE,
                usage=HID.DOWN,
                pressed=True,
            )
        )
    )

    assert result == KeyboardPipelineResult(
        send_to_system=False,
        app_result=AppKeyEventResult.HANDLED_STOP,
    )


def test_service_escape_stops_navigation() -> None:
    service, _input_capture, _hotkey_capture, _speech = build_service()
    service.choose_graphml(str(FIXTURE))
    service.start_navigation()

    result = service.handle_key_event(
        CapturedKeyEvent(
            key_event=KeyEvent(
                usage_page=HID.KEYBOARD_PAGE,
                usage=HID.ESCAPE,
                pressed=True,
            )
        )
    )

    assert result == KeyboardPipelineResult(
        send_to_system=False,
        app_result=AppKeyEventResult.HANDLED_STOP,
    )
    assert service.is_navigation_running() is False
```

- [ ] **Step 2: Run service tests to verify failure**

Run:

```bash
pytest tests/unit/test_access8graph_app_service.py -v
```

Expected: FAIL because `apps.access8graph.service` does not exist.

- [ ] **Step 3: Implement app service**

Create `src/apps/access8graph/service.py`:

```python
from pathlib import Path
from typing import Any

from adapters.inputs.base import HotkeyCapture, InputCapture
from adapters.inputs.captured_event import CapturedKeyEvent
from application.input import InputActivationUseCase, assemble_pipeline_result
from application.input.results import AppKeyEventResult, KeyboardPipelineResult
from application.keyboard import KeyEventHandler, KeyboardInputService
from application.output_capabilities import OutputCapabilities
from apps.access8graph.flow import MrtFlow
from apps.access8graph.graphml import (
    Graph,
    MrtDirectionNavigator,
    MrtModel,
    MrtUndirectionNavigator,
)
from apps.access8graph.input import Access8GraphKeyTranslator
from apps.access8graph.output import Access8GraphFlowOutput
from apps.shared.speech_settings_controller import SpeechSettingsController
from interop.key import HID


class Access8GraphAppService(KeyEventHandler):
    enter_usage = HID.F10

    def __init__(
        self,
        *,
        hotkey_capture: HotkeyCapture,
        input_capture: InputCapture,
        outputs: OutputCapabilities,
        main_thread_dispatch=None,
    ) -> None:
        self.hotkey_capture = hotkey_capture
        self.input_capture = input_capture
        self._outputs = outputs
        self._input_service: KeyboardInputService | None = None
        self._status_listener = None
        self._selected_graphml_path: Path | None = None
        self._flow: MrtFlow | None = None
        self._navigation_running = False
        self._translator = Access8GraphKeyTranslator()
        self._main_thread_dispatch = main_thread_dispatch or (lambda callback: callback())
        self._speech_settings = SpeechSettingsController(speech=outputs.speech)
        self._activation = InputActivationUseCase(
            input_capture=input_capture,
            hotkey_capture=hotkey_capture,
            is_active=self.is_navigation_running,
            set_active=self._set_navigation_active,
            notify_error=lambda message: self._notify_status_listener(
                {"kind": "error", "message": message}
            ),
        )

    def attach_input_service(self, input_service: KeyboardInputService) -> None:
        self._input_service = input_service

    def bind(self) -> None:
        self.input_capture.set_listener(self.handle_key_event)
        self.hotkey_capture.set_handler(self._handle_idle_hotkey)

    def set_status_listener(self, listener) -> None:
        self._status_listener = listener

    def choose_graphml(self, path: str) -> None:
        graphml_path = Path(path)
        if graphml_path.suffix.lower() != ".graphml":
            raise ValueError("Selected file must have a .graphml extension")
        if not graphml_path.exists():
            raise FileNotFoundError(str(graphml_path))
        self._selected_graphml_path = graphml_path
        self._notify_status_listener(
            {"kind": "graphml", "path": str(graphml_path)}
        )

    def get_selected_graphml_path(self) -> str | None:
        if self._selected_graphml_path is None:
            return None
        return str(self._selected_graphml_path)

    def start_navigation(self) -> None:
        if self._selected_graphml_path is None:
            raise RuntimeError("No GraphML file selected")
        if self._input_service is None:
            raise RuntimeError("Keyboard input service is not attached")
        graph = Graph(path=str(self._selected_graphml_path))
        model = MrtModel(graph)
        if not self._activation.enter_active():
            raise RuntimeError("Failed to start keyboard capture")
        try:
            self._flow = MrtFlow(
                navigator={
                    "direction": MrtDirectionNavigator(model),
                    "undirection": MrtUndirectionNavigator(model),
                },
                output=Access8GraphFlowOutput(self._outputs),
            )
        except Exception:
            self._activation.exit_active()
            self._flow = None
            raise
        self._notify_status_listener({"kind": "navigation", "state": "running"})

    def stop_navigation(self) -> None:
        if not self._navigation_running:
            self._flow = None
            return
        self._activation.exit_active()
        self._flow = None
        self._notify_status_listener({"kind": "navigation", "state": "stopped"})

    def _set_navigation_active(self, active: bool) -> None:
        self._navigation_running = active

    def is_navigation_running(self) -> bool:
        return self._navigation_running

    def handle_key_event(self, event: CapturedKeyEvent) -> KeyboardPipelineResult:
        app_result = AppKeyEventResult.UNHANDLED
        if self._flow is not None and self._navigation_running:
            command = self._translator.translate(event.key_event)
            if command and command["key"] == "escape":
                self.stop_navigation()
            elif command is not None:
                self._flow.enter(command)
            app_result = AppKeyEventResult.HANDLED_STOP
        return assemble_pipeline_result(
            send_to_system=False,
            app_result=app_result,
        )

    def get_speech_backend_options(self) -> tuple[tuple[str, str], ...]:
        return self._speech_settings.get_backend_options()

    def get_selected_speech_backend(self) -> str:
        return self._speech_settings.get_selected_backend()

    def set_speech_backend(self, backend_id: str) -> None:
        self._speech_settings.set_backend(backend_id)
        self._notify_status_listener(
            {"kind": "speech_backend", "backend_id": backend_id}
        )

    def get_available_voices(self) -> tuple[tuple[str, str], ...]:
        return self._speech_settings.list_voices()

    def get_selected_voice(self) -> str | None:
        return self._speech_settings.get_voice()

    def set_selected_voice(self, voice_id: str) -> None:
        self._speech_settings.set_voice(voice_id)

    def get_rate(self) -> int | None:
        return self._speech_settings.get_rate()

    def set_rate(self, value: int) -> None:
        self._speech_settings.set_rate(value)

    def get_pitch(self) -> int | None:
        return self._speech_settings.get_pitch()

    def set_pitch(self, value: int) -> None:
        self._speech_settings.set_pitch(value)

    def get_volume(self) -> int | None:
        return self._speech_settings.get_volume()

    def set_volume(self, value: int) -> None:
        self._speech_settings.set_volume(value)

    def shutdown(self) -> None:
        self.stop_navigation()
        if self._input_service is not None and self._input_service.running:
            self._input_service.stop()
        if self.hotkey_capture is not None and self.hotkey_capture.running:
            self.hotkey_capture.stop()
        self._outputs.speech.shutdown()

    def _notify_status_listener(self, status: dict[str, Any]) -> None:
        if self._status_listener is not None:
            self._status_listener(status)

    def _handle_idle_hotkey(self) -> None:
        if self.is_navigation_running():
            return
        self._main_thread_dispatch(self.start_navigation)
```

- [ ] **Step 4: Run service tests**

Run:

```bash
pytest tests/unit/test_access8graph_app_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit service**

Run:

```bash
git add src/apps/access8graph/service.py tests/unit/test_access8graph_app_service.py
git commit -m "feat: add access8graph app service"
```

## Task 6: Add GUI And Runtime

**Files:**

- Create: `src/apps/access8graph/main.py`
- Create: `src/ui/access8graph/__init__.py`
- Create: `src/ui/access8graph/app.py`
- Create: `src/ui/access8graph/main_frame.py`
- Test: `tests/unit/test_access8graph_ui.py`

- [ ] **Step 1: Write failing UI tests**

Create `tests/unit/test_access8graph_ui.py`:

```python
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

    def set_status_listener(self, listener) -> None:
        self.listener = listener

    def choose_graphml(self, path: str) -> None:
        self.selected_path = path

    def get_selected_graphml_path(self) -> str | None:
        return self.selected_path

    def start_navigation(self) -> None:
        self.start_calls += 1
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
```

- [ ] **Step 2: Run UI tests to verify failure**

Run:

```bash
pytest tests/unit/test_access8graph_ui.py -v
```

Expected: FAIL because `ui.access8graph` does not exist.

- [ ] **Step 3: Implement Access8Graph wx app**

Create `src/ui/access8graph/__init__.py`:

```python
# Package marker for Access8Graph wx UI.
```

Create `src/ui/access8graph/app.py`:

```python
import wx

from apps.shared.tool_app_shell import ToolAppShell
from ui.access8graph.main_frame import Access8GraphMainFrame
from ui.shared.speech_settings_frame import SpeechSettingsFrame


class Access8GraphApp(wx.App):
    dispatch = staticmethod(wx.CallAfter)

    def __init__(self, controller):
        self.controller = controller
        super().__init__(False)

    def OnInit(self):
        self.shell = ToolAppShell(
            controller=self.controller,
            main_frame_factory=lambda ctrl: Access8GraphMainFrame(controller=ctrl),
            speech_frame_factory=lambda ctrl: SpeechSettingsFrame(controller=ctrl),
            app_name="Access8Graph",
        )
        self.shell.initialize()
        return True

    def OnExit(self):
        return 0
```

- [ ] **Step 4: Implement main frame**

Create `src/ui/access8graph/main_frame.py`:

```python
from pathlib import Path

import wx


class Access8GraphMainFrame(wx.Frame):
    def __init__(self, controller):
        super().__init__(parent=None, title="Access8Graph")
        self.controller = controller
        if self.controller is not None and hasattr(self.controller, "set_status_listener"):
            self.controller.set_status_listener(self._on_controller_status)

        self.Bind(wx.EVT_CLOSE, self._on_close)

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.status_label = wx.StaticText(panel, label="No file selected")
        self.choose_button = wx.Button(panel, label="Choose GraphML...")
        self.navigation_button = wx.Button(panel, label="Start Navigation")

        sizer.Add(self.status_label, 0, wx.EXPAND | wx.ALL, 4)
        sizer.Add(self.choose_button, 0, wx.EXPAND | wx.ALL, 4)
        sizer.Add(self.navigation_button, 0, wx.EXPAND | wx.ALL, 4)
        panel.SetSizer(sizer)

        self.choose_button.Bind(wx.EVT_BUTTON, self._on_choose_graphml)
        self.navigation_button.Bind(wx.EVT_BUTTON, self._on_toggle_navigation)
        self._sync_controls()

    def _show_error(self, message: str, caption: str) -> None:
        wx.MessageBox(message, caption, wx.OK | wx.ICON_ERROR)

    def _on_choose_graphml(self, _event) -> None:
        if self.controller is None:
            return
        with wx.FileDialog(
            self,
            "Choose GraphML file",
            wildcard="GraphML files (*.graphml)|*.graphml",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            try:
                self.controller.choose_graphml(dialog.GetPath())
            except Exception as error:
                self._show_error(str(error), "GraphML Error")
        self._sync_controls()

    def _on_toggle_navigation(self, _event) -> None:
        if self.controller is None:
            return
        if self._is_navigation_running():
            self.controller.stop_navigation()
        else:
            try:
                self.controller.start_navigation()
            except Exception as error:
                self._show_error(str(error), "Input Error")
        self._sync_controls()

    def _is_navigation_running(self) -> bool:
        if self.controller is None or not hasattr(self.controller, "is_navigation_running"):
            return False
        return bool(self.controller.is_navigation_running())

    def _selected_path(self) -> str | None:
        if self.controller is None or not hasattr(self.controller, "get_selected_graphml_path"):
            return None
        return self.controller.get_selected_graphml_path()

    def _sync_controls(self) -> None:
        running = self._is_navigation_running()
        selected_path = self._selected_path()
        self.navigation_button.SetLabel(
            "Stop Navigation" if running else "Start Navigation"
        )
        self.navigation_button.Enable(bool(selected_path) or running)
        if running:
            self.status_label.SetLabel("Navigation running")
        elif selected_path:
            self.status_label.SetLabel(Path(selected_path).name)
        else:
            self.status_label.SetLabel("No file selected")

    def _on_controller_status(self, status) -> None:
        if isinstance(status, dict) and status.get("kind") == "error":
            self.status_label.SetLabel(str(status.get("message", "")))
        self._sync_controls()

    def _on_close(self, event) -> None:
        self.Hide()
        if hasattr(event, "Veto"):
            event.Veto()
```

- [ ] **Step 5: Implement runtime builder**

Create `src/apps/access8graph/main.py`:

```python
from dataclasses import dataclass
import logging
from typing import Any

from adapters.inputs.base import HotkeyCapture, InputCapture
from application.keyboard import KeyboardInputService
from application.output_capabilities import OutputCapabilities
from application.output_scheduler import OutputScheduler
from application.output_service import QueuedOutputService
from application.speech_service import SpeechService
from apps.access8graph.service import Access8GraphAppService
from bootstrap.platform import (
    create_hotkey_capture,
    create_input_capture,
    default_speech_backend_id,
    default_speech_backend_options,
)
from bootstrap.runtime import configure_logging


@dataclass(frozen=True)
class Access8GraphRuntime:
    input_capture: InputCapture
    hotkey_capture: HotkeyCapture
    speech_scheduler: OutputScheduler
    speech_service: SpeechService
    output_service: QueuedOutputService
    input_service: KeyboardInputService
    app_service: Access8GraphAppService
    app: Any


def build_runtime() -> Access8GraphRuntime:
    from ui.access8graph.app import Access8GraphApp

    input_capture = create_input_capture()
    hotkey_capture = create_hotkey_capture(Access8GraphAppService.enter_usage)
    speech_scheduler = OutputScheduler()
    speech_service = SpeechService(
        backend_options=default_speech_backend_options(speech_scheduler),
        selected_backend_id=default_speech_backend_id(),
        scheduler=speech_scheduler,
    )
    output_service = QueuedOutputService(speech=speech_service)
    app_service = Access8GraphAppService(
        hotkey_capture=hotkey_capture,
        input_capture=input_capture,
        outputs=OutputCapabilities(speech=output_service),
        main_thread_dispatch=getattr(Access8GraphApp, "dispatch", None),
    )
    input_service = KeyboardInputService(input_capture, app_service)
    app_service.attach_input_service(input_service)
    app_service.bind()
    hotkey_capture.start()
    app = Access8GraphApp(controller=app_service)
    return Access8GraphRuntime(
        input_capture=input_capture,
        hotkey_capture=hotkey_capture,
        speech_scheduler=speech_scheduler,
        speech_service=speech_service,
        output_service=output_service,
        input_service=input_service,
        app_service=app_service,
        app=app,
    )


def main() -> int:
    try:
        configure_logging(app_name="access8graph")
    except OSError:
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            )
        logging.getLogger(__name__).warning(
            "Logging initialization failed; continuing without file logging",
            exc_info=True,
        )
    runtime = build_runtime()
    return runtime.app.MainLoop()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run UI tests**

Run:

```bash
pytest tests/unit/test_access8graph_ui.py -v
```

Expected: PASS. The test installs a fake `wx` module, so it should not depend on a desktop display.

- [ ] **Step 7: Commit GUI and runtime**

Run:

```bash
git add src/apps/access8graph/main.py src/ui/access8graph tests/unit/test_access8graph_ui.py
git commit -m "feat: add access8graph gui runtime"
```

## Task 7: Add End-To-End MRT Flow Smoke Test

**Files:**

- Create: `tests/integration/test_access8graph_mrt_flow.py`

- [ ] **Step 1: Write integration smoke test**

Create `tests/integration/test_access8graph_mrt_flow.py`:

```python
from pathlib import Path

from apps.access8graph.flow import MrtFlow
from apps.access8graph.graphml import (
    Graph,
    MrtDirectionNavigator,
    MrtModel,
    MrtUndirectionNavigator,
)


FIXTURE = Path("Access8Graph/addon/globalPlugins/Access8Graph/graph.graphml")


class FakeOutput:
    def __init__(self) -> None:
        self.calls = []

    def cancel_speech(self) -> None:
        self.calls.append(("cancel", None))

    def speak(self, items) -> None:
        self.calls.append(("speak", tuple(items)))

    def beep_failure(self) -> None:
        self.calls.append(("beep", None))


def test_access8graph_mrt_flow_starts_from_fixture_and_accepts_menu_navigation() -> None:
    graph = Graph(path=str(FIXTURE))
    model = MrtModel(graph)
    output = FakeOutput()

    flow = MrtFlow(
        navigator={
            "direction": MrtDirectionNavigator(model),
            "undirection": MrtUndirectionNavigator(model),
        },
        output=output,
    )

    assert output.calls[0] == ("cancel", None)
    assert output.calls[1][0] == "speak"
    assert "方向探索" in output.calls[1][1]

    output.calls.clear()
    assert flow.enter({"key": "down", "repeat": 0, "pressing": 0}) is True

    assert output.calls[0] == ("cancel", None)
    assert output.calls[1][0] == "speak"
    assert "線性探索" in output.calls[1][1]
```

- [ ] **Step 2: Run integration smoke test**

Run:

```bash
pytest tests/integration/test_access8graph_mrt_flow.py -v
```

Expected: PASS.

- [ ] **Step 3: Run all Access8Graph tests**

Run:

```bash
pytest tests/unit/test_access8graph_*.py tests/integration/test_access8graph_mrt_flow.py -v
```

Expected: PASS, with UI tests skipped only if wx is unavailable.

- [ ] **Step 4: Commit integration coverage**

Run:

```bash
git add tests/integration/test_access8graph_mrt_flow.py
git commit -m "test: cover access8graph mrt flow smoke path"
```

## Task 8: Final Verification And Manual Launch Check

**Files:**

- Modify only if verification exposes defects in files from earlier tasks.

- [ ] **Step 1: Run focused Access8Graph tests**

Run:

```bash
pytest tests/unit/test_access8graph_*.py tests/integration/test_access8graph_mrt_flow.py -v
```

Expected: PASS, with UI tests skipped only if wx is unavailable.

- [ ] **Step 2: Run related existing app tests**

Run:

```bash
pytest tests/unit/test_key_echo_app_service.py tests/unit/test_key_echo_use_cases.py tests/unit/test_tool_app_shell.py tests/unit/test_speech_settings_controller.py -v
```

Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run:

```bash
pytest tests/unit tests/integration -v
```

Expected: PASS. If unrelated pre-existing failures appear, record the failing test names and confirm the Access8Graph-focused tests still pass.

- [ ] **Step 4: Run import smoke check**

Run:

```bash
PYTHONPATH=src python -m apps.access8graph.main
```

Expected: On a desktop environment with wx support, the Access8Graph tray app starts. In a headless environment, it may fail with a wx display error; record that as an environment limitation after the unit and integration tests pass.

- [ ] **Step 5: Commit any verification fixes**

If verification required code changes, run:

```bash
git add src/apps/access8graph src/ui/access8graph tests/unit/test_access8graph_*.py tests/integration/test_access8graph_mrt_flow.py
git commit -m "fix: stabilize access8graph gui mrt migration"
```

If no verification fixes were required, do not create an empty commit.

## Spec Coverage Review

- GUI MVP matching `key_echo`: Task 6.
- Tray main/speech settings/exit via shared shell: Task 6.
- `.graphml`-only picker: Task 6.
- MRT-only migration excluding `directedGraphView.py`: Tasks 1 and 4.
- NVDA-free parser/model/navigator: Task 1.
- HID-to-command mapping without `kb:` normalization: Task 2.
- `BreakCommand(time=1)` between speech items: Task 3.
- Keyboard pipeline and suppression behavior while active: Task 5.
- Escape and Stop Navigation exit behavior: Tasks 5 and 6.
- Flow startup and MRT menu speech: Tasks 4 and 7.
- Focused, integration, UI, and manual verification: Tasks 6, 7, and 8.
