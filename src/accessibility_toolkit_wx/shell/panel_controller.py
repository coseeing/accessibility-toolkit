class PanelController:
    def __init__(self) -> None:
        self._panels: dict[str, object] = {}

    def register(self, panel_id: str, frame: object) -> None:
        self._panels[panel_id] = frame

    def show(self, panel_id: str) -> None:
        frame = self._get_frame(panel_id)
        frame.Show(True)
        if hasattr(frame, "Raise"):
            frame.Raise()

    def hide(self, panel_id: str) -> None:
        frame = self._get_frame(panel_id)
        frame.Hide()

    def _get_frame(self, panel_id: str) -> object:
        if panel_id not in self._panels:
            raise KeyError(f"Panel {panel_id!r} not registered")
        return self._panels[panel_id]
