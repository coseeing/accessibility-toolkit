import json
from pathlib import Path

from application.output.speech.settings import clamp_percent


class SpeechEngineConfigStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load_engine_id(self, *, default_engine_id: str) -> str:
        payload = self._read()
        engine_id = payload.get("speech_engine")
        if not isinstance(engine_id, str) or not engine_id:
            return default_engine_id
        return engine_id

    def save_engine_id(self, engine_id: str) -> None:
        payload = self._read()
        payload["speech_engine"] = engine_id
        self._write(payload)

    def load_voice(self, engine_id: str) -> str | None:
        value = self._engine_payload(engine_id).get("voice")
        return value if isinstance(value, str) and value else None

    def save_voice(self, engine_id: str, voice_id: str) -> None:
        payload = self._read()
        self._ensure_engine_payload(payload, engine_id)["voice"] = voice_id
        self._write(payload)

    def load_numeric_setting(self, engine_id: str, setting_id: str) -> int | None:
        value = self._engine_payload(engine_id).get(setting_id)
        if not isinstance(value, int) or isinstance(value, bool):
            return None
        return clamp_percent(value)

    def save_numeric_setting(self, engine_id: str, setting_id: str, value: int) -> None:
        payload = self._read()
        self._ensure_engine_payload(payload, engine_id)[setting_id] = clamp_percent(value)
        self._write(payload)

    def _engine_payload(self, engine_id: str) -> dict[str, object]:
        speech_engines = self._read().get("speech_engines")
        if not isinstance(speech_engines, dict):
            return {}
        payload = speech_engines.get(engine_id)
        return payload if isinstance(payload, dict) else {}

    def _ensure_engine_payload(
        self, payload: dict[str, object], engine_id: str
    ) -> dict[str, object]:
        speech_engines = payload.setdefault("speech_engines", {})
        if not isinstance(speech_engines, dict):
            speech_engines = {}
            payload["speech_engines"] = speech_engines
        engine_payload = speech_engines.setdefault(engine_id, {})
        if not isinstance(engine_payload, dict):
            engine_payload = {}
            speech_engines[engine_id] = engine_payload
        return engine_payload

    def _read(self) -> dict[str, object]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write(self, payload: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
