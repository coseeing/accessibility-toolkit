from pathlib import Path

from accessibility_toolkit.output import Capabilities
from accessibility_toolkit.output.speech import SpeechSequence
from apps.nvda_remote.cues import NvdaRemoteCues


class FakeWave:
    def __init__(self) -> None:
        self.paths: list[str] = []

    def play(self, path: str) -> None:
        self.paths.append(path)


class FakeSpeech:
    def __init__(self) -> None:
        self.spoken: list[SpeechSequence] = []

    def speak(self, sequence: SpeechSequence) -> None:
        self.spoken.append(sequence)


def test_connection_cues_use_packaged_waves_and_disconnect_speech(tmp_path: Path):
    wave = FakeWave()
    speech = FakeSpeech()
    cues = NvdaRemoteCues(
        Capabilities(speech=speech, wave=wave),
        cue_directory=tmp_path,
    )

    cues.connected()
    cues.disconnected()

    assert wave.paths == [
        str(tmp_path / "connected.wav"),
        str(tmp_path / "disconnected.wav"),
    ]
    assert speech.spoken == [SpeechSequence(items=("Disconnected",))]


def test_control_cues_speak_local_and_remote_state(tmp_path: Path):
    speech = FakeSpeech()
    cues = NvdaRemoteCues(
        Capabilities(speech=speech),
        cue_directory=tmp_path,
    )

    cues.controlling_remote()
    cues.controlling_local()

    assert speech.spoken == [
        SpeechSequence(items=("Controlling remote computer",)),
        SpeechSequence(items=("Controlling local computer",)),
    ]


def test_disconnect_speech_continues_without_wave_output(tmp_path: Path):
    speech = FakeSpeech()
    cues = NvdaRemoteCues(
        Capabilities(speech=speech),
        cue_directory=tmp_path,
    )

    cues.disconnected()

    assert speech.spoken == [SpeechSequence(items=("Disconnected",))]
