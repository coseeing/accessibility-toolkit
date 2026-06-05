import json
from pathlib import Path


class SpeechBackendConfigStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load_backend_id(self, *, default_backend_id: str) -> str:
        if not self.path.exists():
            return default_backend_id
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default_backend_id
        backend_id = payload.get("speech_backend")
        if not isinstance(backend_id, str) or not backend_id:
            return default_backend_id
        return backend_id

    def save_backend_id(self, backend_id: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"speech_backend": backend_id}, indent=2) + "\n",
            encoding="utf-8",
        )
