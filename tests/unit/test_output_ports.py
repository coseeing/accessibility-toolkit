from accessibility_toolkit.application.output.ports import (
    SpeechLifecyclePort,
    SpeechOutputPort,
    SpeechServicePort,
    SpeechSettingsPort,
)


class CompleteSpeech:
    def speak(self, sequence): pass
    def cancel(self): pass
    def pause(self, is_paused): pass
    def get_engine_options(self): return ()
    def get_selected_engine(self): return "fake"
    def set_engine(self, engine_id): pass
    def list_voices(self): return ()
    def get_voice(self): return None
    def set_voice(self, voice_id): pass
    def get_rate(self): return None
    def set_rate(self, value): pass
    def get_pitch(self): return None
    def set_pitch(self, value): pass
    def get_volume(self): return None
    def set_volume(self, value): pass
    def get_supported_numeric_settings(self): return ()
    def shutdown(self): pass


def test_complete_speech_satisfies_all_ports():
    speech = CompleteSpeech()

    assert isinstance(speech, SpeechOutputPort)
    assert isinstance(speech, SpeechSettingsPort)
    assert isinstance(speech, SpeechLifecyclePort)
    assert isinstance(speech, SpeechServicePort)
