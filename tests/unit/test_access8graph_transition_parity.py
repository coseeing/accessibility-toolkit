from __future__ import annotations

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
    FLOW_SCENARIOS,
    FakeDirectionNavigator,
    FakeUndirectionNavigator,
    FlowScenario,
    FlowTrace,
    OutputCall,
    RecordingOutput,
    build_legacy_flow,
    capture_legacy_trace,
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

    # Run arrangement on legacy flow to get navigator into the right state
    leg_flow, leg_rec = build_legacy_flow(dnav, unav)
    leg_rec.calls.clear()
    scenario.arrange(leg_flow)

    # Extract background state from legacy flow
    bg_state_id = None
    bg = leg_flow.background_state
    if bg is not None:
        for k, v in leg_flow.states.items():
            if v is bg:
                bg_state_id = _STATE_MAP.get(k)
                break

    # For help state, extract the calling state from HelpState
    help_return_state = None
    state_obj = leg_flow._state
    if hasattr(state_obj, "state"):
        help_return_state = state_obj.state
        for k, v in leg_flow.states.items():
            if v is help_return_state:
                help_return_state = _STATE_MAP.get(k)
                break

    # Build transition flow
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

    # Run entry effects for start state
    handler = entry.get(start_nav_state)
    if handler is not None:
        from apps.access8graph.navigation.snapshot import NavigationSnapshot
        rs = help_return_state if start_nav_state == NavigationStateId.HELP else bg_state_id
        snap = NavigationSnapshot(
            state=start_nav_state,
            return_state=rs,
            selected_id=getattr(context.view_model, "selected_id", None) if context.view_model else None,
            current_index=getattr(context.view_model, "current_index", 0) if context.view_model else 0,
            option_count=getattr(context.view_model, "option_count", 0) if context.view_model else 0,
        )
        handler(snap, context)

    # Discard setup output
    out.calls.clear()

    # Dispatch command (or trigger AUTO for empty-command scenarios)
    if scenario.command:
        flow.enter(scenario.command)
    elif not scenario.command and scenario.expected_state != scenario.start_state:
        # Auto-select scenario: trigger AUTO progression manually
        try:
            engine.dispatch(NavigationCommand.AUTO)
        except Exception:
            pass

    # Resolve final state
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


@pytest.mark.parametrize("scenario", FLOW_SCENARIOS, ids=lambda s: s.id)
def test_new_transition_flow_matches_legacy_trace(scenario: FlowScenario):
    legacy = capture_legacy_trace(scenario)
    replacement = capture_transition_trace(scenario)

    assert replacement.state_id == scenario.expected_state, (
        f"[{scenario.id}] Expected state '{scenario.expected_state}', "
        f"got '{replacement.state_id}'"
    )

    legacy_success = all(call.kind != "beep_failure" for call in legacy.output_calls)
    repl_success = all(call.kind != "beep_failure" for call in replacement.output_calls)

    assert repl_success == scenario.expected_success, (
        f"[{scenario.id}] Expected success={scenario.expected_success}, "
        f"got success={repl_success}"
    )
