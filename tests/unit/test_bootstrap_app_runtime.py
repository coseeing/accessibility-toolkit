from application.output import Scheduler
from application.output.speech import SpeechBackendOption
from bootstrap.app_runtime import build_app_runtime_parts
from bootstrap.platform import PlatformServices
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

    def build_services(self, hotkey_usage):
        self.hotkey_usage = hotkey_usage
        return PlatformServices(
            input_capture=self.input_capture,
            hotkey_capture=self.hotkey_capture,
            clipboard=self.clipboard,
            tone_output=self.tone_output,
        )

    def default_speech_backend_id(self):
        return "default"

    def default_speech_backend_options(self, scheduler):
        assert isinstance(scheduler, Scheduler)
        self.scheduler = scheduler
        return (
            SpeechBackendOption("default", "Default", lambda: FakeSpeechOutput()),
            SpeechBackendOption("selected", "Selected", lambda: FakeSpeechOutput()),
        )


def test_build_app_runtime_parts_wires_platform_and_output_services():
    provider = FakeProvider()

    parts = build_app_runtime_parts(
        provider=provider,
        hotkey_usage=HID.ENTER,
        selected_backend_id="selected",
    )
    try:
        assert provider.hotkey_usage == HID.ENTER
        assert parts.input_capture is provider.input_capture
        assert parts.hotkey_capture is provider.hotkey_capture
        assert parts.clipboard is provider.clipboard
        assert parts.tone_output is provider.tone_output
        assert parts.output.scheduler is provider.scheduler
        assert parts.output.speaker.get_selected_backend() == "selected"
        assert parts.output.capabilities.speech is parts.output.speaker
        assert parts.output.capabilities.tone is provider.tone_output
    finally:
        parts.output.speaker.shutdown()


def test_build_app_runtime_parts_uses_default_backend_and_can_exclude_tone():
    provider = FakeProvider()

    parts = build_app_runtime_parts(
        provider=provider,
        hotkey_usage=HID.ENTER,
        include_tone=False,
    )
    try:
        assert parts.tone_output is provider.tone_output
        assert parts.output.speaker.get_selected_backend() == "default"
        assert parts.output.capabilities.tone is None
    finally:
        parts.output.speaker.shutdown()
