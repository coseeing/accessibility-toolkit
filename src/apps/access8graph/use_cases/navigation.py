from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from accessibility_toolkit.events import ErrorRaised
from apps.access8graph.events import GraphNavigationChanged
from apps.access8graph.graphml import (
    Graph,
    MrtDirectionNavigator,
    MrtModel,
    MrtUndirectionNavigator,
)
from apps.access8graph.navigation.actions import (
    ALL_ACTION_IDS,
    ALL_GUARD_IDS,
    build_action_registry,
    build_entry_effects,
    build_exit_effects,
    build_guard_registry,
    build_snapshot_factory,
)
from apps.access8graph.navigation.engine import TransitionEngine
from apps.access8graph.navigation.flow import TransitionNavigationFlow
from apps.access8graph.navigation.model import (
    NavigationContext,
    NavigationStateId,
)
from apps.access8graph.navigation.presenter import FlowPresenter
from apps.access8graph.navigation.table import (
    build_transition_rules,
    validate_transition_table,
)


class FlowOutput(Protocol):
    def cancel_speech(self) -> None: ...


class FlowFactory(Protocol):
    def create(self, path: Path): ...


class _OutputAdapter:
    def __init__(self, output):
        self._output = output

    def speak(self, items):
        return self._output.speak(items)

    def cancel(self):
        return self._output.cancel_speech()

    def beep(self):
        return self._output.beep_failure()


class MrtFlowFactory:
    def __init__(self, *, output) -> None:
        self._output = output

    def create(self, path: Path) -> TransitionNavigationFlow:
        graph = Graph(path=str(path))
        model = MrtModel(graph)
        direction_nav = MrtDirectionNavigator(model)
        undirection_nav = MrtUndirectionNavigator(model)

        context = NavigationContext(current_state=NavigationStateId.MODE)

        snap_factory = build_snapshot_factory(direction_nav, undirection_nav)
        guards = build_guard_registry(direction_nav, undirection_nav)
        actions = build_action_registry(direction_nav, undirection_nav)
        entry_effects = build_entry_effects(direction_nav, undirection_nav)
        exit_effects = build_exit_effects(direction_nav, undirection_nav)

        rules = build_transition_rules()
        table = validate_transition_table(
            rules=rules,
            initial_state=NavigationStateId.MODE,
            action_ids=ALL_ACTION_IDS,
            guard_ids=ALL_GUARD_IDS,
        )

        engine = TransitionEngine(
            table=table,
            guards=guards,
            actions=actions,
            snapshot_factory=snap_factory,
            context=context,
            exit_effects=exit_effects,
            entry_effects=entry_effects,
        )

        presenter = FlowPresenter(output=_OutputAdapter(self._output))

        flow = TransitionNavigationFlow(engine=engine, presenter=presenter)

        flow.start()

        return flow


class Access8GraphNavigationSession:
    def __init__(
        self,
        *,
        graph_selection,
        flow_factory: FlowFactory,
        flow_output: FlowOutput,
        notify_status: Callable[[ErrorRaised | GraphNavigationChanged], None],
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
