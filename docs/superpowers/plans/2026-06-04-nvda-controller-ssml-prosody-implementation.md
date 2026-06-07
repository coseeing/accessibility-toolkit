# NVDA Controller SSML Prosody Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `NvdaControllerSpeechOutput` to send SSML through `nvdaController_speakSsml`, complete the local prosody command model with `offset` and `multiplier`, and keep remote payload restore aligned with that richer model.

**Architecture:** Keep the existing end-to-end `SpeechSequence` path. Extend the local speech command model first, then update serializer restore, then teach `NvdaControllerSpeechOutput` to maintain local prosody state and convert supported commands into SSML using that state as the baseline. Leave unsupported commands as safe no-ops.

**Tech Stack:** Python 3.11+, `pytest`, existing `interop` models/serializer, `ctypes`-backed NVDA controller DLL wrapper, existing speech backend interfaces

---

## File Structure

### Modify

- `src/interop/models/speech_commands.py`
  Expand `PitchCommand`, `RateCommand`, and `VolumeCommand` to support both `offset` and `multiplier`, plus restore helpers for both formats.
- `src/interop/models/speech_sequence.py`
  Keep payload restoration aligned with the richer prosody command model.
- `src/interop/serializer.py`
  Verify deserialize path keeps restoring the richer prosody payload forms.
- `src/adapters/windows/nvda_controller.py`
  Replace the text-flattening speak path with SSML generation plus local prosody state.
- `tests/unit/test_speech_commands.py`
  Add model and restore coverage for both prosody representations.
- `tests/unit/test_protocol_serializer.py`
  Add deserialize coverage for `offset` and `multiplier` payloads.
- `tests/unit/test_speech_backends.py`
  Add `NvdaControllerSpeechOutput` coverage for SSML output, break mapping, prosody mapping, and local state.

### Keep Untouched

- `src/adapters/outputs/drivers/pyttsx3.py`
  No structural changes in this plan; only ensure test coverage still passes.
- `src/application/controller.py`
  No API shape changes needed for this work.
- `src/ui/main_frame.py`
  Existing UI control APIs remain the same.

## Task 1: Complete The Local Prosody Command Model

**Files:**
- Modify: `src/interop/models/speech_commands.py`
- Test: `tests/unit/test_speech_commands.py`

- [ ] **Step 1: Write the failing tests**

```python
import pytest

from interop.models.speech_commands import (
    PitchCommand,
    RateCommand,
    VolumeCommand,
    restore_speech_command,
)


@pytest.mark.parametrize(
    ("factory", "payload", "expected_mode"),
    [
        (PitchCommand, {"offset": 4}, "offset"),
        (PitchCommand, {"multiplier": 1.1}, "multiplier"),
        (RateCommand, {"offset": 10}, "offset"),
        (RateCommand, {"multiplier": 1.2}, "multiplier"),
        (VolumeCommand, {"offset": -5}, "offset"),
        (VolumeCommand, {"multiplier": 0.8}, "multiplier"),
    ],
)
def test_prosody_commands_accept_offset_or_multiplier(factory, payload, expected_mode):
    command = factory(**payload)

    assert command.mode == expected_mode


@pytest.mark.parametrize("factory", [PitchCommand, RateCommand, VolumeCommand])
def test_prosody_commands_reject_offset_and_multiplier_together(factory):
    with pytest.raises(ValueError, match="offset and multiplier"):
        factory(offset=2, multiplier=1.1)


def test_restore_speech_command_accepts_offset_and_multiplier_payloads():
    assert restore_speech_command("PitchCommand", {"offset": 5}) == PitchCommand(offset=5)
    assert restore_speech_command("PitchCommand", {"multiplier": 1.3}) == PitchCommand(multiplier=1.3)
    assert restore_speech_command("RateCommand", {"offset": 8}) == RateCommand(offset=8)
    assert restore_speech_command("RateCommand", {"multiplier": 0.9}) == RateCommand(multiplier=0.9)
    assert restore_speech_command("VolumeCommand", {"offset": -10}) == VolumeCommand(offset=-10)
    assert restore_speech_command("VolumeCommand", {"multiplier": 0.5}) == VolumeCommand(multiplier=0.5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_speech_commands.py -v`
Expected: FAIL because `PitchCommand`, `RateCommand`, and `VolumeCommand` do not yet accept both `offset` and `multiplier`, and do not expose `mode`.

- [ ] **Step 3: Write the minimal implementation**

```python
# src/interop/models/speech_commands.py
from dataclasses import dataclass, field
from typing import Callable, Literal


ProsodyMode = Literal["default", "offset", "multiplier"]


@dataclass(frozen=True, slots=True)
class SpeechCommand:
    kind: str
    data: dict[str, object] = field(default_factory=dict)


def _coerce_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True, slots=True)
class ProsodyCommand(SpeechCommand):
    offset: int = 0
    multiplier: float = 1.0
    mode: ProsodyMode = "default"

    def __init__(self, kind: str, *, offset: int = 0, multiplier: float = 1.0) -> None:
        if offset != 0 and multiplier != 1.0:
            raise ValueError("offset and multiplier cannot both be non-default")
        mode: ProsodyMode
        if offset != 0:
            mode = "offset"
        elif multiplier != 1.0:
            mode = "multiplier"
        else:
            mode = "default"
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "data", {"offset": offset, "multiplier": multiplier, "mode": mode})
        object.__setattr__(self, "offset", offset)
        object.__setattr__(self, "multiplier", multiplier)
        object.__setattr__(self, "mode", mode)


@dataclass(frozen=True, slots=True)
class PitchCommand(ProsodyCommand):
    def __init__(self, offset: int = 0, multiplier: float = 1.0) -> None:
        super().__init__("PitchCommand", offset=offset, multiplier=multiplier)


@dataclass(frozen=True, slots=True)
class RateCommand(ProsodyCommand):
    def __init__(self, offset: int = 0, multiplier: float = 1.0) -> None:
        super().__init__("RateCommand", offset=offset, multiplier=multiplier)


@dataclass(frozen=True, slots=True)
class VolumeCommand(ProsodyCommand):
    def __init__(self, offset: int = 0, multiplier: float = 1.0) -> None:
        super().__init__("VolumeCommand", offset=offset, multiplier=multiplier)


def _restore_prosody(factory, data: dict[str, object]):
    offset = _coerce_int(data.get("offset", 0), 0)
    multiplier = _coerce_float(data.get("multiplier", 1.0), 1.0)
    if "offset" in data and "multiplier" not in data:
        return factory(offset=offset)
    if "multiplier" in data and "offset" not in data:
        return factory(multiplier=multiplier)
    if "offset" in data and "multiplier" in data:
        return factory(offset=offset, multiplier=multiplier)
    return factory()
```

```python
# append or update SUPPORTED_COMMAND_FACTORIES in src/interop/models/speech_commands.py
SUPPORTED_COMMAND_FACTORIES: dict[str, Callable[[dict[str, object]], SpeechCommand]] = {
    "PitchCommand": lambda data: _restore_prosody(PitchCommand, data),
    "RateCommand": lambda data: _restore_prosody(RateCommand, data),
    "VolumeCommand": lambda data: _restore_prosody(VolumeCommand, data),
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_speech_commands.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/interop/models/speech_commands.py tests/unit/test_speech_commands.py
git commit -m "feat: complete local prosody command model"
```

## Task 2: Align Payload Restore And Serializer Coverage

**Files:**
- Modify: `src/interop/models/speech_sequence.py`
- Modify: `src/interop/serializer.py`
- Modify: `tests/unit/test_protocol_serializer.py`

- [ ] **Step 1: Write the failing tests**

```python
from interop.models.speech_commands import PitchCommand, RateCommand, VolumeCommand
from interop.serializer import JSONSerializer


def test_serializer_restores_offset_and_multiplier_prosody_payloads():
    serializer = JSONSerializer()
    payload = (
        b'{"type":"speak","sequence":['
        b'"hello",'
        b'["PitchCommand",{"multiplier":1.2}],'
        b'["RateCommand",{"offset":7}],'
        b'["VolumeCommand",{"multiplier":0.6}]'
        b']}\n'
    )

    decoded = serializer.deserialize(payload.strip())

    assert decoded["sequence"] == [
        "hello",
        PitchCommand(multiplier=1.2),
        RateCommand(offset=7),
        VolumeCommand(multiplier=0.6),
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_protocol_serializer.py::test_serializer_restores_offset_and_multiplier_prosody_payloads -v`
Expected: FAIL because serializer restore does not yet round-trip the richer prosody model correctly.

- [ ] **Step 3: Write the minimal implementation**

```python
# src/interop/models/speech_sequence.py
from dataclasses import dataclass

from interop.models.speech_commands import SpeechCommand, restore_speech_command


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
            if isinstance(item, SpeechCommand):
                restored.append(item)
                continue
            if (
                isinstance(item, (list, tuple))
                and len(item) >= 2
                and isinstance(item[0], str)
                and isinstance(item[1], dict)
            ):
                restored.append(restore_speech_command(item[0], item[1]))
        return cls(items=tuple(restored))
```

```python
# src/interop/serializer.py
def _as_sequence(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("type") != "speak" or "sequence" not in payload:
        return payload

    raw_sequence = payload["sequence"]
    if not isinstance(raw_sequence, list):
        return payload

    sequence: list[Any] = []
    for item in raw_sequence:
        if isinstance(item, str):
            sequence.append(item)
            continue
        if (
            isinstance(item, list)
            and len(item) >= 2
            and isinstance(item[0], str)
            and isinstance(item[1], dict)
        ):
            sequence.append(restore_speech_command(item[0], item[1]))
            continue
        sequence.append(item)
    payload["sequence"] = sequence
    return payload
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_protocol_serializer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/interop/models/speech_sequence.py src/interop/serializer.py tests/unit/test_protocol_serializer.py
git commit -m "test: cover richer prosody payload restore"
```

## Task 3: Add NVDA Controller SSML Conversion And Local Prosody State

**Files:**
- Modify: `src/adapters/windows/nvda_controller.py`
- Test: `tests/unit/test_speech_backends.py`

- [ ] **Step 1: Write the failing tests**

```python
from adapters.windows.nvda_controller import NvdaControllerSpeechOutput
from interop.models.speech_commands import BreakCommand, PitchCommand, RateCommand, VolumeCommand
from interop.models.speech_sequence import SpeechSequence


class FakeNvdaController:
    def __init__(self) -> None:
        self.ssml_calls: list[tuple[str, int, int, bool]] = []
        self.cancel_calls = 0

    def nvdaController_speakSsml(self, ssml: str, symbol_level: int, priority: int, asynchronous: bool) -> int:
        self.ssml_calls.append((ssml, symbol_level, priority, asynchronous))
        return 0

    def nvdaController_cancelSpeech(self) -> int:
        self.cancel_calls += 1
        return 0


def test_nvda_controller_outputs_ssml_for_break_and_prosody_commands():
    controller = FakeNvdaController()
    output = NvdaControllerSpeechOutput(controller=controller)
    output.set_rate(100)
    output.set_pitch(20)
    output.set_volume(80)

    output.speak(
        SpeechSequence(
            items=(
                "hello",
                BreakCommand(time=50),
                PitchCommand(offset=10),
                RateCommand(multiplier=1.2),
                VolumeCommand(offset=20),
                "world",
            )
        )
    )

    ssml, symbol_level, priority, asynchronous = controller.ssml_calls[0]
    assert "<break time=\"50ms\"/>" in ssml
    assert "pitch=" in ssml
    assert "rate=\"120%\"" in ssml
    assert "volume=" in ssml
    assert "hello" in ssml
    assert "world" in ssml
    assert symbol_level == 0
    assert priority == 0
    assert asynchronous is True


def test_nvda_controller_uses_local_state_as_baseline_for_offset_commands():
    controller = FakeNvdaController()
    output = NvdaControllerSpeechOutput(controller=controller)
    output.set_rate(80)
    output.set_pitch(10)
    output.set_volume(50)

    output.speak(
        SpeechSequence(
            items=(
                RateCommand(offset=20),
                PitchCommand(offset=5),
                VolumeCommand(offset=25),
                "hello",
            )
        )
    )

    ssml = controller.ssml_calls[0][0]
    assert 'rate="125%"' in ssml
    assert 'pitch="150%"' in ssml
    assert 'volume="150%"' in ssml
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_speech_backends.py -k nvda_controller -v`
Expected: FAIL because `NvdaControllerSpeechOutput` still flattens text and calls `nvdaController_speakText`.

- [ ] **Step 3: Write the minimal implementation**

```python
# src/adapters/windows/nvda_controller.py
SPEAK_SSML_FUNCTION = "nvdaController_speakSsml"
CANCEL_SPEECH_FUNCTION = "nvdaController_cancelSpeech"


class NvdaControllerSpeechOutput:
    def __init__(self, controller: Any | None, *, loaded_from: str | None = None) -> None:
        self.controller = controller
        self.available = controller is not None
        self.loaded_from = loaded_from
        self._rate = 100
        self._pitch = 100
        self._volume = 100

    def speak(self, speech: SpeechSequence) -> None:
        if not self.available:
            logger.debug("NVDA controller unavailable; speech output skipped")
            return
        ssml = self._sequence_to_ssml(speech)
        if not ssml:
            logger.debug("NVDA controller SSML is empty; speak skipped")
            return
        try:
            result = getattr(self.controller, SPEAK_SSML_FUNCTION)(ssml, 0, 0, True)
            logger.debug("NVDA controller speakSsml returned %r", result)
        except Exception:
            logger.exception("NVDA controller speakSsml raised an exception")

    def get_rate(self) -> int | None:
        return self._rate

    def set_rate(self, value: int) -> None:
        self._rate = value

    def get_pitch(self) -> int | None:
        return self._pitch

    def set_pitch(self, value: int) -> None:
        self._pitch = value

    def get_volume(self) -> int | None:
        return self._volume

    def set_volume(self, value: int) -> None:
        self._volume = value
```

```python
# helper sketch inside src/adapters/windows/nvda_controller.py
def _percentage_from_offset(baseline: int, offset: int) -> int:
    if baseline <= 0:
        baseline = 100
    return int(((baseline + offset) / baseline) * 100)
```

```python
# helper sketch inside src/adapters/windows/nvda_controller.py
def _sequence_to_ssml(self, speech: SpeechSequence) -> str:
    fragments: list[str] = ['<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis">']
    active_attrs: dict[str, str] = {}

    for item in speech.items:
        if isinstance(item, str):
            escaped = (
                item.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )
            if active_attrs:
                attrs = " ".join(f'{key}="{value}"' for key, value in active_attrs.items())
                fragments.append(f"<prosody {attrs}>{escaped}</prosody>")
            else:
                fragments.append(escaped)
            continue
        if isinstance(item, BreakCommand):
            fragments.append(f'<break time="{max(item.time, 0)}ms"/>')
            continue
        if isinstance(item, PitchCommand):
            active_attrs["pitch"] = (
                f"{int(item.multiplier * 100)}%"
                if item.mode == "multiplier"
                else f"{_percentage_from_offset(self._pitch, item.offset)}%"
            )
            continue
        if isinstance(item, RateCommand):
            active_attrs["rate"] = (
                f"{int(item.multiplier * 100)}%"
                if item.mode == "multiplier"
                else f"{_percentage_from_offset(self._rate, item.offset)}%"
            )
            continue
        if isinstance(item, VolumeCommand):
            active_attrs["volume"] = (
                f"{int(item.multiplier * 100)}%"
                if item.mode == "multiplier"
                else f"{_percentage_from_offset(self._volume, item.offset)}%"
            )
            continue

    fragments.append("</speak>")
    body = "".join(fragment for fragment in fragments if fragment)
    return "" if body == '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"></speak>' else body
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_speech_backends.py -k nvda_controller -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/windows/nvda_controller.py tests/unit/test_speech_backends.py
git commit -m "feat: route nvda controller speech through ssml"
```

## Task 4: Run Regression Coverage For Existing Speech Paths

**Files:**
- Test: `tests/unit/test_speech_commands.py`
- Test: `tests/unit/test_protocol_serializer.py`
- Test: `tests/unit/test_speech_backends.py`
- Test: `tests/unit/test_message_router.py`
- Test: `tests/unit/test_output_manager.py`

- [ ] **Step 1: Run the focused regression suite**

Run: `pytest tests/unit/test_speech_commands.py tests/unit/test_protocol_serializer.py tests/unit/test_speech_backends.py tests/unit/test_message_router.py tests/unit/test_output_manager.py -v`
Expected: PASS with all focused speech-path tests green.

- [ ] **Step 2: Inspect for unintended pyttsx3 regressions**

Run: `pytest tests/unit/test_speech_backends.py -k pyttsx3 -v`
Expected: PASS with existing `pyttsx3` speech sequence and break scheduling tests still green.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_speech_commands.py tests/unit/test_protocol_serializer.py tests/unit/test_speech_backends.py
git commit -m "test: verify nvda controller ssml prosody path"
```

## Self-Review

- Spec coverage:
  - `NvdaControllerSpeechOutput -> speakSsml`: covered by Task 3.
  - `Pitch/Rate/Volume offset + multiplier model`: covered by Task 1.
  - Restore layer accepting both formats: covered by Task 2.
  - Backend local prosody state as baseline: covered by Task 3.
  - Regression safety for existing sequence path: covered by Task 4.
- Placeholder scan:
  - No `TODO`, `TBD`, or “similar to previous task” placeholders remain.
- Type consistency:
  - The plan consistently uses `mode`, `offset`, `multiplier`, `SpeechSequence`, and `NvdaControllerSpeechOutput`.
