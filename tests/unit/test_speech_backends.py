import json
import threading
import time

import pytest

from adapters.outputs.drivers.pyttsx3 import Pyttsx3SpeechOutput
from application.config import SpeechBackendConfigStore
from application.speech_backends import SpeechBackendManager, SpeechBackendOption
from application.services import OutputManager
from adapters.windows.nvda_controller import NvdaControllerSpeechOutput
from remote_core.models.speech_commands import (
    BreakCommand,
    PitchCommand,
    RateCommand,
    SpeechCommand,
    VolumeCommand,
)
from remote_core.models.speech_sequence import SpeechSequence
from remote_core.routing.message_router import MessageRouter
from remote_core.serializer import JSONSerializer


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


class BrokenVoicesEngine(FakeEngine):
    def getProperty(self, name: str) -> object:
        if name == "voices":
            raise ValueError("invalid literal for int() with base 16: '804;4;7804'")
        return super().getProperty(name)


class FakeSapiToken:
    def __init__(self, voice_id: str, description: str) -> None:
        self.Id = voice_id
        self._description = description

    def GetDescription(self) -> str:
        return self._description


class BrokenVoicesEngineWithSapiFallback(BrokenVoicesEngine):
    def __init__(self) -> None:
        super().__init__()

        class FakeTts:
            @staticmethod
            def GetVoices():
                return (
                    FakeSapiToken("HKEY_FAKE_1", "Voice One"),
                    FakeSapiToken("HKEY_FAKE_2", "Voice Two"),
                )

        class FakeDriver:
            _tts = FakeTts()

        class FakeProxy:
            _driver = FakeDriver()

        self.proxy = FakeProxy()


class NoPitchEngine(FakeEngine):
    def setProperty(self, name: str, value: object) -> None:
        if name == "pitch":
            raise RuntimeError("pitch unsupported")
        super().setProperty(name, value)


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


class FakeClipboard:
    def __init__(self) -> None:
        self.text = ""

    def set_text(self, text: str) -> None:
        self.text = text

    def get_text(self) -> str:
        return self.text


class FakeNvdaController:
    def __init__(self) -> None:
        self.speak_ssml_calls: list[tuple[str, int, int, bool]] = []

    def nvdaController_speakSsml(
        self,
        ssml: str,
        symbol_level: int,
        priority: int,
        asynchronous: bool,
    ) -> int:
        self.speak_ssml_calls.append((ssml, symbol_level, priority, asynchronous))
        return 0


class LegacyOnlyNvdaController:
    def __init__(self) -> None:
        self.speak_text_calls: list[str] = []

    def nvdaController_speakText(self, text: str) -> int:
        self.speak_text_calls.append(text)
        return 0


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


def test_raw_json_speak_payload_reaches_real_pyttsx3_sequence_path():
    serializer = JSONSerializer()
    engine = FakeEngine()
    task_manager = FakeTaskManager()
    output = Pyttsx3SpeechOutput(engine=engine, task_manager=task_manager)
    manager = OutputManager(speech_output=output, clipboard=FakeClipboard())
    router = MessageRouter(
        on_speech=manager.handle_speech,
        on_cancel=manager.handle_cancel,
        on_pause=manager.handle_pause,
        on_clipboard=manager.handle_clipboard,
        on_status=lambda event: None,
    )
    payload = serializer.deserialize(
        b'{"type":"speak","sequence":["hello",["BreakCommand",{"time":10}],["PitchCommand",{"offset":2}],"world"]}'
    )

    router.handle_message(payload)

    assert task_manager.calls == [
        ("speak", "hello"),
        ("break", 0.01),
        ("speak", "world"),
    ]
    assert engine.say_calls == ["hello", "world"]
    assert engine.properties["pitch"] == 2


def test_raw_json_speak_payload_reaches_real_nvda_controller_sequence_path():
    serializer = JSONSerializer()
    controller = FakeNvdaController()
    output = NvdaControllerSpeechOutput(controller=controller)
    manager = OutputManager(speech_output=output, clipboard=FakeClipboard())
    router = MessageRouter(
        on_speech=manager.handle_speech,
        on_cancel=manager.handle_cancel,
        on_pause=manager.handle_pause,
        on_clipboard=manager.handle_clipboard,
        on_status=lambda event: None,
    )
    payload = serializer.deserialize(
        b'{"type":"speak","sequence":["hello",["PitchCommand",{"offset":20}],"W"]}'
    )

    router.handle_message(payload)

    assert controller.speak_ssml_calls == [
        ("<speak>hello<prosody pitch=\"120%\">W</prosody></speak>", 0, 0, True)
    ]


def test_nvda_controller_backend_logs_received_speech_sequence(caplog):
    controller = FakeNvdaController()
    output = NvdaControllerSpeechOutput(controller=controller)

    with caplog.at_level("DEBUG"):
        output.speak(SpeechSequence(items=("hello", PitchCommand(offset=20), "W")))

    assert "NVDA controller received speech sequence" in caplog.text
    assert "PitchCommand" in caplog.text


def test_nvda_controller_backend_converts_text_to_ssml_and_escapes_content():
    controller = FakeNvdaController()
    output = NvdaControllerSpeechOutput(controller=controller)

    output.speak(SpeechSequence(items=("hello", ' <tag attr="1"> & ', "world")))

    assert controller.speak_ssml_calls == [
        ("<speak>hello &lt;tag attr=&quot;1&quot;&gt; &amp; world</speak>", 0, 0, True)
    ]


def test_nvda_controller_backend_maps_breaks_and_ignores_unsupported_commands():
    controller = FakeNvdaController()
    output = NvdaControllerSpeechOutput(controller=controller)
    sequence = SpeechSequence(
        items=("hello", BreakCommand(time=50), SpeechCommand(kind="Unknown"), "world")
    )

    output.speak(sequence)

    assert controller.speak_ssml_calls == [
        ("<speak>hello<break time=\"50ms\"/>world</speak>", 0, 0, True)
    ]


def test_nvda_controller_backend_maps_prosody_commands_into_nested_ssml():
    controller = FakeNvdaController()
    output = NvdaControllerSpeechOutput(controller=controller)
    sequence = SpeechSequence(
        items=(
            PitchCommand(multiplier=1.2),
            RateCommand(offset=10),
            VolumeCommand(multiplier=0.8),
            "hello",
        )
    )

    output.speak(sequence)

    assert controller.speak_ssml_calls == [
        (
            '<speak><prosody pitch="120%"><prosody rate="110%"><prosody volume="80%">hello'
            "</prosody></prosody></prosody></speak>",
            0,
            0,
            True,
        )
    ]


def test_nvda_controller_backend_uses_local_state_as_offset_baseline():
    controller = FakeNvdaController()
    output = NvdaControllerSpeechOutput(controller=controller)
    output.set_rate(80)
    output.set_pitch(90)
    output.set_volume(70)

    output.speak(
        SpeechSequence(
            items=(
                RateCommand(offset=20),
                PitchCommand(offset=10),
                VolumeCommand(offset=14),
                "hello",
            )
        )
    )

    assert output.get_rate() == 80
    assert output.get_pitch() == 90
    assert output.get_volume() == 70
    assert controller.speak_ssml_calls == [
        (
            '<speak><prosody rate="125%"><prosody pitch="111%"><prosody volume="120%">hello'
            "</prosody></prosody></prosody></speak>",
            0,
            0,
            True,
        )
    ]


def test_nvda_controller_backend_skips_empty_ssml_output():
    controller = FakeNvdaController()
    output = NvdaControllerSpeechOutput(controller=controller)

    output.speak(SpeechSequence(items=()))
    output.speak(SpeechSequence(items=(SpeechCommand(kind="Unknown"),)))

    assert controller.speak_ssml_calls == []


def test_nvda_controller_backend_does_not_fallback_to_legacy_speak_text():
    controller = LegacyOnlyNvdaController()
    output = NvdaControllerSpeechOutput(controller=controller)

    assert output.available is False
    output.speak(SpeechSequence(items=("hello",)))

    assert controller.speak_text_calls == []


def test_nvda_controller_backend_marks_controller_without_speak_ssml_unavailable():
    output = NvdaControllerSpeechOutput(controller=LegacyOnlyNvdaController())

    assert output.available is False


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
    assert engine.properties["pitch"] == 3


def test_pyttsx3_backend_ignores_unsupported_pitch_property():
    engine = NoPitchEngine()
    task_manager = FakeTaskManager()
    output = Pyttsx3SpeechOutput(engine=engine, task_manager=task_manager)
    sequence = SpeechSequence(items=(PitchCommand(offset=7), "hello"))

    output.speak(sequence)

    assert engine.say_calls == ["hello"]
    assert "pitch" not in engine.properties


def test_pyttsx3_backend_gracefully_handles_voice_enumeration_failure():
    engine = BrokenVoicesEngine()
    output = Pyttsx3SpeechOutput(engine=engine, task_manager=FakeTaskManager())

    assert output.list_voices() == ()


def test_pyttsx3_backend_falls_back_to_raw_sapi_tokens_for_voices():
    engine = BrokenVoicesEngineWithSapiFallback()
    output = Pyttsx3SpeechOutput(engine=engine, task_manager=FakeTaskManager())

    assert output.list_voices() == (
        ("HKEY_FAKE_1", "Voice One"),
        ("HKEY_FAKE_2", "Voice Two"),
    )


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
