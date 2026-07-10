import ctypes
import html
import logging
import sys
from pathlib import Path
from typing import Any

from accessibility_toolkit.output.speech.commands import (
    BreakCommand,
    PitchCommand,
    RateCommand,
    VolumeCommand,
)
from accessibility_toolkit.output.speech.sequence import SpeechSequence
from accessibility_toolkit.output.speech.settings import SpeechNumericSetting, clamp_percent
from accessibility_toolkit.scheduling import Scheduler


VENDORED_X64_DLL = (
    Path(__file__).resolve().parent
    / "vendor"
    / "nvda"
    / "x64"
    / "nvdaControllerClient.dll"
)
logger = logging.getLogger(__name__)
SPEAK_SSML_FUNCTION = "nvdaController_speakSsml"
CANCEL_SPEECH_FUNCTION = "nvdaController_cancelSpeech"
_SUPPORTED_NUMERIC_SETTINGS = (
    SpeechNumericSetting(id="rate", label="Rate"),
    SpeechNumericSetting(id="pitch", label="Pitch"),
    SpeechNumericSetting(id="volume", label="Volume"),
)


class NvdaControllerSpeechOutput:
    def __init__(
        self,
        controller: Any | None,
        *,
        loaded_from: str | None = None,
        scheduler: Scheduler | None = None,
    ) -> None:
        self.controller = controller if self._supports_ssml(controller) else None
        self.available = self.controller is not None
        self.loaded_from = loaded_from
        self._scheduler = scheduler
        self._rate = 50
        self._pitch = 50
        self._volume = 50

    @classmethod
    def load_default(
        cls,
        *,
        loader: Any | None = None,
        is_windows: bool | None = None,
        scheduler: Scheduler | None = None,
    ) -> "NvdaControllerSpeechOutput":
        running_windows = sys.platform == "win32" if is_windows is None else is_windows
        if not running_windows:
            logger.debug("NVDA controller unavailable: not running on Windows")
            return cls(controller=None, scheduler=scheduler)
        if loader is None:
            loader = ctypes.WinDLL
        candidate = str(VENDORED_X64_DLL)
        try:
            controller = loader(candidate)
            if not cls._supports_ssml(controller):
                logger.debug(
                    "Rejected NVDA controller DLL from %s: missing %s",
                    candidate,
                    SPEAK_SSML_FUNCTION,
                )
                return cls(controller=None, scheduler=scheduler)
            logger.debug("Loaded NVDA controller DLL from %s", candidate)
            return cls(controller=controller, loaded_from=candidate, scheduler=scheduler)
        except OSError as error:
            logger.debug("Failed to load NVDA controller DLL from %s: %s", candidate, error)
        logger.warning("NVDA controller DLL could not be loaded from vendored path")
        return cls(controller=None, scheduler=scheduler)

    @staticmethod
    def _supports_ssml(controller: Any | None) -> bool:
        if controller is None:
            return False
        return callable(getattr(controller, SPEAK_SSML_FUNCTION, None))

    def speak(self, speech: SpeechSequence) -> None:
        if not self.available:
            logger.debug("NVDA controller unavailable; speech output skipped")
            return
        logger.debug("NVDA controller received speech sequence: %r", speech)
        ssml = self._speech_to_ssml(speech)
        logger.debug(
            "NVDA controller speak requested: ssml=%r",
            ssml,
        )
        if not ssml:
            logger.debug("NVDA controller speech SSML is empty; speak skipped")
            return
        if self._scheduler is None:
            self._speak_ssml(ssml)
            return
        self._scheduler.schedule(self, lambda: self._speak_ssml(ssml))

    def _speak_ssml(self, ssml: str) -> None:
        try:
            result = getattr(self.controller, SPEAK_SSML_FUNCTION)(ssml, 0, 0, True)
            logger.debug("NVDA controller speakSsml returned %r", result)
        except Exception:
            logger.exception("NVDA controller speech call raised an exception")

    def cancel(self) -> None:
        if self._scheduler is not None:
            self._scheduler.cancel_all()
        self.stop()

    def stop(self) -> None:
        if self.available:
            try:
                result = getattr(self.controller, CANCEL_SPEECH_FUNCTION)()
                logger.debug("NVDA controller cancelSpeech returned %r", result)
            except Exception:
                logger.exception("NVDA controller cancelSpeech raised an exception")
        else:
            logger.debug("NVDA controller unavailable; cancel skipped")

    def pause(self, is_paused: bool) -> None:
        return None

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return ()

    def get_voice(self) -> str | None:
        return None

    def set_voice(self, voice_id: str) -> None:
        return None

    def get_rate(self) -> int | None:
        if not self.available:
            return None
        return self._rate

    def set_rate(self, value: int) -> None:
        self._rate = clamp_percent(value)

    def get_pitch(self) -> int | None:
        if not self.available:
            return None
        return self._pitch

    def set_pitch(self, value: int) -> None:
        self._pitch = clamp_percent(value)

    def get_volume(self) -> int | None:
        if not self.available:
            return None
        return self._volume

    def set_volume(self, value: int) -> None:
        self._volume = clamp_percent(value)

    def get_supported_numeric_settings(self) -> tuple[SpeechNumericSetting, ...]:
        if not self.available:
            return ()
        return _SUPPORTED_NUMERIC_SETTINGS

    def _speech_to_ssml(self, speech: SpeechSequence) -> str:
        segments: list[tuple[dict[str, int], str]] = []
        active_prosody = self._baseline_prosody_attrs()
        content_parts: list[str] = []

        for item in speech.items:
            if isinstance(item, str):
                if item:
                    content_parts.append(html.escape(item, quote=True))
                continue
            if isinstance(item, BreakCommand):
                content_parts.append(f'<break time="{item.time}ms"/>')
                continue
            prosody_attr = self._resolve_prosody_attr(item)
            if prosody_attr is not None:
                if content_parts:
                    segments.append((dict(active_prosody), "".join(content_parts)))
                    content_parts = []
                name, value = prosody_attr
                active_prosody[name] = value
                continue

        if content_parts:
            segments.append((dict(active_prosody), "".join(content_parts)))

        body = "".join(self._wrap_prosody(attrs, content) for attrs, content in segments)
        if not body:
            return ""
        return f"<speak>{body}</speak>"

    def _resolve_prosody_attr(self, item: object) -> tuple[str, int] | None:
        if isinstance(item, PitchCommand):
            return ("pitch", self._prosody_percent(item, baseline=self._pitch))
        if isinstance(item, RateCommand):
            return ("rate", self._prosody_percent(item, baseline=self._rate))
        if isinstance(item, VolumeCommand):
            return ("volume", self._prosody_percent(item, baseline=self._volume))
        return None

    @staticmethod
    def _prosody_percent(command: PitchCommand | RateCommand | VolumeCommand, *, baseline: int) -> int:
        if command.mode == "multiplier":
            return round(command.multiplier * 100)
        if command.mode == "offset":
            if baseline == 0:
                return 100
            return round(((baseline + command.offset) / baseline) * 100)
        return 100

    def _baseline_prosody_attrs(self) -> dict[str, int]:
        attrs: dict[str, int] = {}
        for name, value in (
            ("rate", self._normalized_percent_to_ssml_percent(self._rate)),
            ("pitch", self._normalized_percent_to_ssml_percent(self._pitch)),
            ("volume", self._normalized_percent_to_ssml_percent(self._volume)),
        ):
            if value != 100:
                attrs[name] = value
        return attrs

    @staticmethod
    def _normalized_percent_to_ssml_percent(value: int) -> int:
        """Map a normalized 0-100 percent to an SSML prosody percent.

        The baseline (normalized value 50) maps to SSML ``100%``. Values at or
        below ``0`` map to ``0%``: for ``volume`` this means silence, while for
        ``rate``/``pitch`` the resulting ``rate="0%"``/``pitch="0%"`` semantics
        are defined by the receiving SSML engine. This mapping is intentionally
        driver-owned and kept inside the NVDA controller driver per the spec.
        """
        if value <= 0:
            return 0
        return round((value / 50) * 100)

    @staticmethod
    def _wrap_prosody(attrs: dict[str, int], content: str) -> str:
        if not content:
            return ""
        wrapped = content
        for name, value in reversed(tuple(attrs.items())):
            wrapped = f'<prosody {name}="{value}%">{wrapped}</prosody>'
        return wrapped
