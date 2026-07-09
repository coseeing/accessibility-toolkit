from typing import Protocol


class ClipboardService(Protocol):
    def set_text(self, text: str) -> None: ...

    def get_text(self) -> str: ...
