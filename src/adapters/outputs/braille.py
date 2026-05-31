from typing import Protocol


class BrailleOutput(Protocol):
    def display(self, text: str) -> None: ...


class NullBrailleOutput:
    def display(self, text: str) -> None:
        return None
