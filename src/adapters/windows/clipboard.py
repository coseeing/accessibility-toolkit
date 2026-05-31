from collections.abc import Callable


class WindowsClipboardService:
    def __init__(
        self,
        reader: Callable[[], str] | None = None,
        writer: Callable[[str], None] | None = None,
    ) -> None:
        self._reader = reader or (lambda: "")
        self._writer = writer or (lambda _value: None)

    def set_text(self, text: str) -> None:
        self._writer(text)

    def get_text(self) -> str:
        return self._reader()
