from application.input.results import AppKeyEventResult
from interop.key import HID, KeyEvent
from apps.key_echo.events import EchoStateChanged


class FakeSpeech:
    def __init__(self):
        self.engine_id = "default"
        self.voice_id = None
        self.rate = None
        self.pitch = None
        self.volume = None

    def get_engine_options(self):
        return (("default", "Default"),)

    def get_selected_engine(self):
        return self.engine_id

    def set_engine(self, engine_id):
        self.engine_id = engine_id

    def list_voices(self):
        return ()

    def get_voice(self):
        return self.voice_id

    def set_voice(self, voice_id):
        self.voice_id = voice_id

    def get_rate(self):
        return self.rate

    def set_rate(self, value):
        self.rate = value

    def get_pitch(self):
        return self.pitch

    def set_pitch(self, value):
        self.pitch = value

    def get_volume(self):
        return self.volume

    def set_volume(self, value):
        self.volume = value


def test_key_echo_speech_settings_use_case_proxies_engine_and_voice_controls():
    from apps.shared.speech_settings_facade import SpeechSettingsFacade

    speech = FakeSpeech()
    use_case = SpeechSettingsFacade(speech=speech)

    use_case.set_speech_engine("pyttsx3")
    use_case.set_selected_voice("voice-2")
    use_case.set_rate(120)

    assert speech.get_selected_engine() == "pyttsx3"
    assert speech.get_voice() == "voice-2"
    assert speech.get_rate() == 120


def test_echo_control_use_case_start_and_stop_echo():
    from apps.key_echo.use_cases.echo_control import KeyEchoControlUseCase

    statuses = []
    use_case = KeyEchoControlUseCase(
        notify_status=statuses.append,
    )

    use_case.start_echo()
    use_case.stop_echo()

    assert use_case.is_running() is False
    assert statuses == [
        EchoStateChanged(running=True),
        EchoStateChanged(running=False),
    ]


def test_echo_input_use_case_speaks_vk_text_on_keydown():
    from apps.key_echo.use_cases.echo_input import KeyEchoInputUseCase

    calls = []
    use_case = KeyEchoInputUseCase(
        cancel=lambda: calls.append(("cancel", None)),
        speak=lambda sequence: calls.append(("speak", sequence)),
    )

    decision = use_case.handle(KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True))

    assert decision is AppKeyEventResult.HANDLED_STOP
    assert calls[0] == ("cancel", None)
    assert calls[1][0] == "speak"


def test_echo_input_use_case_treats_num_lock_like_any_other_key():
    from apps.key_echo.use_cases.echo_input import KeyEchoInputUseCase

    calls = []
    use_case = KeyEchoInputUseCase(
        cancel=lambda: calls.append(("cancel", None)),
        speak=lambda sequence: calls.append(("speak", sequence)),
    )

    decision = use_case.handle(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.NUM_LOCK, pressed=True)
    )

    assert decision is AppKeyEventResult.HANDLED_CONTINUE
    assert calls[0] == ("cancel", None)
    assert calls[1][0] == "speak"


def test_echo_input_use_case_returns_handled_stop_for_regular_keys():
    from apps.key_echo.use_cases.echo_input import KeyEchoInputUseCase

    use_case = KeyEchoInputUseCase(cancel=lambda: None, speak=lambda _sequence: None)

    result = use_case.handle(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)
    )

    assert result is AppKeyEventResult.HANDLED_STOP


def test_echo_input_use_case_returns_handled_continue_for_num_lock():
    from apps.key_echo.use_cases.echo_input import KeyEchoInputUseCase

    use_case = KeyEchoInputUseCase(cancel=lambda: None, speak=lambda _sequence: None)

    result = use_case.handle(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.NUM_LOCK, pressed=True)
    )

    assert result is AppKeyEventResult.HANDLED_CONTINUE
