# WorldVoice pyttsx3 Small Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `nvda-remote-client` restore remote NVDA speech sequences into command objects during deserialization, route complete sequences to an upgraded `pyttsx3` backend, use a transplanted `taskManager` for real break scheduling, and expose minimal GUI controls for voice, rate, volume, and pitch.

**Architecture:** Keep the larger `WorldVoice` core-extraction work out of scope. Follow NVDA `_remoteClient.serializer` by reconstructing speech commands during deserialization, then carry full speech sequences end-to-end, transplant only `taskManager`, and evolve the existing `pyttsx3` backend into a sequence-aware backend that interprets commands locally while the GUI remains a thin shell over controller/backend APIs.

**Tech Stack:** Python 3.11+, `pytest`, `wxPython`, `pyttsx3`, transplanted `WorldVoice` `taskManager`, existing `application` / `interop` / `adapters` layers

---

## File Structure

### Create

- `src/interop/models/speech_commands.py`
  Client-local NVDA speech command compatibility classes such as `SpeechCommand`, `BreakCommand`, `PitchCommand`, `RateCommand`, `VolumeCommand`, `LangChangeCommand`, and `IndexCommand`.
- `src/interop/models/speech_sequence.py`
  Immutable container plus payload restoration helpers for `list[str | SpeechCommand]` sequences.
- `src/adapters/worldvoice_task/__init__.py`
  Package marker for transplanted scheduling code.
- `src/adapters/worldvoice_task/events.py`
  Local callback/event types replacing NVDA notification globals from `WorldVoice`.
- `src/adapters/worldvoice_task/task_manager.py`
  Transplanted and client-adapted `taskManager`.
- `tests/unit/test_speech_commands.py`
  Coverage for command restoration and sequence modeling.
- `tests/unit/test_worldvoice_task_manager.py`
  Coverage for transplanted task scheduling behavior.

### Modify

- `src/interop/serializer.py`
  Reconstruct `speak` payload sequences during deserialization, following NVDA `_remoteClient.serializer`.
- `src/interop/routing/message_router.py`
  Consume already-restored full speech sequences instead of only `NormalizedSpeech`.
- `src/application/services.py`
  Let `OutputManager` forward full speech sequences.
- `src/adapters/outputs/speech.py`
  Update the speech backend protocol to accept the new speech sequence model and expose voice/rate/volume/pitch controls.
- `src/adapters/windows/nvda_controller.py`
  Keep working under the new backend contract by flattening supported text segments internally and returning unsupported-control defaults.
- `src/adapters/windows/pyttsx3_output.py`
  Upgrade to a sequence-aware backend driven by transplanted `taskManager`.
- `src/application/speech_backends.py`
  Keep backend registration compatible with the upgraded `pyttsx3` backend.
- `src/application/controller.py`
  Add APIs for voice/rate/volume/pitch UI actions.
- `src/ui/main.py`
  Keep backend wiring intact under the new backend protocol.
- `src/ui/main_frame.py`
  Add GUI controls for voice, rate, volume, and pitch.
- `tests/unit/test_message_router.py`
  Update routing expectations from `NormalizedSpeech` to full restored sequences.
- `tests/unit/test_output_manager.py`
  Update output manager tests for the new sequence model.
- `tests/unit/test_speech_backends.py`
  Replace normalized-speech assumptions with full-sequence behavior and command scheduling assertions.
- `tests/unit/test_application_controller.py`
  Add controller tests for voice/rate/volume/pitch pass-through.
- `tests/unit/test_app_wx.py`
  Add GUI tests for new speech controls and backend-specific enablement.

## Task 1: Add Speech Command Compatibility Types

**Files:**
- Create: `src/interop/models/speech_commands.py`
- Create: `src/interop/models/speech_sequence.py`
- Test: `tests/unit/test_speech_commands.py`

- [ ] **Step 1: Write the failing tests**

```python
from interop.models.speech_commands import (
    BreakCommand,
    PitchCommand,
    RateCommand,
    SpeechCommand,
    VolumeCommand,
)
from interop.models.speech_sequence import SpeechSequence


def test_speech_sequence_restores_text_and_supported_commands():
    payload = {
        "sequence": [
            "hello",
            ["BreakCommand", {"time": 75}],
            ["PitchCommand", {"offset": 12}],
            ["RateCommand", {"multiplier": 1.5}],
            ["VolumeCommand", {"multiplier": 0.5}],
            "world",
        ]
    }

    restored = SpeechSequence.from_remote_payload(payload)

    assert restored.items == (
        "hello",
        BreakCommand(time=75),
        PitchCommand(offset=12),
        RateCommand(multiplier=1.5),
        VolumeCommand(multiplier=0.5),
        "world",
    )


def test_speech_sequence_preserves_unknown_command_as_generic_speech_command():
    payload = {"sequence": [["MyCommand", {"value": 3}]]}

    restored = SpeechSequence.from_remote_payload(payload)

    assert restored.items == (
        SpeechCommand(kind="MyCommand", data={"value": 3}),
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_speech_commands.py -v`
Expected: FAIL with `ModuleNotFoundError` for `interop.models.speech_commands`

- [ ] **Step 3: Write the minimal compatibility layer**

```python
# src/interop/models/speech_commands.py
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SpeechCommand:
    kind: str
    data: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class IndexCommand(SpeechCommand):
    index: int = 0

    def __init__(self, index: int) -> None:
        object.__setattr__(self, "kind", "IndexCommand")
        object.__setattr__(self, "data", {"index": index})
        object.__setattr__(self, "index", index)


@dataclass(frozen=True, slots=True)
class BreakCommand(SpeechCommand):
    time: int = 0

    def __init__(self, time: int = 0) -> None:
        object.__setattr__(self, "kind", "BreakCommand")
        object.__setattr__(self, "data", {"time": time})
        object.__setattr__(self, "time", time)


@dataclass(frozen=True, slots=True)
class PitchCommand(SpeechCommand):
    offset: int = 0

    def __init__(self, offset: int = 0) -> None:
        object.__setattr__(self, "kind", "PitchCommand")
        object.__setattr__(self, "data", {"offset": offset})
        object.__setattr__(self, "offset", offset)


@dataclass(frozen=True, slots=True)
class RateCommand(SpeechCommand):
    multiplier: float = 1.0

    def __init__(self, multiplier: float = 1.0) -> None:
        object.__setattr__(self, "kind", "RateCommand")
        object.__setattr__(self, "data", {"multiplier": multiplier})
        object.__setattr__(self, "multiplier", multiplier)


@dataclass(frozen=True, slots=True)
class VolumeCommand(SpeechCommand):
    multiplier: float = 1.0

    def __init__(self, multiplier: float = 1.0) -> None:
        object.__setattr__(self, "kind", "VolumeCommand")
        object.__setattr__(self, "data", {"multiplier": multiplier})
        object.__setattr__(self, "multiplier", multiplier)
```

```python
# src/interop/models/speech_sequence.py
from dataclasses import dataclass

from interop.models.speech_commands import (
    BreakCommand,
    PitchCommand,
    RateCommand,
    SpeechCommand,
    VolumeCommand,
)


_FACTORIES = {
    "BreakCommand": lambda data: BreakCommand(time=int(data.get("time", 0))),
    "PitchCommand": lambda data: PitchCommand(offset=int(data.get("offset", 0))),
    "RateCommand": lambda data: RateCommand(multiplier=float(data.get("multiplier", 1.0))),
    "VolumeCommand": lambda data: VolumeCommand(multiplier=float(data.get("multiplier", 1.0))),
}


@dataclass(frozen=True, slots=True)
class SpeechSequence:
    items: tuple[str | SpeechCommand, ...]

    @classmethod
    def from_remote_payload(cls, payload: dict[str, object]) -> "SpeechSequence":
        restored: list[str | SpeechCommand] = []
        sequence = payload.get("sequence", [])
        if not isinstance(sequence, (list, tuple)):
            sequence = []
        for item in sequence:
            if isinstance(item, str):
                restored.append(item)
                continue
            if (
                isinstance(item, (list, tuple))
                and len(item) >= 2
                and isinstance(item[0], str)
                and isinstance(item[1], dict)
            ):
                factory = _FACTORIES.get(item[0])
                restored.append(
                    factory(item[1])
                    if factory is not None
                    else SpeechCommand(kind=item[0], data=dict(item[1]))
                )
        return cls(items=tuple(restored))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_speech_commands.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/interop/models/speech_commands.py src/interop/models/speech_sequence.py tests/unit/test_speech_commands.py
git commit -m "feat: add speech command compatibility layer"
```

## Task 2: Reconstruct Full Speech Sequences During Deserialization

**Files:**
- Modify: `src/interop/serializer.py`
- Modify: `tests/unit/test_protocol_serializer.py`

- [ ] **Step 1: Write the failing serializer tests**

```python
from interop.models.speech_commands import BreakCommand, PitchCommand
from interop.serializer import JSONSerializer


def test_serializer_restores_speak_sequence_during_deserialize():
    serializer = JSONSerializer()
    payload = (
        b'{"type":"speak","sequence":["hello",["BreakCommand",{"time":40}],["PitchCommand",{"offset":2}]]}\n'
    )

    decoded = serializer.deserialize(payload.strip())

    assert decoded["sequence"] == ["hello", BreakCommand(time=40), PitchCommand(offset=2)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_protocol_serializer.py -v`
Expected: FAIL because deserialization still returns raw JSON list items

- [ ] **Step 3: Update serializer to follow NVDA `_remoteClient.serializer`**

```python
# src/interop/serializer.py
import json

from interop.models.speech_commands import (
    BreakCommand,
    PitchCommand,
    RateCommand,
    SpeechCommand,
    VolumeCommand,
)


_SEQUENCE_CLASSES = {
    "BreakCommand": BreakCommand,
    "PitchCommand": PitchCommand,
    "RateCommand": RateCommand,
    "VolumeCommand": VolumeCommand,
}


def _as_sequence(dct: dict[str, object]) -> dict[str, object]:
    if not ("type" in dct and dct["type"] == "speak" and "sequence" in dct):
        return dct
    sequence: list[object] = []
    for item in dct["sequence"]:
        if not isinstance(item, list):
            sequence.append(item)
            continue
        name, values = item
        cls = _SEQUENCE_CLASSES.get(name)
        if cls is None:
            sequence.append(SpeechCommand(kind=name, data=dict(values)))
            continue
        obj = cls.__new__(cls)
        obj.__dict__.update(values)
        obj.__dict__["kind"] = name
        obj.__dict__["data"] = dict(values)
        sequence.append(obj)
    dct["sequence"] = sequence
    return dct


class JSONSerializer:
    def deserialize(self, data: bytes) -> dict[str, object]:
        return json.loads(data, object_hook=_as_sequence)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_protocol_serializer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/interop/serializer.py tests/unit/test_protocol_serializer.py
git commit -m "feat: restore speech commands during deserialize"
```

## Task 3: Route Full Speech Sequences Through MessageRouter And OutputManager

**Files:**
- Modify: `src/interop/routing/message_router.py`
- Modify: `src/application/services.py`
- Modify: `src/adapters/outputs/speech.py`
- Modify: `tests/unit/test_message_router.py`
- Modify: `tests/unit/test_output_manager.py`

- [ ] **Step 1: Write the failing routing and output tests**

```python
from interop.models.speech_commands import BreakCommand
from interop.models.speech_sequence import SpeechSequence


def test_router_dispatches_full_speech_sequence():
    seen = []
    router = MessageRouter(
        on_speech=lambda sequence: seen.append(sequence),
        on_cancel=lambda: None,
        on_pause=lambda paused: None,
        on_clipboard=lambda text: None,
        on_status=lambda event: None,
    )

    router.handle_message(
        {"type": "speak", "sequence": ["hello", ["BreakCommand", {"time": 50}], "world"]}
    )

    assert seen == [
        SpeechSequence(items=("hello", BreakCommand(time=50), "world"))
    ]


def test_output_manager_passes_sequence_to_backend():
    spoken = []

    class FakeSpeechOutput:
        def speak(self, sequence):
            spoken.append(sequence)
        def cancel(self):
            return None
        def pause(self, is_paused):
            return None
        def list_voices(self):
            return ()
        def get_voice(self):
            return None
        def set_voice(self, voice_id):
            return None
        def get_rate(self):
            return None
        def set_rate(self, value):
            return None
        def get_pitch(self):
            return None
        def set_pitch(self, value):
            return None
        def get_volume(self):
            return None
        def set_volume(self, value):
            return None

    manager = OutputManager(speech_output=FakeSpeechOutput(), clipboard=FakeClipboard())
    sequence = SpeechSequence(items=("hello",))

    manager.handle_speech(sequence)

    assert spoken == [sequence]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_message_router.py tests/unit/test_output_manager.py -v`
Expected: FAIL because router still produces `NormalizedSpeech`

- [ ] **Step 3: Update router, output manager, and backend protocol**

```python
# src/adapters/outputs/speech.py
from typing import Protocol

from interop.models.speech_sequence import SpeechSequence


class SpeechOutput(Protocol):
    def speak(self, sequence: SpeechSequence) -> None: ...
    def cancel(self) -> None: ...
    def pause(self, is_paused: bool) -> None: ...
    def list_voices(self) -> tuple[tuple[str, str], ...]: ...
    def get_voice(self) -> str | None: ...
    def set_voice(self, voice_id: str) -> None: ...
    def get_rate(self) -> int | None: ...
    def set_rate(self, value: int) -> None: ...
    def get_pitch(self) -> int | None: ...
    def set_pitch(self, value: int) -> None: ...
    def get_volume(self) -> int | None: ...
    def set_volume(self, value: int) -> None: ...
```

```python
# src/application/services.py
from interop.models.speech_sequence import SpeechSequence


class OutputManager:
    def handle_speech(self, speech: SpeechSequence) -> None:
        self.speech_output.speak(speech)
```

```python
# src/interop/routing/message_router.py
from interop.models.speech_sequence import SpeechSequence


class MessageRouter:
    def handle_message(self, payload: dict[str, Any]) -> None:
        match payload.get("type"):
            case RemoteMessageType.SPEAK.value:
                self._on_speech(SpeechSequence(items=tuple(payload.get("sequence", ()))))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_message_router.py tests/unit/test_output_manager.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/outputs/speech.py src/application/services.py src/interop/routing/message_router.py tests/unit/test_message_router.py tests/unit/test_output_manager.py
git commit -m "feat: route full speech sequences to speech backends"
```

## Task 4: Transplant And Decouple WorldVoice TaskManager

**Files:**
- Create: `src/adapters/worldvoice_task/__init__.py`
- Create: `src/adapters/worldvoice_task/events.py`
- Create: `src/adapters/worldvoice_task/task_manager.py`
- Test: `tests/unit/test_worldvoice_task_manager.py`

- [ ] **Step 1: Copy the WorldVoice task manager and write failing tests**

```bash
mkdir -p src/adapters/worldvoice_task
cp /workspace/WorldVoice/addon/synthDrivers/WorldVoice/taskManager.py src/adapters/worldvoice_task/task_manager.py
```

```python
from adapters.worldvoice_task.task_manager import TaskManager


class FakeVoice:
    def __init__(self):
        self.stop_count = 0

    def stop(self):
        self.stop_count += 1


def test_task_manager_completes_basic_task():
    manager = TaskManager()
    voice = FakeVoice()
    called = []

    future = manager.add_task(voice, lambda: called.append("ran"))

    assert future.result(timeout=0.5) is None
    assert called == ["ran"]
    manager.shutdown()


def test_task_manager_break_task_waits_and_can_cancel():
    manager = TaskManager()
    voice = FakeVoice()
    future = manager.add_break_task(voice, 0.2)

    manager.cancel_current()

    assert voice.stop_count == 1
    future.cancel()
    manager.shutdown()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_worldvoice_task_manager.py -v`
Expected: FAIL due to missing NVDA imports in transplanted file

- [ ] **Step 3: Replace NVDA notification globals with local callbacks**

```python
# src/adapters/worldvoice_task/events.py
from dataclasses import dataclass
from typing import Callable


@dataclass
class SpeechEventCallbacks:
    on_index_reached: Callable[[int | None], None] = lambda index: None
    on_done_speaking: Callable[[], None] = lambda: None
```

```python
# src/adapters/worldvoice_task/task_manager.py
from adapters.worldvoice_task.events import SpeechEventCallbacks


class TaskManager:
    def __init__(self, callbacks: SpeechEventCallbacks | None = None):
        self._callbacks = callbacks or SpeechEventCallbacks()
        ...

    def notify_index_reached(self, index: int | None) -> None:
        self._callbacks.on_index_reached(index)

    def notify_done_speaking(self) -> None:
        self._callbacks.on_done_speaking()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_worldvoice_task_manager.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/worldvoice_task/__init__.py src/adapters/worldvoice_task/events.py src/adapters/worldvoice_task/task_manager.py tests/unit/test_worldvoice_task_manager.py
git commit -m "feat: transplant worldvoice task manager"
```

## Task 5: Upgrade pyttsx3 Backend To Use Sequences And Real Break Scheduling

**Files:**
- Modify: `src/adapters/windows/pyttsx3_output.py`
- Modify: `tests/unit/test_speech_backends.py`

- [ ] **Step 1: Write the failing backend tests**

```python
from interop.models.speech_commands import BreakCommand, PitchCommand, RateCommand, VolumeCommand
from interop.models.speech_sequence import SpeechSequence


def test_pyttsx3_backend_schedules_real_breaks_between_text_chunks():
    engine = FakeEngine()
    output = Pyttsx3SpeechOutput(engine=engine, task_manager=FakeTaskManager())
    sequence = SpeechSequence(items=("hello", BreakCommand(time=50), "world"))

    output.speak(sequence)

    assert output._task_manager.calls == [
        ("speak", "hello"),
        ("break", 0.05),
        ("speak", "world"),
    ]


def test_pyttsx3_backend_tracks_rate_pitch_and_volume_commands():
    engine = FakeEngine()
    output = Pyttsx3SpeechOutput(engine=engine, task_manager=FakeTaskManager())
    sequence = SpeechSequence(
        items=(
            PitchCommand(offset=3),
            RateCommand(multiplier=1.2),
            VolumeCommand(multiplier=0.8),
            "hello",
        )
    )

    output.speak(sequence)

    assert output.get_pitch() == 3
    assert output.get_rate() == 120
    assert output.get_volume() == 80
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_speech_backends.py -v`
Expected: FAIL because `pyttsx3` still expects `NormalizedSpeech`

- [ ] **Step 3: Replace normalized-speech assumptions with sequence scheduling**

```python
# src/adapters/windows/pyttsx3_output.py
from adapters.worldvoice_task.task_manager import TaskManager
from interop.models.speech_commands import BreakCommand, PitchCommand, RateCommand, VolumeCommand
from interop.models.speech_sequence import SpeechSequence


class Pyttsx3SpeechOutput:
    def __init__(..., task_manager: TaskManager | None = None) -> None:
        ...
        self._task_manager = task_manager or TaskManager()
        self._voice_id: str | None = None
        self._rate = 100
        self._pitch = 0
        self._volume = 100

    def speak(self, sequence: SpeechSequence) -> None:
        for item in sequence.items:
            if isinstance(item, str) and item:
                self._task_manager.add_speak_task(self, lambda text=item: self._speak_text(text))
            elif isinstance(item, BreakCommand):
                self._task_manager.add_break_task(self, item.time / 1000.0)
            elif isinstance(item, PitchCommand):
                self._pitch = item.offset
            elif isinstance(item, RateCommand):
                self._rate = int(item.multiplier * 100)
            elif isinstance(item, VolumeCommand):
                self._volume = int(item.multiplier * 100)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_speech_backends.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/windows/pyttsx3_output.py tests/unit/test_speech_backends.py
git commit -m "feat: add sequence scheduling to pyttsx3 backend"
```

## Task 6: Add Voice, Rate, Volume, And Pitch Control APIs To Controller

**Files:**
- Modify: `src/application/controller.py`
- Modify: `tests/unit/test_application_controller.py`

- [ ] **Step 1: Write the failing controller tests**

```python
def test_controller_exposes_voice_and_prosody_controls():
    controller, _transport, _capture, _clipboard, _hotkey = build_controller(
        speech_backend_manager=make_manager_with_pyttsx3_backend()
    )

    assert controller.get_available_voices()
    controller.set_selected_voice("voice-1")
    controller.set_rate(120)
    controller.set_pitch(3)
    controller.set_volume(80)

    assert controller.get_selected_voice() == "voice-1"
    assert controller.get_rate() == 120
    assert controller.get_pitch() == 3
    assert controller.get_volume() == 80
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_application_controller.py -v`
Expected: FAIL because the controller has no voice/rate/pitch/volume APIs

- [ ] **Step 3: Add pass-through methods on the controller**

```python
# src/application/controller.py
def get_available_voices(self) -> tuple[tuple[str, str], ...]:
    return self.output_manager.speech_output.list_voices()


def get_selected_voice(self) -> str | None:
    return self.output_manager.speech_output.get_voice()


def set_selected_voice(self, voice_id: str) -> None:
    self.output_manager.speech_output.set_voice(voice_id)


def get_rate(self) -> int | None:
    return self.output_manager.speech_output.get_rate()


def set_rate(self, value: int) -> None:
    self.output_manager.speech_output.set_rate(value)


def get_pitch(self) -> int | None:
    return self.output_manager.speech_output.get_pitch()


def set_pitch(self, value: int) -> None:
    self.output_manager.speech_output.set_pitch(value)


def get_volume(self) -> int | None:
    return self.output_manager.speech_output.get_volume()


def set_volume(self, value: int) -> None:
    self.output_manager.speech_output.set_volume(value)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_application_controller.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/application/controller.py tests/unit/test_application_controller.py
git commit -m "feat: add speech control APIs to controller"
```

## Task 7: Add GUI Controls For Voice, Rate, Volume, And Pitch

**Files:**
- Modify: `src/ui/main_frame.py`
- Modify: `tests/unit/test_app_wx.py`

- [ ] **Step 1: Write the failing GUI tests**

```python
def test_main_frame_exposes_voice_and_prosody_controls(monkeypatch):
    install_fake_wx(monkeypatch)
    MainFrame = importlib.import_module("ui.main_frame").MainFrame
    controller = FakeController()
    controller.speech_backend_id = "pyttsx3"
    controller.available_voices = (("voice-1", "Voice 1"), ("voice-2", "Voice 2"))
    controller.rate = 120
    controller.pitch = 3
    controller.volume = 80

    frame = MainFrame(controller=controller)

    assert frame.voice_choice.GetCount() == 2
    assert frame.rate_ctrl.GetValue() == "120"
    assert frame.pitch_ctrl.GetValue() == "3"
    assert frame.volume_ctrl.GetValue() == "80"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_app_wx.py -v`
Expected: FAIL because the frame has no speech-control widgets

- [ ] **Step 3: Add controls and wire them to the controller**

```python
# src/ui/main_frame.py
self.voice_choice = wx.Choice(panel, choices=[])
self.rate_ctrl = wx.TextCtrl(panel, value="")
self.pitch_ctrl = wx.TextCtrl(panel, value="")
self.volume_ctrl = wx.TextCtrl(panel, value="")

for widget in (
    self.host_ctrl,
    self.port_ctrl,
    self.key_ctrl,
    self.connect_button,
    self.control_button,
    self.clipboard_button,
    self.speech_backend_choice,
    self.voice_choice,
    self.rate_ctrl,
    self.pitch_ctrl,
    self.volume_ctrl,
):
    sizer.Add(widget, 0, wx.EXPAND | wx.ALL, 4)
```

```python
def _on_voice_change(self, event):
    voice_id = self._voice_id_for_selection(self.voice_choice.GetSelection())
    if voice_id is not None:
        self.controller.set_selected_voice(voice_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_app_wx.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ui/main_frame.py tests/unit/test_app_wx.py
git commit -m "feat: add pyttsx3 speech controls to gui"
```

## Task 8: End-To-End Sequence Path Verification

**Files:**
- Modify: `tests/unit/test_message_router.py`
- Modify: `tests/unit/test_output_manager.py`
- Modify: `tests/unit/test_speech_backends.py`
- Optional doc note: `README.md`

- [ ] **Step 1: Write the failing end-to-end unit test**

```python
def test_sequence_routes_from_router_to_pyttsx3_backend():
    seen = []

    class FakeBackend:
        def speak(self, sequence):
            seen.append(sequence)
        def cancel(self):
            return None
        def pause(self, is_paused):
            return None
        def list_voices(self):
            return ()
        def get_voice(self):
            return None
        def set_voice(self, voice_id):
            return None
        def get_rate(self):
            return None
        def set_rate(self, value):
            return None
        def get_pitch(self):
            return None
        def set_pitch(self, value):
            return None
        def get_volume(self):
            return None
        def set_volume(self, value):
            return None

    router = MessageRouter(
        on_speech=lambda sequence: OutputManager(FakeBackend(), FakeClipboard()).handle_speech(sequence),
        on_cancel=lambda: None,
        on_pause=lambda paused: None,
        on_clipboard=lambda text: None,
        on_status=lambda event: None,
    )

    router.handle_message({"type": "speak", "sequence": ["hello", ["BreakCommand", {"time": 10}], "world"]})

    assert len(seen) == 1
    assert seen[0].items[0] == "hello"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_message_router.py tests/unit/test_output_manager.py tests/unit/test_speech_backends.py -v`
Expected: FAIL until all sequence path pieces are wired consistently

- [ ] **Step 3: Fix any mismatched names or signatures and document manual validation**

```markdown
# README.md
- The pyttsx3 backend now restores remote NVDA speech sequences into local command objects before handing them to the backend.
- GUI exposes voice, rate, pitch, and volume controls when the pyttsx3 backend is active.
```

- [ ] **Step 4: Run focused verification**

Run: `pytest tests/unit/test_speech_commands.py tests/unit/test_message_router.py tests/unit/test_output_manager.py tests/unit/test_worldvoice_task_manager.py tests/unit/test_speech_backends.py tests/unit/test_application_controller.py tests/unit/test_app_wx.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md tests/unit/test_message_router.py tests/unit/test_output_manager.py tests/unit/test_speech_backends.py
git commit -m "test: verify pyttsx3 speech sequence path end to end"
```
