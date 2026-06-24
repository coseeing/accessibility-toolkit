import json
import threading
import time

import pytest

from adapters.outputs.drivers.pyttsx3 import Pyttsx3SpeechOutput
from application.config import SpeechEngineConfigStore
from application.output import Manager
from application.output.speech import (
    SpeechEngineManager,
    SpeechEngineOption,
    SpeechNumericSetting,
)
from application.output.speech.settings import (
    clamp_percent,
    percent_to_range,
    range_to_percent,
)
from adapters.windows.nvda_controller import NvdaControllerSpeechOutput
from interop.speech.speech_commands import (
    BreakCommand,
    PitchCommand,
    RateCommand,
    SpeechCommand,
    VolumeCommand,
)
from interop.speech.speech_sequence import SpeechSequence
from interop.protocol.routing.message_router import MessageRouter
from interop.protocol.serializer import JSONSerializer


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

    def get_supported_numeric_settings(self) -> tuple[SpeechNumericSetting, ...]:
        return ()


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


class SameThreadStopEngine:
    def __init__(self) -> None:
        self.say_calls: list[str] = []
        self.started = threading.Event()
        self.finished = threading.Event()
        self.stop_count = 0
        self.properties: dict[str, object] = {}
        self._speech_thread_id: int | None = None
        self._stopped = False

    def say(self, text: str) -> None:
        self.say_calls.append(text)

    def setProperty(self, name: str, value: object) -> None:
        self.properties[name] = value

    def getProperty(self, name: str) -> object:
        return self.properties.get(name, [])

    def startLoop(self, useDriverLoop: bool = True) -> None:
        return None

    def iterate(self) -> None:
        self.started.set()
        if self._speech_thread_id is None:
            self._speech_thread_id = threading.get_ident()
        if self._stopped:
            self.finished.set()
            return
        time.sleep(0.01)

    def isBusy(self) -> bool:
        return not self._stopped

    def endLoop(self) -> None:
        return None

    def runAndWait(self) -> None:
        self.started.set()
        if self._speech_thread_id is None:
            self._speech_thread_id = threading.get_ident()
        deadline = time.time() + 0.5
        while time.time() < deadline:
            if self._stopped:
                self.finished.set()
                return
            time.sleep(0.01)

    def stop(self) -> None:
        self.stop_count += 1
        if self._speech_thread_id == threading.get_ident():
            self._stopped = True


class BusyLoopEngine:
    def __init__(self) -> None:
        self.say_calls: list[str] = []
        self.finished = threading.Event()
        self.properties: dict[str, object] = {}
        self._loop_started = False
        self._busy_cycles_remaining = 3
        self.iterate_calls = 0

    def say(self, text: str) -> None:
        self.say_calls.append(text)
        self._busy_cycles_remaining = 3
        self.finished.clear()

    def setProperty(self, name: str, value: object) -> None:
        self.properties[name] = value

    def getProperty(self, name: str) -> object:
        return self.properties.get(name, [])

    def startLoop(self, useDriverLoop: bool = True) -> None:
        self._loop_started = True

    def iterate(self) -> None:
        self.iterate_calls += 1
        time.sleep(0.005)
        if self._busy_cycles_remaining > 0:
            self._busy_cycles_remaining -= 1
        if self._busy_cycles_remaining == 0:
            self.finished.set()

    def isBusy(self) -> bool:
        return self._busy_cycles_remaining > 0

    def endLoop(self) -> None:
        self._loop_started = False

    def stop(self) -> None:
        self._busy_cycles_remaining = 0
        self.finished.set()


class RestartableBusyLoopEngine:
    def __init__(self) -> None:
        self.say_calls: list[str] = []
        self.finished_events: list[threading.Event] = []
        self.properties: dict[str, object] = {}
        self._busy_cycles_remaining = 0
        self._current_finished: threading.Event | None = None
        self.iterate_calls = 0

    def say(self, text: str) -> None:
        self.say_calls.append(text)
        self._busy_cycles_remaining = 3
        self._current_finished = threading.Event()
        self.finished_events.append(self._current_finished)

    def setProperty(self, name: str, value: object) -> None:
        self.properties[name] = value

    def getProperty(self, name: str) -> object:
        return self.properties.get(name, [])

    def startLoop(self, useDriverLoop: bool = True) -> None:
        return None

    def iterate(self) -> None:
        self.iterate_calls += 1
        time.sleep(0.005)
        if self._busy_cycles_remaining > 0:
            self._busy_cycles_remaining -= 1
        if self._busy_cycles_remaining == 0 and self._current_finished is not None:
            self._current_finished.set()

    def isBusy(self) -> bool:
        return self._busy_cycles_remaining > 0

    def endLoop(self) -> None:
        return None

    def stop(self) -> None:
        self._busy_cycles_remaining = 0
        if self._current_finished is not None:
            self._current_finished.set()


class InterruptibleSequenceEngine:
    def __init__(self) -> None:
        self.say_calls: list[str] = []
        self.started_events: list[threading.Event] = []
        self.finished_events: list[threading.Event] = []
        self.properties: dict[str, object] = {}
        self._busy_cycles_remaining = 0
        self._current_started: threading.Event | None = None
        self._current_finished: threading.Event | None = None

    def say(self, text: str) -> None:
        self.say_calls.append(text)
        self._busy_cycles_remaining = 20
        self._current_started = threading.Event()
        self._current_finished = threading.Event()
        self.started_events.append(self._current_started)
        self.finished_events.append(self._current_finished)

    def setProperty(self, name: str, value: object) -> None:
        self.properties[name] = value

    def getProperty(self, name: str) -> object:
        return self.properties.get(name, [])

    def startLoop(self, useDriverLoop: bool = True) -> None:
        return None

    def iterate(self) -> None:
        if self._current_started is not None:
            self._current_started.set()
        time.sleep(0.005)
        if self._busy_cycles_remaining > 0:
            self._busy_cycles_remaining -= 1
        if self._busy_cycles_remaining == 0 and self._current_finished is not None:
            self._current_finished.set()

    def isBusy(self) -> bool:
        return self._busy_cycles_remaining > 0

    def endLoop(self) -> None:
        return None

    def stop(self) -> None:
        self._busy_cycles_remaining = 0
        if self._current_finished is not None:
            self._current_finished.set()


class Sapi5ExternalLoopRegressionEngine:
    def __init__(self) -> None:
        self.driver_name = "sapi5"
        self.say_calls: list[str] = []
        self.spoken_texts: list[str] = []
        self.finished_events: list[threading.Event] = []
        self.started_events: list[threading.Event] = []
        self.properties: dict[str, object] = {}
        self._pending_text: str | None = None
        self._busy = False
        self._stopped_once = False
        self._current_started: threading.Event | None = None
        self._current_finished: threading.Event | None = None

    def say(self, text: str) -> None:
        self.say_calls.append(text)
        self._pending_text = text
        self._busy = True
        self._current_started = threading.Event()
        self._current_finished = threading.Event()
        self.started_events.append(self._current_started)
        self.finished_events.append(self._current_finished)

    def setProperty(self, name: str, value: object) -> None:
        self.properties[name] = value

    def getProperty(self, name: str) -> object:
        return self.properties.get(name, [])

    def startLoop(self, useDriverLoop: bool = True) -> None:
        return None

    def iterate(self) -> None:
        if self._current_started is not None:
            self._current_started.set()
        time.sleep(0.005)
        if self._pending_text is None:
            self._busy = False
        elif self._stopped_once:
            # Mimics the upstream external-loop interruption bug on SAPI5:
            # after a stop, the next utterance never actually starts speaking.
            self._pending_text = None
            self._busy = False
        else:
            if not self.spoken_texts or self.spoken_texts[-1] != self._pending_text:
                self.spoken_texts.append(self._pending_text)

    def isBusy(self) -> bool:
        return self._busy

    def endLoop(self) -> None:
        if self._current_finished is not None:
            self._current_finished.set()

    def runAndWait(self) -> None:
        if self._current_started is not None:
            self._current_started.set()
        time.sleep(0.005)
        if self._pending_text is not None:
            self.spoken_texts.append(self._pending_text)
            self._pending_text = None
        self._busy = False
        if self._current_finished is not None:
            self._current_finished.set()

    def stop(self) -> None:
        self._stopped_once = True
        self._pending_text = None
        self._busy = False
        if self._current_finished is not None:
            self._current_finished.set()


class NsssLoopEngine(BusyLoopEngine):
    def __init__(self) -> None:
        super().__init__()
        self.driver_name = "nsss"


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

    def notify_done(self) -> None:
        pass

    def cancel_all(self) -> None:
        self.calls.append(("cancel_all", None))


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


def test_speech_numeric_setting_defaults_to_zero_to_one_hundred_percent():
    setting = SpeechNumericSetting(id="rate", label="Rate")

    assert setting.id == "rate"
    assert setting.label == "Rate"
    assert setting.default_percent == 50
    assert setting.min_percent == 0
    assert setting.max_percent == 100
    assert setting.step == 1
    assert setting.large_step == 10


def test_percent_helpers_clamp_and_map_ranges():
    assert clamp_percent(-1) == 0
    assert clamp_percent(0) == 0
    assert clamp_percent(50) == 50
    assert clamp_percent(100) == 100
    assert clamp_percent(101) == 100
    assert percent_to_range(50, 50, 300) == 175
    assert percent_to_range(0, 50, 300) == 50
    assert percent_to_range(100, 50, 300) == 300
    assert range_to_percent(175, 50, 300) == 50


def test_percent_to_range_returns_float_and_range_to_percent_returns_int():
    assert isinstance(percent_to_range(50, 50, 300), float)
    assert percent_to_range(50, 50.0, 300.0) == 175.0
    assert isinstance(range_to_percent(175, 50, 300), int)


def test_range_to_percent_handles_degenerate_range():
    assert range_to_percent(50, 100, 100) == 0


def test_speech_engine_manager_switches_engine_and_cancels_previous():
    events: list[tuple[str, str]] = []
    manager = SpeechEngineManager(
        engine_options=(
            SpeechEngineOption(
                engine_id="NvdaController",
                label="Nvda Controller",
                factory=lambda: FakeSpeechOutput("NvdaController", events),
            ),
            SpeechEngineOption(
                engine_id="Pyttsx3",
                label="Pyttsx3",
                factory=lambda: FakeSpeechOutput("Pyttsx3", events),
            ),
        ),
        selected_engine_id="NvdaController",
    )

    previous = manager.current_output
    manager.set_engine("Pyttsx3")

    assert previous is not manager.current_output
    assert manager.selected_engine_id == "Pyttsx3"
    assert manager.engine_choices() == (
        ("NvdaController", "Nvda Controller"),
        ("Pyttsx3", "Pyttsx3"),
    )
    assert events == [("cancel", "NvdaController")]


def test_speech_engine_manager_rejects_unknown_engine():
    manager = SpeechEngineManager(
        engine_options=(
            SpeechEngineOption(
                engine_id="NvdaController",
                label="Nvda Controller",
                factory=lambda: FakeSpeechOutput("NvdaController", []),
            ),
        ),
        selected_engine_id="NvdaController",
    )

    with pytest.raises(ValueError, match="Unknown speech engine"):
        manager.set_engine("Pyttsx3")


def test_speech_engine_manager_keeps_current_engine_on_factory_failure():
    events: list[tuple[str, str]] = []
    current = FakeSpeechOutput("NvdaController", events)

    class FactoryError(RuntimeError):
        pass

    def failing_factory() -> FakeSpeechOutput:
        raise FactoryError("engine unavailable")

    manager = SpeechEngineManager(
        engine_options=(
            SpeechEngineOption(
                engine_id="NvdaController",
                label="Nvda Controller",
                factory=lambda: current,
            ),
            SpeechEngineOption(
                engine_id="Pyttsx3",
                label="Pyttsx3",
                factory=failing_factory,
            ),
        ),
        selected_engine_id="NvdaController",
    )

    previous_output = manager.current_output
    with pytest.raises(FactoryError, match="engine unavailable"):
        manager.set_engine("Pyttsx3")

    assert manager.current_output is previous_output
    assert manager.selected_engine_id == "NvdaController"
    assert events == []  # previous engine must not be canceled on failure


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
    manager = Manager(speech_output=output, clipboard=FakeClipboard())
    router = MessageRouter(
        on_speech=manager.handle_speech,
        on_cancel=manager.handle_cancel,
        on_pause=manager.handle_pause,
        on_clipboard=manager.handle_clipboard,
        on_tone=lambda hz, length, left, right: None,
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
    assert engine.properties["pitch"] == 52


def test_raw_json_speak_payload_reaches_real_nvda_controller_sequence_path():
    serializer = JSONSerializer()
    controller = FakeNvdaController()
    output = NvdaControllerSpeechOutput(controller=controller)
    manager = Manager(speech_output=output, clipboard=FakeClipboard())
    router = MessageRouter(
        on_speech=manager.handle_speech,
        on_cancel=manager.handle_cancel,
        on_pause=manager.handle_pause,
        on_clipboard=manager.handle_clipboard,
        on_tone=lambda hz, length, left, right: None,
        on_status=lambda event: None,
    )
    payload = serializer.deserialize(
        b'{"type":"speak","sequence":["hello",["PitchCommand",{"offset":20}],"W"]}'
    )

    router.handle_message(payload)

    assert controller.speak_ssml_calls == [
        ("<speak>hello<prosody pitch=\"140%\">W</prosody></speak>", 0, 0, True)
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
            '<speak><prosody pitch="120%"><prosody rate="120%"><prosody volume="80%">hello'
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


def test_nvda_controller_backend_declares_supported_numeric_settings():
    output = NvdaControllerSpeechOutput(controller=FakeNvdaController())

    settings = {setting.id: setting for setting in output.get_supported_numeric_settings()}

    assert tuple(settings) == ("rate", "pitch", "volume")
    assert output.get_rate() == 50
    assert output.get_pitch() == 50
    assert output.get_volume() == 50


def test_nvda_controller_backend_uses_normalized_baseline_for_offsets():
    controller = FakeNvdaController()
    output = NvdaControllerSpeechOutput(controller=controller)
    output.set_rate(80)
    output.set_pitch(40)
    output.set_volume(60)

    output.speak(
        SpeechSequence(
            items=(
                RateCommand(offset=20),
                PitchCommand(offset=10),
                VolumeCommand(offset=30),
                "hello",
            )
        )
    )

    assert controller.speak_ssml_calls == [
        (
            '<speak><prosody rate="125%"><prosody pitch="125%"><prosody volume="150%">hello'
            "</prosody></prosody></prosody></speak>",
            0,
            0,
            True,
        )
    ]


def test_nvda_controller_backend_applies_normalized_baseline_to_plain_speech():
    controller = FakeNvdaController()
    output = NvdaControllerSpeechOutput(controller=controller)
    output.set_rate(80)
    output.set_pitch(40)
    output.set_volume(60)

    output.speak(SpeechSequence(items=("hello",)))

    assert controller.speak_ssml_calls == [
        (
            '<speak><prosody rate="160%"><prosody pitch="80%"><prosody volume="120%">hello'
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

    assert output.get_pitch() == 53
    assert output.get_rate() == 60
    assert output.get_volume() == 40
    assert engine.properties["pitch"] == 53


def test_pyttsx3_backend_declares_supported_numeric_settings():
    output = Pyttsx3SpeechOutput(engine=FakeEngine(), task_manager=FakeTaskManager())

    settings = {setting.id: setting for setting in output.get_supported_numeric_settings()}

    assert tuple(settings) == ("rate", "pitch", "volume")
    assert settings["rate"].label == "Rate"
    assert settings["pitch"].label == "Pitch"
    assert settings["volume"].label == "Volume"
    assert output.get_rate() == 50
    assert output.get_pitch() == 50
    assert output.get_volume() == 50


def test_pyttsx3_backend_maps_normalized_values_to_engine_properties():
    engine = FakeEngine()
    output = Pyttsx3SpeechOutput(engine=engine, task_manager=FakeTaskManager())

    output.set_rate(100)
    output.set_pitch(80)
    output.set_volume(25)
    output.speak(SpeechSequence(items=("hello",)))

    assert engine.properties["rate"] == 300
    assert engine.properties["pitch"] == 80
    assert engine.properties["volume"] == 0.25


def test_pyttsx3_backend_clamps_normalized_values():
    output = Pyttsx3SpeechOutput(engine=FakeEngine(), task_manager=FakeTaskManager())

    output.set_rate(999)
    output.set_pitch(-1)
    output.set_volume(150)

    assert output.get_rate() == 100
    assert output.get_pitch() == 0
    assert output.get_volume() == 100


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


def test_pyttsx3_backend_warns_without_traceback_when_voice_enumeration_fails(caplog):
    engine = BrokenVoicesEngine()
    output = Pyttsx3SpeechOutput(engine=engine, task_manager=FakeTaskManager())

    with caplog.at_level("WARNING"):
        assert output.list_voices() == ()

    assert "no fallback voices were available" in caplog.text
    assert "Traceback" not in caplog.text


def test_pyttsx3_backend_falls_back_to_raw_sapi_tokens_for_voices(caplog):
    engine = BrokenVoicesEngineWithSapiFallback()
    output = Pyttsx3SpeechOutput(engine=engine, task_manager=FakeTaskManager())

    with caplog.at_level("WARNING"):
        assert output.list_voices() == (
            ("HKEY_FAKE_1", "Voice One"),
            ("HKEY_FAKE_2", "Voice Two"),
        )

    assert caplog.text == ""


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


def test_pyttsx3_speech_output_cancel_interrupts_when_engine_requires_same_thread_stop():
    engine = SameThreadStopEngine()
    output = Pyttsx3SpeechOutput(engine=engine)
    sequence = SpeechSequence(items=("interrupt me",))

    output.speak(sequence)
    assert engine.started.wait(timeout=0.5)

    output.cancel()

    assert engine.stop_count >= 1
    assert engine.finished.wait(timeout=0.5)


def test_pyttsx3_speech_output_waits_for_busy_loop_completion_before_finishing():
    engine = BusyLoopEngine()
    output = Pyttsx3SpeechOutput(engine=engine)

    output.speak(SpeechSequence(items=("first",)))
    assert engine.finished.wait(timeout=0.5)

    assert engine.iterate_calls >= 3


def test_pyttsx3_speech_output_cancel_then_next_speak_still_runs():
    engine = RestartableBusyLoopEngine()
    output = Pyttsx3SpeechOutput(engine=engine)

    output.speak(SpeechSequence(items=("first",)))
    deadline = time.time() + 0.5
    while len(engine.finished_events) < 1 and time.time() < deadline:
        time.sleep(0.01)
    assert len(engine.finished_events) == 1
    assert engine.finished_events[0].wait(timeout=0.5)

    output.cancel()
    output.speak(SpeechSequence(items=("second",)))

    deadline = time.time() + 0.5
    while len(engine.finished_events) < 2 and time.time() < deadline:
        time.sleep(0.01)
    assert len(engine.finished_events) == 2
    assert engine.finished_events[1].wait(timeout=0.5)
    assert engine.say_calls == ["first", "second"]


def test_pyttsx3_speech_output_repeated_interrupts_still_speak_latest_text():
    engines: list[InterruptibleSequenceEngine] = []

    def engine_factory():
        engine = InterruptibleSequenceEngine()
        engines.append(engine)
        return engine

    output = Pyttsx3SpeechOutput(
        engine_factory=engine_factory,
        recreate_engine_per_utterance=True,
    )

    output.speak(SpeechSequence(items=("first",)))
    deadline = time.time() + 0.5
    while (not engines or len(engines[0].started_events) < 1) and time.time() < deadline:
        time.sleep(0.01)
    assert len(engines) >= 1
    assert len(engines[0].started_events) == 1
    assert engines[0].started_events[0].wait(timeout=0.5)

    output.cancel()
    output.speak(SpeechSequence(items=("second",)))
    deadline = time.time() + 0.5
    while (len(engines) < 2 or len(engines[1].started_events) < 1) and time.time() < deadline:
        time.sleep(0.01)
    assert len(engines) >= 2
    assert len(engines[1].started_events) == 1
    assert engines[1].started_events[0].wait(timeout=0.5)

    output.cancel()
    output.speak(SpeechSequence(items=("third",)))
    deadline = time.time() + 0.5
    while (len(engines) < 3 or len(engines[2].started_events) < 1) and time.time() < deadline:
        time.sleep(0.01)
    assert len(engines) >= 3
    assert len(engines[2].started_events) == 1
    assert engines[2].finished_events[0].wait(timeout=0.5)
    assert [engine.say_calls for engine in engines[:3]] == [["first"], ["second"], ["third"]]


def test_pyttsx3_sapi5_engine_falls_back_to_run_and_wait_after_cancel():
    engine = Sapi5ExternalLoopRegressionEngine()
    output = Pyttsx3SpeechOutput(engine=engine)

    output.speak(SpeechSequence(items=("first",)))
    deadline = time.time() + 0.5
    while len(engine.started_events) < 1 and time.time() < deadline:
        time.sleep(0.01)
    assert len(engine.started_events) == 1
    assert engine.started_events[0].wait(timeout=0.5)

    output.cancel()
    assert engine.finished_events[0].wait(timeout=0.5)

    output.speak(SpeechSequence(items=("second",)))
    deadline = time.time() + 0.5
    while len(engine.finished_events) < 2 and time.time() < deadline:
        time.sleep(0.01)
    assert len(engine.finished_events) == 2
    assert engine.finished_events[1].wait(timeout=0.5)

    assert engine.say_calls == ["first", "second"]
    assert engine.spoken_texts == ["first", "second"]


def test_pyttsx3_driver_execution_strategy_is_explicit_per_driver():
    assert (
        Pyttsx3SpeechOutput._driver_execution_strategy(NsssLoopEngine())
        == "external_loop"
    )
    assert (
        Pyttsx3SpeechOutput._driver_execution_strategy(
            Sapi5ExternalLoopRegressionEngine()
        )
        == "run_and_wait"
    )


def test_speech_engine_config_store_loads_and_saves_engine_id(tmp_path):
    config_path = tmp_path / "client-config.json"
    store = SpeechEngineConfigStore(config_path)

    assert store.load_engine_id(default_engine_id="NvdaController") == "NvdaController"

    store.save_engine_id("Pyttsx3")

    assert json.loads(config_path.read_text(encoding="utf-8")) == {
        "speech_engine": "Pyttsx3"
    }
    assert store.load_engine_id(default_engine_id="NvdaController") == "Pyttsx3"


def test_speech_engine_config_store_persists_settings_per_engine(tmp_path):
    config_path = tmp_path / "client-config.json"
    store = SpeechEngineConfigStore(config_path)

    store.save_voice("NvdaController", "voice-a")
    store.save_numeric_setting("NvdaController", "rate", 120)
    store.save_numeric_setting("Pyttsx3", "rate", -10)

    assert store.load_voice("NvdaController") == "voice-a"
    assert store.load_numeric_setting("NvdaController", "rate") == 100
    assert store.load_numeric_setting("Pyttsx3", "rate") == 0
    assert store.load_numeric_setting("NvdaController", "pitch") is None
    assert json.loads(config_path.read_text(encoding="utf-8")) == {
        "speech_engines": {
            "NvdaController": {
                "voice": "voice-a",
                "rate": 100,
            },
            "Pyttsx3": {
                "rate": 0,
            },
        }
    }


def test_speech_engine_config_store_ignores_bool_numeric_settings(tmp_path):
    config_path = tmp_path / "client-config.json"
    config_path.write_text(
        json.dumps({"speech_engines": {"Pyttsx3": {"rate": True, "pitch": False}}}),
        encoding="utf-8",
    )
    store = SpeechEngineConfigStore(config_path)

    assert store.load_numeric_setting("Pyttsx3", "rate") is None
    assert store.load_numeric_setting("Pyttsx3", "pitch") is None
