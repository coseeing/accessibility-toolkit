from pathlib import Path

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
    NavigationCommand,
    NavigationContext,
    NavigationStateId,
    TransitionOutcome,
    TransitionResult,
)
from apps.access8graph.navigation.presenter import FlowPresenter
from apps.access8graph.navigation.table import (
    build_transition_rules,
    validate_transition_table,
)


FIXTURE = Path("Access8Graph/tests/test.graphml")


class FakeOutput:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def cancel(self) -> None:
        self.calls.append(("cancel", None))

    def speak(self, items: tuple[object, ...]) -> None:
        self.calls.append(("speak", tuple(str(item) for item in items if item)))

    def beep(self) -> None:
        self.calls.append(("beep", None))


def _build_transition_flow(fixture_path: Path, output: FakeOutput) -> TransitionNavigationFlow:
    graph = Graph(path=str(fixture_path))
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

    presenter = FlowPresenter(output=output)

    flow = TransitionNavigationFlow(engine=engine, presenter=presenter)

    mode_entry = entry_effects.get(NavigationStateId.MODE)
    if mode_entry is not None:
        snap = snap_factory.create(context)
        effects = mode_entry(snap, context)
        result = TransitionResult.transitioned(
            source=NavigationStateId.MODE,
            target=NavigationStateId.MODE,
            effects=effects,
        )
        presenter.present(result)

    return flow


def test_access8graph_transition_flow_starts_from_fixture_and_accepts_menu_navigation() -> None:
    output = FakeOutput()
    flow = _build_transition_flow(FIXTURE, output)

    assert output.calls[0] == ("cancel", None)
    assert output.calls[1][0] == "speak"
    assert "功能選單開啟" in output.calls[1][1]

    output.calls.clear()

    result = flow.enter(NavigationCommand.DOWN)

    assert result is True
    assert output.calls[0] == ("cancel", None)
    assert output.calls[1][0] == "speak"
    assert "線性探索" in output.calls[1][1]
    assert "功能選單關閉" in output.calls[1][1]
    assert "功能選單開啟" in output.calls[1][1]


def test_access8graph_transition_flow_confirm_direction_moves_to_lines() -> None:
    output = FakeOutput()
    flow = _build_transition_flow(FIXTURE, output)
    output.calls.clear()

    result = flow.enter(NavigationCommand.CONFIRM)

    assert result is True
    assert output.calls[0] == ("cancel", None)
    assert output.calls[1][0] == "speak"
    assert "功能選單關閉" in output.calls[1][1]
