from application.config import SpeechEngineConfigStore
from application.output import Scheduler
from application.output.speech import SpeechEngineOption
from apps.shared.speech_runtime_settings import SpeechRuntimeSettingsCoordinator
from bootstrap.app_runtime import build_app_runtime_parts
from interop.key import HID


class FakeCapture:
    running = False


class FakeClipboard:
    def get_text(self):
        return ""

    def set_text(self, text):
        del text


class FakeTone:
    def beep(self, hz, length, left=50, right=50):
        del hz, length, left, right


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


class FakeProvider:
    def __init__(self):
        self.input_capture = FakeCapture()
        self.hotkey_capture = FakeCapture()
        self.clipboard = FakeClipboard()
        self.tone_output = FakeTone()
        self.hotkey_usage = None
        self.scheduler = None
        self.clipboard_calls = 0
        self.input_calls = 0
        self.hotkey_calls = []
        self.tone_calls = 0

    def build_services(self, hotkey_usage):
        self.hotkey_usage = hotkey_usage
        self.input_calls += 1
        self.hotkey_calls.append(hotkey_usage)
        self.clipboard_calls += 1
        self.tone_calls += 1
        return object()

    def create_input_capture(self):
        self.input_calls += 1
        return self.input_capture

    def create_hotkey_capture(self, usage):
        self.hotkey_calls.append(usage)
        return self.hotkey_capture

    def create_clipboard_service(self):
        self.clipboard_calls += 1
        return self.clipboard

    def create_tone_output(self):
        self.tone_calls += 1
        return self.tone_output

    def default_speech_engine_id(self):
        return "default"

    def default_speech_engine_options(self, scheduler):
        assert isinstance(scheduler, Scheduler)
        self.scheduler = scheduler
        return (
            SpeechEngineOption("default", "Default", lambda: FakeSpeechOutput()),
            SpeechEngineOption("selected", "Selected", lambda: FakeSpeechOutput()),
        )


def test_build_app_runtime_parts_wires_platform_and_output_services():
    provider = FakeProvider()

    parts = build_app_runtime_parts(
        provider=provider,
        hotkey_usage=HID.ENTER,
        selected_engine_id="selected",
        include_clipboard=True,
    )
    try:
        assert provider.input_calls == 1
        assert provider.hotkey_calls == [HID.ENTER]
        assert provider.clipboard_calls == 1
        assert provider.tone_calls == 1
        assert parts.input_capture is provider.input_capture
        assert parts.hotkey_capture is provider.hotkey_capture
        assert parts.clipboard is provider.clipboard
        assert parts.tone_output is provider.tone_output
        assert parts.output.scheduler is provider.scheduler
        assert parts.output.speaker.get_selected_engine() == "selected"
        assert parts.output.capabilities.speech is parts.output.speaker
        assert parts.output.capabilities.tone is provider.tone_output
    finally:
        parts.output.speaker.shutdown()


def test_build_app_runtime_parts_uses_default_engine_and_can_exclude_tone():
    provider = FakeProvider()

    parts = build_app_runtime_parts(
        provider=provider,
        hotkey_usage=HID.ENTER,
        include_tone=False,
    )
    try:
        assert provider.input_calls == 1
        assert provider.hotkey_calls == [HID.ENTER]
        assert provider.clipboard_calls == 0
        assert provider.tone_calls == 0
        assert parts.clipboard is None
        assert parts.tone_output is None
        assert parts.output.speaker.get_selected_engine() == "default"
        assert parts.output.capabilities.tone is None
    finally:
        parts.output.speaker.shutdown()


def test_build_app_runtime_parts_can_request_clipboard_without_tone():
    provider = FakeProvider()

    parts = build_app_runtime_parts(
        provider=provider,
        hotkey_usage=HID.ENTER,
        include_clipboard=True,
        include_tone=False,
    )
    try:
        assert provider.input_calls == 1
        assert provider.hotkey_calls == [HID.ENTER]
        assert provider.clipboard_calls == 1
        assert provider.tone_calls == 0
        assert parts.clipboard is provider.clipboard
        assert parts.tone_output is None
        assert parts.output.capabilities.tone is None
    finally:
        parts.output.speaker.shutdown()


def test_coordinator_selected_engine_id_uses_store_default(tmp_path):
    store = SpeechEngineConfigStore(tmp_path / "speech.json")
    coordinator = SpeechRuntimeSettingsCoordinator(config_store=store)

    assert coordinator.selected_engine_id(default_engine_id="Pyttsx3") == "Pyttsx3"


def test_coordinator_selected_engine_id_reads_saved_engine(tmp_path):
    store = SpeechEngineConfigStore(tmp_path / "speech.json")
    store.save_engine_id("NvdaController")
    coordinator = SpeechRuntimeSettingsCoordinator(config_store=store)

    assert coordinator.selected_engine_id(default_engine_id="Pyttsx3") == "NvdaController"
