from __future__ import annotations

import json
from pathlib import Path

import pytest

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
)
from apps.access8graph.navigation.presenter import FlowPresenter
from apps.access8graph.navigation.table import (
    build_transition_rules,
    validate_transition_table,
)

from tests.unit.access8graph_flow_scenarios import (
    _ArrangeAdapter,
    FLOW_SCENARIOS,
    FakeDirectionNavigator,
    FakeUndirectionNavigator,
    FlowScenario,
    FlowTrace,
    OutputCall,
)


# ---------------------------------------------------------------------------
# Recording output for the new flow
# ---------------------------------------------------------------------------

class TransitionRecordingOutput:
    def __init__(self):
        self.calls: list[OutputCall] = []

    def cancel(self) -> None:
        self.calls.append(OutputCall("cancel_speech"))

    def speak(self, items: tuple[object, ...]) -> None:
        self.calls.append(
            OutputCall("speak", tuple(str(item) for item in items if item))
        )

    def beep(self) -> None:
        self.calls.append(OutputCall("beep_failure"))


# ---------------------------------------------------------------------------
# State mapping
# ---------------------------------------------------------------------------

_STATE_MAP: dict[str, NavigationStateId] = {
    "mode": NavigationStateId.MODE,
    "stations": NavigationStateId.STATIONS,
    "lines": NavigationStateId.LINES,
    "direction_end_point": NavigationStateId.DIRECTION_END_POINT,
    "direction_run": NavigationStateId.DIRECTION_RUN,
    "undirection_run": NavigationStateId.UNDIRECTION_RUN,
    "plan_run": NavigationStateId.PLAN_RUN,
    "direction_transfer": NavigationStateId.DIRECTION_TRANSFER,
    "undirection_transfer": NavigationStateId.UNDIRECTION_TRANSFER,
    "explore_neighbor": NavigationStateId.EXPLORE_NEIGHBOR,
    "explore_sub_line": NavigationStateId.EXPLORE_SUB_LINE,
    "direction_stations": NavigationStateId.DIRECTION_STATIONS,
    "direction_lines": NavigationStateId.DIRECTION_LINES,
    "source_stations": NavigationStateId.SOURCE_STATIONS,
    "source_lines": NavigationStateId.SOURCE_LINES,
    "destination_stations": NavigationStateId.DESTINATION_STATIONS,
    "destination_lines": NavigationStateId.DESTINATION_LINES,
    "undirection_stations": NavigationStateId.UNDIRECTION_STATIONS,
    "undirection_lines": NavigationStateId.UNDIRECTION_LINES,
    "undirection_sub_lines": NavigationStateId.UNDIRECTION_SUB_LINES,
    "help": NavigationStateId.HELP,
}

_STATE_REV = {v: k for k, v in _STATE_MAP.items()}

_CMD_MAP: dict[str, NavigationCommand] = {
    "up": NavigationCommand.UP,
    "down": NavigationCommand.DOWN,
    "left": NavigationCommand.LEFT,
    "right": NavigationCommand.RIGHT,
    "enter": NavigationCommand.CONFIRM,
    "home": NavigationCommand.HOME,
    "end": NavigationCommand.END,
    "d": NavigationCommand.SELECT_DIRECTION,
    "u": NavigationCommand.SELECT_UNDIRECTED,
    "p": NavigationCommand.SELECT_PLAN,
    "q": NavigationCommand.QUIT,
    "h": NavigationCommand.OPEN_HELP,
    "m": NavigationCommand.OPEN_MODE,
    "v": NavigationCommand.OPEN_BROWSER,
    "s": NavigationCommand.SELECT_STATION,
    "l": NavigationCommand.SELECT_LINE,
    "e": NavigationCommand.SELECT_ENDPOINT,
}


# ---------------------------------------------------------------------------
# Trace capture for transition flow
# ---------------------------------------------------------------------------


def capture_transition_trace(scenario: FlowScenario) -> FlowTrace:
    dnav = FakeDirectionNavigator()
    unav = FakeUndirectionNavigator()

    adapter = _ArrangeAdapter({"direction": dnav, "undirection": unav})
    scenario.arrange(adapter)

    bg_state_id = _STATE_MAP.get(adapter.background_state) if adapter.background_state else None
    help_return_state = _STATE_MAP.get(adapter._help_from) if adapter._help_from else None

    out = TransitionRecordingOutput()
    presenter = FlowPresenter(out)

    guards = build_guard_registry()
    actions = build_action_registry(dnav, unav)
    entry = build_entry_effects(dnav, unav)
    exit_fx = build_exit_effects(dnav, unav)
    snap_factory = build_snapshot_factory(dnav, unav)

    rules = build_transition_rules()
    table = validate_transition_table(
        rules=rules,
        initial_state=NavigationStateId.MODE,
        action_ids=ALL_ACTION_IDS,
        guard_ids=ALL_GUARD_IDS,
    )

    start_nav_state = _STATE_MAP.get(scenario.start_state, NavigationStateId.MODE)

    context = NavigationContext(
        current_state=start_nav_state,
        return_state=help_return_state if start_nav_state == NavigationStateId.HELP else bg_state_id,
    )

    engine = TransitionEngine(
        table=table,
        guards=guards,
        actions=actions,
        snapshot_factory=snap_factory,
        context=context,
        exit_effects=exit_fx,
        entry_effects=entry,
    )

    flow = TransitionNavigationFlow(engine=engine, presenter=presenter)
    if start_nav_state in (NavigationStateId.MODE, NavigationStateId.HELP):
        flow.start()
    else:
        handler = entry.get(start_nav_state)
        if handler is not None:
            handler(snap_factory.create(context), context)
            context.hint_pending = True
    if scenario.command or start_nav_state == NavigationStateId.MODE:
        out.calls.clear()

    if scenario.command:
        cmd = _CMD_MAP.get(scenario.command)
        if cmd is not None:
            flow.enter(cmd)
        else:
            # Runtime misuse still rejects consistently at the flow boundary;
            # production callers use the typed NavigationCommand contract.
            flow.enter(scenario.command)  # type: ignore[arg-type]
    elif not scenario.command and scenario.expected_state != scenario.start_state:
        try:
            engine.dispatch(NavigationCommand.AUTO)
        except Exception:
            pass

    final_state = _STATE_REV.get(context.current_state, "unknown")

    return FlowTrace(
        state_id=final_state,
        background_state_id=(
            _STATE_REV.get(context.return_state) if context.return_state else None
        ),
        output_calls=tuple(out.calls),
        direction={
            "line": dnav.line,
            "station": dnav.station,
            "source": dnav.source,
            "destination": dnav.destination,
            "current": dnav.current,
            "run": dnav.run,
        },
        undirection={
            "line": unav.line,
            "station": unav.station,
            "current": unav.current,
            "sub_line": unav.sub_line,
        },
    )


# ---------------------------------------------------------------------------
# Parameterized parity test
# ---------------------------------------------------------------------------

_LEGACY_TRACES = json.loads(
    (
        Path(__file__).parent
        / "data"
        / "access8graph_legacy_traces.json"
    ).read_text(encoding="utf-8")
)


def _normalize_trace(value):
    if hasattr(value, "__dataclass_fields__"):
        return {
            name: _normalize_trace(getattr(value, name))
            for name in value.__dataclass_fields__
        }
    if isinstance(value, dict):
        return {str(key): _normalize_trace(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_trace(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_normalize_trace(item) for item in value), key=repr)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


@pytest.mark.parametrize("scenario", FLOW_SCENARIOS, ids=lambda s: s.id)
def test_transition_flow_scenario(scenario: FlowScenario):
    trace = capture_transition_trace(scenario)

    assert _normalize_trace(trace) == _LEGACY_TRACES[scenario.id]


@pytest.mark.parametrize(
    ("return_state", "expected_state", "selected_id", "nav_family", "field"),
    (
        ("stations", "lines", "l", "direction", "line"),
        ("lines", "stations", "s", "direction", "station"),
        ("direction_stations", "direction_lines", "l", "direction", "line"),
        ("direction_lines", "direction_stations", "s", "direction", "station"),
        ("undirection_stations", "undirection_lines", "l", "undirection", "line"),
        ("undirection_lines", "undirection_stations", "s", "undirection", "station"),
        ("source_stations", "source_lines", "l", "direction", "line"),
        ("source_lines", "source_stations", "s", "direction", "station"),
        ("destination_stations", "destination_lines", "l", "direction", "line"),
        ("destination_lines", "destination_stations", "s", "direction", "station"),
        ("direction_run", "mode", "m", "direction", None),
        ("undirection_run", "mode", "m", "undirection", None),
        ("plan_run", "mode", "m", "direction", None),
    ),
)
def test_help_confirm_uses_return_state_family(
    return_state, expected_state, selected_id, nav_family, field
):
    def arrange(adapter):
        adapter._help_from = return_state
        if field is not None:
            setattr(adapter.navigator[nav_family], field, "selected")

    trace = capture_transition_trace(
        FlowScenario(
            id=f"help_{return_state}_{selected_id}",
            start_state="help",
            command="enter",
            arrange=arrange,
            expected_state=expected_state,
            expected_success=True,
        )
    )

    assert trace.state_id == expected_state
    if field is not None:
        assert trace.direction[field] is None if nav_family == "direction" else (
            trace.undirection[field] is None
        )
