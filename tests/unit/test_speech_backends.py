import json
import threading
import time

import pytest

from adapters.windows.pyttsx3_output import Pyttsx3SpeechOutput
from application.config import SpeechBackendConfigStore
from application.speech_backends import SpeechBackendManager, SpeechBackendOption
from remote_core.models.speech_commands import (
    BreakCommand,
    PitchCommand,
    RateCommand,
    VolumeCommand,
)
from remote_core.models.speech_sequence import SpeechSequence


class FakeSpeechOutput:
    def __init__(self, name: str, events: list[tuple[str, str]]) -> None:
        self.name = name
        self.events = events

    def speak(self, speech) -> None:
        self.events.append(("speak", self.name))

    def cancel(self) -> None:
        self.events.append(("cancel", self.name))

    def pause(self, is_paused: bool) -> None:
        self.events.append(("pause", self.name))

    def list_voices(self):
        return ()

    def get_voice(self):
        return None

    def set_voice(self, voice_id: str) -> None:
        return None

    def get_rate(self):
        return None

    def set_rate(self, value: int) -> None:
        return None

    def get_pitch(self):
        return None

    def set_pitch(self, value: int) -> None:
        return None

    def get_volume(self):
        return None

    def set_volume(self, value: int) -> None:
        return None


class FakeEngine:
    def __init__(self) -> None:
        self.say_calls: list[str] = []
        self.run_count = 0
        self.stop_count = 0
        self.finished = threading.Event()
        self.properties: dict[str, object] = {}

    def say(self, text: str) -> None:
        self.say_calls.append(text)

    def setProperty(self, name: str, value: object) -> None:
        self.properties[name] = value

    def getProperty(self, name: str) -> object:
        return self.properties.get(name, [])

    def runAndWait(self) -> None:
        self.run_count += 1
        self.finished.set()

    def stop(self) -> None:
        self.stop_count += 1


class BlockingEngine:
    def __init__(self) -> None:
        self.say_calls: list[str] = []
        self.started = threading.Event()
        self.stopped = threading.Event()
        self.finished = threading.Event()
        self.stop_count = 0
        self.properties: dict[str, object] = {}

    def say(self, text: str) -> None:
        self.say_calls.append(text)

    def setProperty(self, name: str, value: object) -> None:
        self.properties[name] = value

    def runAndWait(self) -> None:
        self.started.set()
        while not self.stopped.is_set():
            time.sleep(0.01)
        self.finished.set()

    def stop(self) -> None:
        self.stop_count += 1
        self.stopped.set()


class PoisonableEngine:
    def __init__(self, name: str) -> None:
        self.name = name
        self.say_calls: list[str] = []
        self.run_count = 0
        self.stop_count = 0
        self.poisoned = False
        self.finished = threading.Event()
        self.properties: dict[str, object] = {}

    def say(self, text: str) -> None:
        if self.poisoned:
            raise RuntimeError(f"{self.name} cannot speak after stop")
        self.say_calls.append(text)

    def setProperty(self, name: str, value: object) -> None:
        if self.poisoned:
            raise RuntimeError(f"{self.name} cannot set properties after stop")
        self.properties[name] = value

    def runAndWait(self) -> None:
        if self.poisoned:
            raise RuntimeError(f"{self.name} cannot run after stop")
        self.run_count += 1
        self.finished.set()

    def stop(self) -> None:
        self.stop_count += 1
        self.poisoned = True


class FakeTaskManager:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def add_speak_task(self, voice_instance, speak_fn, *, token=None, timeout=None):
        text = None
        if getattr(speak_fn, "__defaults__", None):
            text = speak_fn.__defaults__[0]
        self.calls.append(("speak", text))
        speak_fn()
        return None

    def add_break_task(self, voice_instance, seconds: float):
        self.calls.append(("break", seconds))
        return None

    def cancel(self) -> None:
        self.calls.append(("cancel", None))


def test_speech_backend_manager_switches_backend_and_cancels_previous():
    events: list[tuple[str, str]] = []
    manager = SpeechBackendManager(
        backend_options=(
            SpeechBackendOption(
                backend_id="nvda_controller",
                label="NVDA Controller",
                factory=lambda: FakeSpeechOutput("nvda_controller", events),
            ),
            SpeechBackendOption(
                backend_id="pyttsx3",
                label="pyttsx3",
                factory=lambda: FakeSpeechOutput("pyttsx3", events),
            ),
        ),
        selected_backend_id="nvda_controller",
    )

    previous = manager.current_output
    manager.set_backend("pyttsx3")

    assert previous is not manager.current_output
    assert manager.selected_backend_id == "pyttsx3"
    assert events == [("cancel", "nvda_controller")]


def test_speech_backend_manager_rejects_unknown_backend():
    manager = SpeechBackendManager(
        backend_options=(
            SpeechBackendOption(
                backend_id="nvda_controller",
                label="NVDA Controller",
                factory=lambda: FakeSpeechOutput("nvda_controller", []),
            ),
        ),
        selected_backend_id="nvda_controller",
    )

    with pytest.raises(ValueError, match="Unknown speech backend"):
        manager.set_backend("pyttsx3")


def test_pyttsx3_backend_schedules_real_breaks_between_text_chunks():
    engine = FakeEngine()
    task_manager = FakeTaskManager()
    output = Pyttsx3SpeechOutput(engine=engine, task_manager=task_manager)
    sequence = SpeechSequence(items=("hello", BreakCommand(time=50), "world"))

    output.speak(sequence)

    assert task_manager.calls == [
        ("speak", "hello"),
        ("break", 0.05),
        ("speak", "world"),
    ]
    assert engine.say_calls == ["hello", "world"]

def test_pyttsx3_backend_tracks_rate_pitch_and_volume_commands():
    engine = FakeEngine()
    task_manager = FakeTaskManager()
    output = Pyttsx3SpeechOutput(engine=engine, task_manager=task_manager)
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


def test_pyttsx3_speech_output_ignores_empty_sequence():
    engine = FakeEngine()
    task_manager = FakeTaskManager()
    output = Pyttsx3SpeechOutput(engine=engine, task_manager=task_manager)

    output.speak(SpeechSequence(()))

    assert engine.say_calls == []
    assert task_manager.calls == []


def test_pyttsx3_speech_output_cancel_interrupts_current_speech():
    engine = BlockingEngine()
    output = Pyttsx3SpeechOutput(engine=engine)
    sequence = SpeechSequence(items=("interrupt me",))

    output.speak(sequence)
    assert engine.started.wait(timeout=0.5)

    output.cancel()

    assert engine.stop_count == 1
    assert engine.finished.wait(timeout=0.5)


def test_pyttsx3_speech_output_uses_fresh_engine_after_cancel():
    engines: list[PoisonableEngine] = []

    def engine_factory():
        engine = PoisonableEngine(name=f"engine-{len(engines)}")
        engines.append(engine)
        return engine

    output = Pyttsx3SpeechOutput(
        engine_factory=engine_factory,
        recreate_engine_per_utterance=True,
    )
    first = SpeechSequence(items=("first",))
    second = SpeechSequence(items=("second",))

    output.speak(first)
    deadline = time.time() + 0.5
    while not engines and time.time() < deadline:
        time.sleep(0.01)
    assert engines
    assert engines[0].finished.wait(timeout=0.5)
    output.cancel()
    output.speak(second)
    deadline = time.time() + 0.5
    while len(engines) < 2 and time.time() < deadline:
        time.sleep(0.01)
    assert len(engines) == 2
    assert engines[1].finished.wait(timeout=0.5)

    assert engines[0].say_calls == ["first"]
    assert engines[0].stop_count == 0
    assert engines[1].say_calls == ["second"]


def test_speech_backend_config_store_loads_and_saves_backend_id(tmp_path):
    config_path = tmp_path / "client-config.json"
    store = SpeechBackendConfigStore(config_path)

    assert store.load_backend_id(default_backend_id="nvda_controller") == "nvda_controller"

    store.save_backend_id("pyttsx3")

    assert json.loads(config_path.read_text(encoding="utf-8")) == {
        "speech_backend": "pyttsx3"
    }
    assert store.load_backend_id(default_backend_id="nvda_controller") == "pyttsx3"
