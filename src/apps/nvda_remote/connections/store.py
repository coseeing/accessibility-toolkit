from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from .models import ConnectionCatalog


class JsonConnectionStore:
    def __init__(self, path: Path, logger: logging.Logger | None = None) -> None:
        self.path = Path(path)
        self._logger = logger or logging.getLogger(__name__)

    def load(self) -> ConnectionCatalog:
        if not self.path.exists():
            return ConnectionCatalog.default()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return ConnectionCatalog.from_dict(payload)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            self._logger.error("Failed to load saved connections from %s", self.path, exc_info=True)
            return ConnectionCatalog.default()

    def save(self, catalog: ConnectionCatalog) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f"{self.path.name}.tmp")
        try:
            temporary.write_text(
                json.dumps(catalog.to_dict(), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, self.path)
        except OSError:
            try:
                temporary.unlink(missing_ok=True)
            finally:
                raise
