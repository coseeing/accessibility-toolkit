import logging

from application.output import Capabilities, QueuedService, Scheduler
from application.output.speech import SpeechBackendOption, SpeechService
import bootstrap.output as bootstrap_output
from bootstrap.output import build_output_services


class FakeSpeechOutput:
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


def backend_options_factory(scheduler):
    assert isinstance(scheduler, Scheduler)
    return (
        SpeechBackendOption("primary", "Primary", lambda: FakeSpeechOutput()),
        SpeechBackendOption("fallback", "Fallback", lambda: FakeSpeechOutput()),
    )


def test_build_output_services_wires_scheduler_speech_speaker_and_capabilities():
    services = build_output_services(
        backend_options_factory=backend_options_factory,
        selected_backend_id="primary",
    )
    try:
        assert isinstance(services.scheduler, Scheduler)
        assert isinstance(services.speech, SpeechService)
        assert isinstance(services.speaker, QueuedService)
        assert isinstance(services.capabilities, Capabilities)
        assert services.speaker.get_selected_backend() == "primary"
        assert services.capabilities.speech is services.speaker
        assert services.capabilities.tone is None
    finally:
        services.speaker.shutdown()


def test_build_output_services_includes_tone_capability():
    tone_output = object()

    services = build_output_services(
        backend_options_factory=backend_options_factory,
        selected_backend_id="primary",
        tone_output=tone_output,
    )
    try:
        assert services.capabilities.tone is tone_output
    finally:
        services.speaker.shutdown()


def test_build_output_services_falls_back_and_persists_backend(caplog):
    persisted = []

    with caplog.at_level(logging.WARNING):
        services = build_output_services(
            backend_options_factory=backend_options_factory,
            selected_backend_id="missing",
            fallback_backend_id="fallback",
            on_backend_fallback=persisted.append,
        )
    try:
        assert services.speaker.get_selected_backend() == "fallback"
        assert persisted == ["fallback"]
        assert "Unknown configured speech backend" in caplog.text
    finally:
        services.speaker.shutdown()


def test_build_output_services_shuts_down_scheduler_when_options_factory_raises(monkeypatch):
    class FakeScheduler:
        instances = []

        def __init__(self):
            self.shutdown_calls = 0
            type(self).instances.append(self)

        def shutdown(self):
            self.shutdown_calls += 1

    monkeypatch.setattr(bootstrap_output, "Scheduler", FakeScheduler)

    def raise_options(scheduler):
        assert isinstance(scheduler, FakeScheduler)
        raise RuntimeError("options failed")

    try:
        build_output_services(
            backend_options_factory=raise_options,
            selected_backend_id="primary",
        )
    except RuntimeError as error:
        assert str(error) == "options failed"
    else:
        raise AssertionError("expected RuntimeError")

    assert FakeScheduler.instances[0].shutdown_calls == 1


def test_build_output_services_shuts_down_scheduler_when_fallback_callback_raises(
    monkeypatch,
):
    class FakeScheduler:
        instances = []

        def __init__(self):
            self.shutdown_calls = 0
            type(self).instances.append(self)

        def shutdown(self):
            self.shutdown_calls += 1

    monkeypatch.setattr(bootstrap_output, "Scheduler", FakeScheduler)

    def raise_fallback(backend_id):
        assert backend_id == "fallback"
        raise RuntimeError("persist failed")

    try:
        build_output_services(
            backend_options_factory=lambda scheduler: (
                SpeechBackendOption(
                    "fallback",
                    "Fallback",
                    lambda: FakeSpeechOutput(),
                ),
            ),
            selected_backend_id="missing",
            fallback_backend_id="fallback",
            on_backend_fallback=raise_fallback,
        )
    except RuntimeError as error:
        assert str(error) == "persist failed"
    else:
        raise AssertionError("expected RuntimeError")

    assert FakeScheduler.instances[0].shutdown_calls == 1
