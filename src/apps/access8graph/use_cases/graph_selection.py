from pathlib import Path


class GraphSelectionUseCase:
    def __init__(self) -> None:
        self._selected_path: str | None = None

    def choose_graphml(self, path: str) -> None:
        graphml_path = Path(path)
        if graphml_path.suffix.lower() != ".graphml":
            raise ValueError("Selected file must have a .graphml extension")
        if not graphml_path.is_file():
            raise FileNotFoundError(str(graphml_path))
        self._selected_path = str(graphml_path)

    def get_selected_graphml_path(self) -> str | None:
        return self._selected_path

    def require_existing_graphml_path(self) -> Path:
        if self._selected_path is None:
            raise RuntimeError("No GraphML file selected")
        graphml_path = Path(self._selected_path)
        if not graphml_path.is_file():
            raise FileNotFoundError(
                f"GraphML file no longer exists: {self._selected_path}"
            )
        return graphml_path
