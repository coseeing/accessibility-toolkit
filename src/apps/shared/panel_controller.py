class PanelController:
    def __init__(self) -> None:
        self._panels: dict[str, object] = {}

    def register(self, panel_id: str, frame: object) -> None:
        self._panels[panel_id] = frame

    def show(self, panel_id: str) -> None:
        frame = self._panels[panel_id]
        frame.Show(True)
        if hasattr(frame, "Raise"):
            frame.Raise()

    def hide(self, panel_id: str) -> None:
        frame = self._panels[panel_id]
        frame.Hide()
