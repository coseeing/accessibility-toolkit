"""Exact ordered output regression tests for the transition flow.

These tests assert the precise sequence of output calls (cancel, speak, beep)
for key navigation paths, complementing the parameterized parity suite which
only checks final state and beep presence.
"""
from __future__ import annotations

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
    FakeDirectionNavigator,
    FakeUndirectionNavigator,
    OutputCall,
)


class _RecordingOutput:
    def __init__(self) -> None:
        self.calls: list[OutputCall] = []

    def cancel(self) -> None:
        self.calls.append(OutputCall("cancel_speech"))

    def speak(self, items: tuple[object, ...]) -> None:
        self.calls.append(
            OutputCall("speak", tuple(str(item) for item in items if item))
        )

    def beep(self) -> None:
        self.calls.append(OutputCall("beep_failure"))


def _build_flow():
    dnav = FakeDirectionNavigator()
    unav = FakeUndirectionNavigator()
    out = _RecordingOutput()
    context = NavigationContext(current_state=NavigationStateId.MODE)
    snap = build_snapshot_factory(dnav, unav)
    guards = build_guard_registry()
    actions = build_action_registry(dnav, unav)
    entry = build_entry_effects(dnav, unav)
    exit_fx = build_exit_effects(dnav, unav)
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
        snapshot_factory=snap,
        context=context,
        exit_effects=exit_fx,
        entry_effects=entry,
    )
    presenter = FlowPresenter(output=out)
    flow = TransitionNavigationFlow(engine=engine, presenter=presenter)
    flow.start()

    return flow, out, context


def _speak_items(calls):
    """Extract all speak payloads concatenated."""
    items = []
    for call in calls:
        if call.kind == "speak":
            items.extend(call.payload)
    return items


def _call_kinds(calls):
    """Return the sequence of output call kinds."""
    return tuple(call.kind for call in calls)


# ── Startup ────────────────────────────────────────────────────────────


def test_startup_speaks_open_message_hint_and_view():
    flow, out, ctx = _build_flow()

    kinds = _call_kinds(out.calls)
    assert kinds == ("cancel_speech", "speak")

    spoken = _speak_items(out.calls)
    assert "功能選單開啟" in spoken
    assert "請使用上下鍵選擇導航模式" in spoken  # hint
    assert "方向探索" in spoken  # view item
    assert any("之" in item for item in spoken)  # position info


# ── Self-transition (list movement) ────────────────────────────────────


def test_list_movement_does_not_repeat_hint():
    flow, out, ctx = _build_flow()
    out.calls.clear()

    flow.enter(NavigationCommand.DOWN)

    kinds = _call_kinds(out.calls)
    assert kinds == ("cancel_speech", "speak")

    spoken = _speak_items(out.calls)
    # Hint should NOT be repeated on self-transition
    assert "請使用上下鍵選擇導航模式" not in spoken
    # View item should be present exactly once
    assert spoken.count("線性探索") == 1


def test_list_movement_does_not_repeat_view_items():
    flow, out, ctx = _build_flow()
    out.calls.clear()

    flow.enter(NavigationCommand.DOWN)
    spoken = _speak_items(out.calls)
    # Each view item should appear exactly once
    assert spoken.count("線性探索") == 1
    assert sum(1 for item in spoken if "之" in item) == 1


# ── State transition ───────────────────────────────────────────────────


def test_state_transition_includes_close_open_hint_and_view():
    flow, out, ctx = _build_flow()
    out.calls.clear()

    flow.enter(NavigationCommand.CONFIRM)

    kinds = _call_kinds(out.calls)
    assert kinds == ("cancel_speech", "speak")

    spoken = _speak_items(out.calls)
    # New state's hint
    assert any("路線" in item for item in spoken)  # direction_lines hint


# ── Rejected ───────────────────────────────────────────────────────────


def test_rejected_beeps_cancels_and_speaks_view():
    flow, out, ctx = _build_flow()
    out.calls.clear()

    # UP at first position (index 0) should be rejected
    flow.enter(NavigationCommand.UP)

    kinds = _call_kinds(out.calls)
    assert kinds[0] == "beep_failure"
    assert "cancel_speech" in kinds
    assert "speak" in kinds

    spoken = _speak_items(out.calls)
    # Should speak the current view (first item)
    assert "方向探索" in spoken


# ── Help flow ──────────────────────────────────────────────────────────


def test_help_from_stations_can_quit_back():
    flow, out, ctx = _build_flow()

    # Navigate to STATIONS: MODE → CONFIRM (select direction) → DIRECTION_LINES → STATIONS
    flow.enter(NavigationCommand.CONFIRM)  # MODE → DIRECTION_LINES
    flow.enter(NavigationCommand.CONFIRM)  # DIRECTION_LINES → DIRECTION_STATIONS
    flow.enter(NavigationCommand.CONFIRM)  # DIRECTION_STATIONS → DIRECTION_ENDPOINT (if both set)
    # Actually let's navigate to STATIONS (the generic list)
    # Start over with a simpler path
    flow2, out2, ctx2 = _build_flow()
    # MODE → CONFIRM selects "direction" → goes to DIRECTION_LINES
    flow2.enter(NavigationCommand.CONFIRM)
    # DIRECTION_LINES → SELECT_STATION → DIRECTION_STATIONS
    flow2.enter(NavigationCommand.SELECT_STATION)
    assert ctx2.current_state == NavigationStateId.DIRECTION_STATIONS

    out2.calls.clear()
    # Open help from DIRECTION_STATIONS
    flow2.enter(NavigationCommand.OPEN_HELP)
    assert ctx2.current_state == NavigationStateId.HELP
    assert ctx2.return_state == NavigationStateId.DIRECTION_STATIONS

    out2.calls.clear()
    # Quit help — should return to DIRECTION_STATIONS
    flow2.enter(NavigationCommand.QUIT)
    assert ctx2.current_state == NavigationStateId.DIRECTION_STATIONS

    kinds = _call_kinds(out2.calls)
    assert "cancel_speech" in kinds
    assert "speak" in kinds


def test_help_from_undirection_run_can_quit_back():
    dnav = FakeDirectionNavigator()
    unav = FakeUndirectionNavigator()
    out = _RecordingOutput()
    context = NavigationContext(current_state=NavigationStateId.UNDIRECTION_RUN)
    snap = build_snapshot_factory(dnav, unav)
    guards = build_guard_registry()
    actions = build_action_registry(dnav, unav)
    entry = build_entry_effects(dnav, unav)
    exit_fx = build_exit_effects(dnav, unav)
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
        snapshot_factory=snap,
        context=context,
        exit_effects=exit_fx,
        entry_effects=entry,
    )
    presenter = FlowPresenter(output=out)
    flow = TransitionNavigationFlow(engine=engine, presenter=presenter)

    # Open help from UNDIRECTION_RUN
    flow.enter(NavigationCommand.OPEN_HELP)
    assert context.current_state == NavigationStateId.HELP
    assert context.return_state == NavigationStateId.UNDIRECTION_RUN

    # Quit — should return to UNDIRECTION_RUN
    flow.enter(NavigationCommand.QUIT)
    assert context.current_state == NavigationStateId.UNDIRECTION_RUN
