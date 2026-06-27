from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from application.events import ErrorRaised
from apps.access8graph.events import GraphNavigationChanged
from apps.access8graph.flow import MrtFlow
from apps.access8graph.graphml import (
    Graph,
    MrtDirectionNavigator,
    MrtModel,
    MrtUndirectionNavigator,
)


class FlowOutput(Protocol):
    def cancel_speech(self) -> None: ...


class FlowFactory(Protocol):
    def create(self, path: Path): ...


class MrtFlowFactory:
    def __init__(self, *, output) -> None:
        self._output = output

    def create(self, path: Path) -> MrtFlow:
        graph = Graph(path=str(path))
        model = MrtModel(graph)
        return MrtFlow(
            navigator={
                "direction": MrtDirectionNavigator(model),
                "undirection": MrtUndirectionNavigator(model),
            },
            output=self._output,
        )


class Access8GraphNavigationSession:
    def __init__(
        self,
        *,
        graph_selection,
        flow_factory: FlowFactory,
        flow_output: FlowOutput,
        notify_status: Callable[[object], None],
    ) -> None:
        self._graph_selection = graph_selection
        self._flow_factory = flow_factory
        self._flow_output = flow_output
        self._notify_status = notify_status
        self._active = False
        self._flow = None

    @property
    def current_flow(self):
        return self._flow

    def is_active(self) -> bool:
        return self._active

    def set_active(self, active: bool) -> None:
        self._active = active

    def can_start(self) -> bool:
        return self._graph_selection.get_selected_graphml_path() is not None

    def start_flow(self) -> None:
        path = self._graph_selection.require_existing_graphml_path()
        self._flow = self._flow_factory.create(path)
        self._notify_status(GraphNavigationChanged(active=True))

    def report_error(self, message: str) -> None:
        self._notify_status(ErrorRaised(message))

    def stop_flow(self) -> None:
        had_flow = self._flow is not None
        self._active = False
        self._flow = None
        self._flow_output.cancel_speech()
        if had_flow:
            self._notify_status(GraphNavigationChanged(active=False))
