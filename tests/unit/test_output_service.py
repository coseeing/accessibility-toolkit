from application.output import QueuedService
from application.output import Scheduler
from application.output.speech import SpeechBackendOption
from application.output.speech import SpeechService
from interop.speech.speech_sequence import SpeechSequence


class FakeSpeechOutput:
    def __init__(self, name: str) -> None:
        self.name = name
        self.spoken: list[SpeechSequence] = []
        self.cancelled = 0
        self.paused: list[bool] = []
        self.voice: str | None = None
        self.rate: int | None = None
        self.pitch: int | None = None
        self.volume: int | None = None

    def speak(self, sequence: SpeechSequence) -> None:
        self.spoken.append(sequence)

    def cancel(self) -> None:
        self.cancelled += 1

    def pause(self, is_paused: bool) -> None:
        self.paused.append(is_paused)

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return (("voice-1", "Voice 1"),)

    def get_voice(self) -> str | None:
        return self.voice

    def set_voice(self, voice_id: str) -> None:
        self.voice = voice_id

    def get_rate(self) -> int | None:
        return self.rate

    def set_rate(self, value: int) -> None:
        self.rate = value

    def get_pitch(self) -> int | None:
        return self.pitch

    def set_pitch(self, value: int) -> None:
        self.pitch = value

    def get_volume(self) -> int | None:
        return self.volume

    def set_volume(self, value: int) -> None:
        self.volume = value


class SchedulerBackedFakeOutput(FakeSpeechOutput):
    """Mimics real backends (pyttsx3/nvda_controller) that schedule speak
    work into their own Scheduler instead of recording synchronously."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.scheduler = Scheduler()

    def speak(self, sequence: SpeechSequence) -> None:
        self.scheduler.schedule(self, lambda seq=sequence: self.spoken.append(seq))

    def cancel(self) -> None:
        self.scheduler.cancel_all()
        super().cancel()


def build_service() -> tuple[QueuedService, list[FakeSpeechOutput], Scheduler]:
    created: list[FakeSpeechOutput] = []

    def factory(name: str):
        def create() -> FakeSpeechOutput:
            output = FakeSpeechOutput(name)
            created.append(output)
            return output

        return create

    scheduler = Scheduler()
    speech = SpeechService(
        backend_options=(
            SpeechBackendOption(
                backend_id="nvda_controller",
                label="NVDA Controller",
                factory=factory("nvda_controller"),
            ),
            SpeechBackendOption(
                backend_id="pyttsx3",
                label="pyttsx3",
                factory=factory("pyttsx3"),
            ),
        ),
        selected_backend_id="nvda_controller",
        scheduler=scheduler,
    )
    return QueuedService(speech=speech), created, scheduler


def build_scheduler_backed_service() -> tuple[QueuedService, list[SchedulerBackedFakeOutput], Scheduler]:
    created: list[SchedulerBackedFakeOutput] = []

    def factory(name: str):
        def create() -> SchedulerBackedFakeOutput:
            output = SchedulerBackedFakeOutput(name)
            created.append(output)
            return output

        return create

    scheduler = Scheduler()
    speech = SpeechService(
        backend_options=(
            SpeechBackendOption(
                backend_id="nvda_controller",
                label="NVDA Controller",
                factory=factory("nvda_controller"),
            ),
            SpeechBackendOption(
                backend_id="pyttsx3",
                label="pyttsx3",
                factory=factory("pyttsx3"),
            ),
        ),
        selected_backend_id="nvda_controller",
        scheduler=scheduler,
    )
    return QueuedService(speech=speech), created, scheduler


def test_queued_output_service_proxies_speech_calls() -> None:
    service, created, _scheduler = build_service()

    speech = SpeechSequence(items=("hello",))
    service.speak(speech)
    service.pause(True)
    service.cancel()

    assert created[0].spoken == [speech]
    assert created[0].paused == [True]
    assert created[0].cancelled == 1
    service.shutdown()


def test_output_package_re_exports_core_types() -> None:
    from application.output import (
        Capabilities,
        EventCallbacks,
        Manager,
        Mode,
        QueuedService,
        ScheduledFuture,
        Scheduler,
    )
    from application.output.manager import ClipboardService
    from application.output.speech import (
        SpeechBackendManager,
        SpeechBackendOption,
        SpeechService,
    )
    from application.output import SpeechServiceProtocol

    assert Capabilities is not None
    assert EventCallbacks is not None
    assert Manager is not None
    assert ClipboardService is not None
    assert Mode is not None
    assert QueuedService is not None
    assert ScheduledFuture is not None
    assert Scheduler is not None
    assert SpeechBackendManager is not None
    assert SpeechBackendOption is not None
    assert SpeechService is not None
    assert SpeechServiceProtocol is not None


def test_queued_output_service_switches_backend_via_speech_service() -> None:
    service, created, _scheduler = build_service()

    service.set_backend("pyttsx3")
    service.speak(SpeechSequence(items=("next",)))

    assert created[0].cancelled == 1
    assert created[1].spoken == [SpeechSequence(items=("next",))]
    assert service.get_selected_backend() == "pyttsx3"
    service.shutdown()


def test_queued_output_service_proxies_configuration_calls() -> None:
    service, created, _scheduler = build_service()

    service.set_voice("voice-1")
    service.set_rate(120)
    service.set_pitch(4)
    service.set_volume(80)

    assert service.list_voices() == (("voice-1", "Voice 1"),)
    assert service.get_voice() == "voice-1"
    assert service.get_rate() == 120
    assert service.get_pitch() == 4
    assert service.get_volume() == 80
    assert created[0].voice == "voice-1"
    service.shutdown()


import threading

from application.output import Mode


def test_output_mode_enum_values() -> None:
    assert Mode.SEQUENTIAL.value == "sequential"
    assert Mode.PARALLEL.value == "parallel"


def test_default_mode_is_parallel() -> None:
    service, _created, _scheduler = build_service()
    assert service.get_mode() == Mode.PARALLEL


def test_set_and_get_mode() -> None:
    service, _created, _scheduler = build_service()

    service.set_mode(Mode.SEQUENTIAL)
    assert service.get_mode() == Mode.SEQUENTIAL

    service.set_mode(Mode.PARALLEL)
    assert service.get_mode() == Mode.PARALLEL


def test_sequential_orders_consecutive_speak_calls() -> None:
    service, created, _scheduler = build_service()
    service.set_mode(Mode.SEQUENTIAL)

    seq_a = SpeechSequence(items=("a",))
    seq_b = SpeechSequence(items=("b",))
    service.speak(seq_a)
    service.speak(seq_b)

    sentinel = service._shared_scheduler.schedule(service, lambda: None)
    sentinel.result(timeout=2)

    assert created[0].spoken == [seq_a, seq_b]


def test_cancel_in_sequential_clears_shared_queue() -> None:
    service, created, _scheduler = build_service()
    service.set_mode(Mode.SEQUENTIAL)

    seq_a = SpeechSequence(items=("a",))
    seq_b = SpeechSequence(items=("b",))

    service.speak(seq_a)
    sentinel = service._shared_scheduler.schedule(service, lambda: None)
    sentinel.result(timeout=2)

    service.speak(seq_b)
    service.cancel()

    sentinel2 = service._shared_scheduler.schedule(service, lambda: None)
    sentinel2.result(timeout=2)

    assert created[0].spoken == [seq_a]


def test_shutdown_stops_shared_scheduler() -> None:
    service, _created, _scheduler = build_service()
    service.set_mode(Mode.SEQUENTIAL)

    seq = SpeechSequence(items=("x",))
    service.speak(seq)
    sentinel = service._shared_scheduler.schedule(service, lambda: None)
    sentinel.result(timeout=2)

    service.shutdown()

    assert not service._shared_scheduler._thread.is_alive()


def test_parallel_mode_is_backward_compatible() -> None:
    service, created, _scheduler = build_service()

    speech = SpeechSequence(items=("hello",))
    service.speak(speech)
    service.pause(True)
    service.cancel()

    assert created[0].spoken == [speech]
    assert created[0].paused == [True]
    assert created[0].cancelled == 1
    service.shutdown()


def test_sequential_orders_consecutive_speak_calls_with_async_backend() -> None:
    """Sequential ordering holds when backend speak() schedules
    asynchronously into its own Scheduler, matching the
    real pyttsx3/nvda_controller pattern."""
    service, created, _scheduler = build_scheduler_backed_service()
    service.set_mode(Mode.SEQUENTIAL)

    seq_a = SpeechSequence(items=("a",))
    seq_b = SpeechSequence(items=("b",))
    service.speak(seq_a)
    service.speak(seq_b)

    # Wait for shared_scheduler to drain
    sentinel = service._shared_scheduler.schedule(service, lambda: None)
    sentinel.result(timeout=2)

    # Wait for backend scheduler to drain
    backend_sentinel = created[0].scheduler.schedule(service, lambda: None)
    backend_sentinel.result(timeout=2)

    assert created[0].spoken == [seq_a, seq_b]
    created[0].scheduler.shutdown()
    service.shutdown()
