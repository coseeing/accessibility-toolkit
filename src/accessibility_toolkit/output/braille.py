from accessibility_toolkit.output.interfaces import BrailleOutput


class NullBrailleOutput:
    def display(self, text: str) -> None:
        return None
