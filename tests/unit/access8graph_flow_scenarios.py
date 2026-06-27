from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable




# ---------------------------------------------------------------------------
# Observable trace types
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class OutputCall:
    kind: str
    payload: tuple[object, ...] = ()


@dataclass(frozen=True, slots=True)
class FlowTrace:
    state_id: str
    background_state_id: str | None
    output_calls: tuple[OutputCall, ...]
    direction: dict[str, Any]
    undirection: dict[str, Any]


@dataclass(frozen=True, slots=True)
class FlowScenario:
    id: str
    start_state: str
    command: str
    arrange: Callable[[object], None]
    expected_state: str
    expected_success: bool
    expected_beep: bool = False


# ---------------------------------------------------------------------------
# Recording output (implements the FlowOutput protocol)
# ---------------------------------------------------------------------------

class RecordingOutput:
    def __init__(self) -> None:
        self.calls: list[OutputCall] = []

    def cancel_speech(self) -> None:
        self.calls.append(OutputCall("cancel_speech"))

    def speak(self, items: Any) -> None:
        self.calls.append(
            OutputCall("speak", tuple(str(item) for item in items if item))
        )

    def beep_failure(self) -> None:
        self.calls.append(OutputCall("beep_failure"))


# ---------------------------------------------------------------------------
# Fake model (supports get_node_from_station_id_line_id)
# ---------------------------------------------------------------------------

class FakeModel:
    def __init__(self) -> None:
        self._nodes: dict[tuple, set[str]] = {}

    def get_node_from_station_id_line_id(
        self, station_id: str, line_id: str
    ) -> set[str]:
        key = (station_id, line_id)
        if key not in self._nodes:
            self._nodes[key] = {f"node_{station_id}_{line_id}"}
        return self._nodes[key]


# ---------------------------------------------------------------------------
# Fake direction navigator
# ---------------------------------------------------------------------------

_EMPTY_DISPLAY_LIST: list[dict[str, Any]] = []


class FakeDirectionNavigator:
    def __init__(self, model: FakeModel | None = None) -> None:
        self.model: FakeModel = model if model is not None else FakeModel()
        self.line: str | None = None
        self.station: str | None = None
        self.source: Any = None
        self.destination: Any = None
        self.current: Any = None
        self._run: bool = False

        self.lines_display: list[dict[str, Any]] = [
            {"id": "blue", "label": "Blue Line"},
            {"id": "red", "label": "Red Line"},
        ]
        self.stations_display: list[dict[str, Any]] = [
            {"id": "central", "label": "Central"},
            {"id": "east", "label": "East"},
        ]
        self.end_points: list[dict[str, Any]] = [
            {"id": "north", "label": "North Terminal"},
        ]
        self.transfer_display: list[dict[str, Any]] = _EMPTY_DISPLAY_LIST
        self.current_display: dict[str, Any] = {
            "id": "central", "label": "Central",
        }
        self.destination_display: dict[str, Any] = {
            "id": "east", "label": "East",
        }
        self.forward: list[Any] = []
        self.reverse: list[Any] = []
        self.reverse_display: list[dict[str, Any]] = _EMPTY_DISPLAY_LIST

    @property
    def run(self) -> bool:
        return self._run or bool(self.source and self.destination and self.current)

    @run.setter
    def run(self, value: bool) -> None:
        self._run = value


# ---------------------------------------------------------------------------
# Fake undirection navigator
# ---------------------------------------------------------------------------

class FakeUndirectionNavigator:
    def __init__(self, model: FakeModel | None = None) -> None:
        self.model: FakeModel = model if model is not None else FakeModel()
        self.line: str | None = None
        self.station: str | None = None
        self.current: Any = None
        self.sub_line: tuple = ()

        self.lines_display: list[dict[str, Any]] = [
            {"id": "blue", "label": "Blue Line"},
            {"id": "red", "label": "Red Line"},
        ]
        self.stations_display: list[dict[str, Any]] = [
            {"id": "central", "label": "Central"},
            {"id": "east", "label": "East"},
        ]
        self.sub_lines_display: list[dict[str, Any]] = [
            {"id": ("central", "east"), "label": "Central to East"},
            {"id": ("central", "west"), "label": "Central to West"},
        ]
        self.transfer_display: list[dict[str, Any]] = _EMPTY_DISPLAY_LIST
        self.current_display: dict[str, Any] = {
            "id": "central", "label": "Central",
        }
        self.line_name_display: dict[str, Any] = {
            "id": "central", "label": "Blue Line",
        }
        self.left_point_name_display: dict[str, Any] = {
            "id": "central", "label": "Central",
        }
        self.right_point_name_display: dict[str, Any] = {
            "id": "east", "label": "East",
        }
        self.previous: Any = None
        self.next: Any = None
        self.mode: str = "center"
        self.transfer_same_sub_line: list[Any] = _EMPTY_DISPLAY_LIST


# ---------------------------------------------------------------------------
# Arrange adapter for running scenario arrangement
# ---------------------------------------------------------------------------

class _ArrangeAdapter:
    """Thin wrapper that supports the arrange lambdas directly on navigators."""

    def __init__(self, navigators: dict[str, Any]) -> None:
        self.navigator = navigators
        self.background_state: str | None = None
        self._help_from: str | None = None
        self.message: list[str] = []

    def enter(self, command: dict[str, str]) -> bool:
        return True


# ---------------------------------------------------------------------------
# Arrange helpers (reusable for many scenarios)
# ---------------------------------------------------------------------------

def _set_state(adapter: _ArrangeAdapter, state_id: str) -> None:
    pass


def _enter_help(adapter: _ArrangeAdapter, from_state_id: str) -> None:
    adapter._help_from = from_state_id


def _arrange_mode_with_bg(adapter: _ArrangeAdapter, bg_state_id: str) -> None:
    adapter.navigator["direction"].run = True
    adapter.background_state = bg_state_id


# ---------------------------------------------------------------------------
# Display data factories
# ---------------------------------------------------------------------------

_MULTI_LINES: list[dict[str, Any]] = [
    {"id": "blue", "label": "Blue Line"},
    {"id": "red", "label": "Red Line"},
]

_SINGLE_LINE: list[dict[str, Any]] = [
    {"id": "green", "label": "Green Line"},
]

_MULTI_STATIONS: list[dict[str, Any]] = [
    {"id": "central", "label": "Central"},
    {"id": "east", "label": "East"},
]

_SINGLE_STATION: list[dict[str, Any]] = [
    {"id": "central", "label": "Central"},
]

_MULTI_END_POINTS: list[dict[str, Any]] = [
    {"id": "north", "label": "North Terminal"},
    {"id": "south", "label": "South Terminal"},
]

_MULTI_SUB_LINES: list[dict[str, Any]] = [
    {"id": ("central", "east"), "label": "Central to East"},
    {"id": ("central", "west"), "label": "Central to West"},
]

_TRANSFER_OPTIONS: list[dict[str, Any]] = [
    {
        "id": ("node_a", "node_b"),
        "label": "Transfer A",
        "attribute": "transfer",
    },
]


# ===================================================================
# FLOW SCENARIOS
# ===================================================================

FLOW_SCENARIOS: tuple[FlowScenario, ...] = (

    # ── mode ────────────────────────────────────────────────────────

    FlowScenario(
        id="mode_up_success",
        start_state="mode",
        command="down",
        arrange=lambda f: None,
        expected_state="mode",
        expected_success=True,
    ),
    FlowScenario(
        id="mode_up_boundary",
        start_state="mode",
        command="up",
        arrange=lambda f: None,
        expected_state="mode",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="mode_home_success",
        start_state="mode",
        command="home",
        arrange=lambda f: None,
        expected_state="mode",
        expected_success=True,
    ),
    FlowScenario(
        id="mode_end_success",
        start_state="mode",
        command="end",
        arrange=lambda f: None,
        expected_state="mode",
        expected_success=True,
    ),
    FlowScenario(
        id="mode_select_direction",
        start_state="mode",
        command="d",
        arrange=lambda f: None,
        expected_state="direction_lines",
        expected_success=True,
    ),
    FlowScenario(
        id="mode_select_undirection",
        start_state="mode",
        command="u",
        arrange=lambda f: None,
        expected_state="undirection_lines",
        expected_success=True,
    ),
    FlowScenario(
        id="mode_select_plan",
        start_state="mode",
        command="p",
        arrange=lambda f: None,
        expected_state="source_lines",
        expected_success=True,
    ),
    FlowScenario(
        id="mode_quit_with_active_background",
        start_state="mode",
        command="q",
        arrange=lambda f: _arrange_mode_with_bg(f, "direction_run"),
        expected_state="direction_run",
        expected_success=True,
    ),
    FlowScenario(
        id="mode_quit_without_background_rejected",
        start_state="mode",
        command="q",
        arrange=lambda f: None,
        expected_state="mode",
        expected_success=False,
        expected_beep=True,
    ),

    # ── stations ────────────────────────────────────────────────────

    FlowScenario(
        id="stations_down_success",
        start_state="stations",
        command="down",
        arrange=lambda f: _set_state(f, "stations"),
        expected_state="stations",
        expected_success=True,
    ),
    FlowScenario(
        id="stations_up_boundary",
        start_state="stations",
        command="up",
        arrange=lambda f: _set_state(f, "stations"),
        expected_state="stations",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="stations_confirm",
        start_state="stations",
        command="enter",
        arrange=lambda f: _set_state(f, "stations"),
        expected_state="lines",
        expected_success=True,
    ),
    FlowScenario(
        id="stations_line_command",
        start_state="stations",
        command="l",
        arrange=lambda f: _set_state(f, "stations"),
        expected_state="lines",
        expected_success=True,
    ),
    FlowScenario(
        id="stations_quit_with_active_background",
        start_state="stations",
        command="q",
        arrange=lambda f: (
            _arrange_mode_with_bg(f, "direction_run"),
            _set_state(f, "stations"),
        ),
        expected_state="direction_run",
        expected_success=True,
    ),
    FlowScenario(
        id="stations_quit_without_run_rejected",
        start_state="stations",
        command="q",
        arrange=lambda f: _set_state(f, "stations"),
        expected_state="stations",
        expected_success=False,
        expected_beep=True,
    ),

    # ── lines ───────────────────────────────────────────────────────

    FlowScenario(
        id="lines_down_success",
        start_state="lines",
        command="down",
        arrange=lambda f: _set_state(f, "lines"),
        expected_state="lines",
        expected_success=True,
    ),
    FlowScenario(
        id="lines_up_boundary",
        start_state="lines",
        command="up",
        arrange=lambda f: _set_state(f, "lines"),
        expected_state="lines",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="lines_confirm",
        start_state="lines",
        command="enter",
        arrange=lambda f: _set_state(f, "lines"),
        expected_state="stations",
        expected_success=True,
    ),
    FlowScenario(
        id="lines_station_command",
        start_state="lines",
        command="s",
        arrange=lambda f: _set_state(f, "lines"),
        expected_state="stations",
        expected_success=True,
    ),

    # ── direction_stations ──────────────────────────────────────────

    FlowScenario(
        id="direction_stations_down_success",
        start_state="direction_stations",
        command="down",
        arrange=lambda f: _set_state(f, "direction_stations"),
        expected_state="direction_stations",
        expected_success=True,
    ),
    FlowScenario(
        id="direction_stations_up_boundary",
        start_state="direction_stations",
        command="up",
        arrange=lambda f: _set_state(f, "direction_stations"),
        expected_state="direction_stations",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="direction_stations_confirm_with_line",
        start_state="direction_stations",
        command="enter",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "line", "blue"),
            _set_state(f, "direction_stations"),
        ),
        expected_state="direction_end_point",
        expected_success=True,
    ),
    FlowScenario(
        id="direction_stations_confirm_without_line",
        start_state="direction_stations",
        command="enter",
        arrange=lambda f: _set_state(f, "direction_stations"),
        expected_state="direction_lines",
        expected_success=True,
    ),
    FlowScenario(
        id="direction_stations_line_command",
        start_state="direction_stations",
        command="l",
        arrange=lambda f: _set_state(f, "direction_stations"),
        expected_state="direction_lines",
        expected_success=True,
    ),

    # ── direction_lines ─────────────────────────────────────────────

    FlowScenario(
        id="direction_lines_down_success",
        start_state="direction_lines",
        command="down",
        arrange=lambda f: _set_state(f, "direction_lines"),
        expected_state="direction_lines",
        expected_success=True,
    ),
    FlowScenario(
        id="direction_lines_up_boundary",
        start_state="direction_lines",
        command="up",
        arrange=lambda f: _set_state(f, "direction_lines"),
        expected_state="direction_lines",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="direction_lines_confirm_with_station",
        start_state="direction_lines",
        command="enter",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "station", "central"),
            _set_state(f, "direction_lines"),
        ),
        expected_state="direction_end_point",
        expected_success=True,
    ),
    FlowScenario(
        id="direction_lines_confirm_without_station",
        start_state="direction_lines",
        command="enter",
        arrange=lambda f: _set_state(f, "direction_lines"),
        expected_state="direction_stations",
        expected_success=True,
    ),
    FlowScenario(
        id="direction_lines_station_command",
        start_state="direction_lines",
        command="s",
        arrange=lambda f: _set_state(f, "direction_lines"),
        expected_state="direction_stations",
        expected_success=True,
    ),
    FlowScenario(
        id="direction_lines_auto_select_single_item",
        start_state="direction_lines",
        command="",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "lines_display", _SINGLE_LINE),
            _set_state(f, "direction_lines"),
        ),
        expected_state="direction_stations",
        expected_success=True,
    ),

    # ── direction_end_point ─────────────────────────────────────────

    FlowScenario(
        id="direction_end_point_down_success",
        start_state="direction_end_point",
        command="down",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "end_points", _MULTI_END_POINTS),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            _set_state(f, "direction_end_point"),
        ),
        expected_state="direction_end_point",
        expected_success=True,
    ),
    FlowScenario(
        id="direction_end_point_up_boundary",
        start_state="direction_end_point",
        command="up",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "end_points", _MULTI_END_POINTS),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            _set_state(f, "direction_end_point"),
        ),
        expected_state="direction_end_point",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="direction_end_point_confirm",
        start_state="direction_end_point",
        command="enter",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            _set_state(f, "direction_end_point"),
        ),
        expected_state="direction_run",
        expected_success=True,
    ),

    # ── direction_run ───────────────────────────────────────────────

    FlowScenario(
        id="direction_run_left_zero_reverse_neighbors",
        start_state="direction_run",
        command="left",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            setattr(f.navigator["direction"], "reverse", []),
            _set_state(f, "direction_run"),
        ),
        expected_state="direction_run",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="direction_run_left_one_reverse_neighbor",
        start_state="direction_run",
        command="left",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            setattr(f.navigator["direction"], "reverse", ["node_prev"]),
            _set_state(f, "direction_run"),
        ),
        expected_state="direction_run",
        expected_success=True,
    ),
    FlowScenario(
        id="direction_run_left_many_reverse_neighbors",
        start_state="direction_run",
        command="left",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            setattr(f.navigator["direction"], "reverse", ["node_a", "node_b"]),
            setattr(f.navigator["direction"], "reverse_display", [
                {"id": "node_a", "label": "Station A"},
                {"id": "node_b", "label": "Station B"},
            ]),
            _set_state(f, "direction_run"),
        ),
        expected_state="explore_neighbor",
        expected_success=True,
    ),
    FlowScenario(
        id="direction_run_right_zero_forward",
        start_state="direction_run",
        command="right",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            setattr(f.navigator["direction"], "forward", []),
            _set_state(f, "direction_run"),
        ),
        expected_state="direction_run",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="direction_run_right_has_forward",
        start_state="direction_run",
        command="right",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            setattr(f.navigator["direction"], "forward", ["node_next"]),
            _set_state(f, "direction_run"),
        ),
        expected_state="direction_run",
        expected_success=True,
    ),
    FlowScenario(
        id="direction_run_transfer_with_zero_options",
        start_state="direction_run",
        command="up",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            setattr(f.navigator["direction"], "transfer_display", []),
            _set_state(f, "direction_run"),
        ),
        expected_state="direction_run",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="direction_run_transfer_with_options",
        start_state="direction_run",
        command="up",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            setattr(f.navigator["direction"], "transfer_display", _TRANSFER_OPTIONS),
            _set_state(f, "direction_run"),
        ),
        expected_state="direction_transfer",
        expected_success=True,
    ),
    FlowScenario(
        id="direction_run_mode",
        start_state="direction_run",
        command="m",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            _set_state(f, "direction_run"),
        ),
        expected_state="mode",
        expected_success=True,
    ),
    FlowScenario(
        id="direction_run_browser",
        start_state="direction_run",
        command="v",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            _set_state(f, "direction_run"),
        ),
        expected_state="lines",
        expected_success=True,
    ),
    FlowScenario(
        id="direction_run_endpoint",
        start_state="direction_run",
        command="e",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            _set_state(f, "direction_run"),
        ),
        expected_state="direction_end_point",
        expected_success=True,
    ),

    # ── undirection_run ─────────────────────────────────────────────

    FlowScenario(
        id="undirection_run_left_no_neighbor",
        start_state="undirection_run",
        command="left",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "sub_line", ("node_a", "node_b")),
            setattr(f.navigator["undirection"], "current", "node_b"),
            setattr(f.navigator["undirection"], "previous", None),
            _set_state(f, "undirection_run"),
        ),
        expected_state="undirection_run",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="undirection_run_left_has_neighbor",
        start_state="undirection_run",
        command="left",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "sub_line", ("node_a", "node_b")),
            setattr(f.navigator["undirection"], "current", "node_b"),
            setattr(f.navigator["undirection"], "previous", "node_a"),
            _set_state(f, "undirection_run"),
        ),
        expected_state="undirection_run",
        expected_success=True,
    ),
    FlowScenario(
        id="undirection_run_right_no_neighbor",
        start_state="undirection_run",
        command="right",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "sub_line", ("node_a", "node_b")),
            setattr(f.navigator["undirection"], "current", "node_b"),
            setattr(f.navigator["undirection"], "next", None),
            _set_state(f, "undirection_run"),
        ),
        expected_state="undirection_run",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="undirection_run_right_has_neighbor",
        start_state="undirection_run",
        command="right",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "sub_line", ("node_a", "node_b")),
            setattr(f.navigator["undirection"], "current", "node_a"),
            setattr(f.navigator["undirection"], "next", "node_b"),
            _set_state(f, "undirection_run"),
        ),
        expected_state="undirection_run",
        expected_success=True,
    ),
    FlowScenario(
        id="undirection_run_transfer_zero_options",
        start_state="undirection_run",
        command="up",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "sub_line", ("node_a", "node_b")),
            setattr(f.navigator["undirection"], "current", "node_a"),
            setattr(f.navigator["undirection"], "transfer_display", []),
            _set_state(f, "undirection_run"),
        ),
        expected_state="undirection_run",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="undirection_run_transfer_has_options",
        start_state="undirection_run",
        command="up",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "sub_line", ("node_a", "node_b")),
            setattr(f.navigator["undirection"], "current", "node_a"),
            setattr(f.navigator["undirection"], "transfer_display", _TRANSFER_OPTIONS),
            _set_state(f, "undirection_run"),
        ),
        expected_state="undirection_transfer",
        expected_success=True,
    ),
    FlowScenario(
        id="undirection_run_mode",
        start_state="undirection_run",
        command="m",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "sub_line", ("node_a", "node_b")),
            setattr(f.navigator["undirection"], "current", "node_a"),
            _set_state(f, "undirection_run"),
        ),
        expected_state="mode",
        expected_success=True,
    ),
    FlowScenario(
        id="undirection_run_browser",
        start_state="undirection_run",
        command="v",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "sub_line", ("node_a", "node_b")),
            setattr(f.navigator["undirection"], "current", "node_a"),
            _set_state(f, "undirection_run"),
        ),
        expected_state="lines",
        expected_success=True,
    ),

    # ── plan_run ────────────────────────────────────────────────────

    FlowScenario(
        id="plan_run_left_no_neighbor",
        start_state="plan_run",
        command="left",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            setattr(f.navigator["direction"], "previous", None),
            _set_state(f, "plan_run"),
        ),
        expected_state="plan_run",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="plan_run_left_has_neighbor",
        start_state="plan_run",
        command="left",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_east"),
            setattr(f.navigator["direction"], "previous", "node_central_blue"),
            _set_state(f, "plan_run"),
        ),
        expected_state="plan_run",
        expected_success=True,
    ),
    FlowScenario(
        id="plan_run_right_no_neighbor",
        start_state="plan_run",
        command="right",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_north"),
            setattr(f.navigator["direction"], "next", None),
            _set_state(f, "plan_run"),
        ),
        expected_state="plan_run",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="plan_run_right_has_neighbor",
        start_state="plan_run",
        command="right",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            setattr(f.navigator["direction"], "next", "node_east"),
            _set_state(f, "plan_run"),
        ),
        expected_state="plan_run",
        expected_success=True,
    ),
    FlowScenario(
        id="plan_run_mode",
        start_state="plan_run",
        command="m",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            _set_state(f, "plan_run"),
        ),
        expected_state="mode",
        expected_success=True,
    ),
    FlowScenario(
        id="plan_run_browser",
        start_state="plan_run",
        command="v",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            _set_state(f, "plan_run"),
        ),
        expected_state="lines",
        expected_success=True,
    ),

    # ── direction_transfer ──────────────────────────────────────────

    FlowScenario(
        id="direction_transfer_confirm",
        start_state="direction_transfer",
        command="enter",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            setattr(f.navigator["direction"], "transfer_display", _TRANSFER_OPTIONS),
            setattr(f.navigator["direction"], "destination_display", {"label": {"line": "Red Line", "name": "South"}}),
            _set_state(f, "direction_transfer"),
        ),
        expected_state="direction_run",
        expected_success=True,
    ),
    FlowScenario(
        id="direction_transfer_quit",
        start_state="direction_transfer",
        command="q",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            setattr(f.navigator["direction"], "transfer_display", _TRANSFER_OPTIONS),
            setattr(f.navigator["direction"], "destination_display", {"label": {"line": "Red Line", "name": "South"}}),
            _set_state(f, "direction_transfer"),
        ),
        expected_state="direction_run",
        expected_success=True,
    ),
    FlowScenario(
        id="direction_transfer_down_success",
        start_state="direction_transfer",
        command="down",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "transfer_display", _TRANSFER_OPTIONS * 2),
            setattr(f.navigator["direction"], "destination_display", {"label": {"line": "Red", "name": "South"}}),
            _set_state(f, "direction_transfer"),
        ),
        expected_state="direction_transfer",
        expected_success=True,
    ),
    FlowScenario(
        id="direction_transfer_up_boundary",
        start_state="direction_transfer",
        command="up",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "transfer_display", _TRANSFER_OPTIONS),
            setattr(f.navigator["direction"], "destination_display", {"label": {"line": "Red", "name": "South"}}),
            _set_state(f, "direction_transfer"),
        ),
        expected_state="direction_transfer",
        expected_success=False,
        expected_beep=True,
    ),

    # ── undirection_transfer ────────────────────────────────────────

    FlowScenario(
        id="undirection_transfer_confirm",
        start_state="undirection_transfer",
        command="enter",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "sub_line", ("node_a", "node_b")),
            setattr(f.navigator["undirection"], "current", "node_a"),
            setattr(f.navigator["undirection"], "transfer_display", [
                {"id": {"sub_line": ("node_a", "node_b"), "current": "node_a"}, "label": "Central to East"},
                {"id": {"sub_line": ("node_c", "node_d"), "current": "node_c"}, "label": "West to North"},
            ]),
            setattr(f.navigator["undirection"], "line_name_display", {"label": "Blue Line"}),
            setattr(f.navigator["undirection"], "left_point_name_display", {"label": "Central"}),
            setattr(f.navigator["undirection"], "right_point_name_display", {"label": "East"}),
            _set_state(f, "undirection_transfer"),
        ),
        expected_state="undirection_run",
        expected_success=True,
    ),
    FlowScenario(
        id="undirection_transfer_quit",
        start_state="undirection_transfer",
        command="q",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "sub_line", ("node_a", "node_b")),
            setattr(f.navigator["undirection"], "current", "node_a"),
            setattr(f.navigator["undirection"], "transfer_display", [
                {"id": {"sub_line": ("node_a", "node_b"), "current": "node_a"}, "label": "Central to East"},
            ]),
            _set_state(f, "undirection_transfer"),
        ),
        expected_state="undirection_run",
        expected_success=True,
    ),
    FlowScenario(
        id="undirection_transfer_down_success",
        start_state="undirection_transfer",
        command="down",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "transfer_display", _TRANSFER_OPTIONS * 2),
            _set_state(f, "undirection_transfer"),
        ),
        expected_state="undirection_transfer",
        expected_success=True,
    ),
    FlowScenario(
        id="undirection_transfer_up_boundary",
        start_state="undirection_transfer",
        command="up",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "transfer_display", _TRANSFER_OPTIONS),
            _set_state(f, "undirection_transfer"),
        ),
        expected_state="undirection_transfer",
        expected_success=False,
        expected_beep=True,
    ),

    # ── explore_neighbor ────────────────────────────────────────────

    FlowScenario(
        id="explore_neighbor_confirm",
        start_state="explore_neighbor",
        command="enter",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "reverse", ["node_a", "node_b"]),
            setattr(f.navigator["direction"], "reverse_display", [
                {"id": "node_a", "label": "Station A"},
                {"id": "node_b", "label": "Station B"},
            ]),
            _set_state(f, "explore_neighbor"),
        ),
        expected_state="direction_run",
        expected_success=True,
    ),
    FlowScenario(
        id="explore_neighbor_quit",
        start_state="explore_neighbor",
        command="q",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "reverse", ["node_a", "node_b"]),
            setattr(f.navigator["direction"], "reverse_display", [
                {"id": "node_a", "label": "Station A"},
            ]),
            _set_state(f, "explore_neighbor"),
        ),
        expected_state="direction_run",
        expected_success=True,
    ),
    FlowScenario(
        id="explore_neighbor_down_success",
        start_state="explore_neighbor",
        command="down",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "reverse", ["node_a", "node_b"]),
            setattr(f.navigator["direction"], "reverse_display", [
                {"id": "node_a", "label": "Station A"},
                {"id": "node_b", "label": "Station B"},
            ]),
            _set_state(f, "explore_neighbor"),
        ),
        expected_state="explore_neighbor",
        expected_success=True,
    ),
    FlowScenario(
        id="explore_neighbor_up_boundary",
        start_state="explore_neighbor",
        command="up",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "reverse", ["node_a", "node_b"]),
            setattr(f.navigator["direction"], "reverse_display", [
                {"id": "node_a", "label": "Station A"},
            ]),
            _set_state(f, "explore_neighbor"),
        ),
        expected_state="explore_neighbor",
        expected_success=False,
        expected_beep=True,
    ),

    # ── explore_sub_line ────────────────────────────────────────────

    FlowScenario(
        id="explore_sub_line_confirm",
        start_state="explore_sub_line",
        command="enter",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "transfer_display", [
                {"id": ("node_a", "node_b"), "label": "Central to East"},
            ]),
            setattr(f.navigator["undirection"], "mode", "center"),
            _set_state(f, "explore_sub_line"),
        ),
        expected_state="undirection_run",
        expected_success=True,
    ),
    FlowScenario(
        id="explore_sub_line_quit",
        start_state="explore_sub_line",
        command="q",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "transfer_display", [
                {"id": ("node_a", "node_b"), "label": "Central to East"},
            ]),
            _set_state(f, "explore_sub_line"),
        ),
        expected_state="undirection_run",
        expected_success=True,
    ),
    FlowScenario(
        id="explore_sub_line_down_success",
        start_state="explore_sub_line",
        command="down",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "transfer_display", [
                {"id": ("node_a", "node_b"), "label": "Central to East"},
                {"id": ("node_c", "node_d"), "label": "East to North"},
            ]),
            _set_state(f, "explore_sub_line"),
        ),
        expected_state="explore_sub_line",
        expected_success=True,
    ),
    FlowScenario(
        id="explore_sub_line_up_boundary",
        start_state="explore_sub_line",
        command="up",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "transfer_display", [
                {"id": ("node_a", "node_b"), "label": "Central to East"},
            ]),
            _set_state(f, "explore_sub_line"),
        ),
        expected_state="explore_sub_line",
        expected_success=False,
        expected_beep=True,
    ),

    # ── undirection_stations ────────────────────────────────────────

    FlowScenario(
        id="undirection_stations_down_success",
        start_state="undirection_stations",
        command="down",
        arrange=lambda f: _set_state(f, "undirection_stations"),
        expected_state="undirection_stations",
        expected_success=True,
    ),
    FlowScenario(
        id="undirection_stations_up_boundary",
        start_state="undirection_stations",
        command="up",
        arrange=lambda f: _set_state(f, "undirection_stations"),
        expected_state="undirection_stations",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="undirection_stations_confirm_with_line",
        start_state="undirection_stations",
        command="enter",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "line", "blue"),
            _set_state(f, "undirection_stations"),
        ),
        expected_state="undirection_sub_lines",
        expected_success=True,
    ),
    FlowScenario(
        id="undirection_stations_confirm_without_line",
        start_state="undirection_stations",
        command="enter",
        arrange=lambda f: _set_state(f, "undirection_stations"),
        expected_state="undirection_lines",
        expected_success=True,
    ),
    FlowScenario(
        id="undirection_stations_line_command",
        start_state="undirection_stations",
        command="l",
        arrange=lambda f: _set_state(f, "undirection_stations"),
        expected_state="undirection_lines",
        expected_success=True,
    ),

    # ── undirection_lines ───────────────────────────────────────────

    FlowScenario(
        id="undirection_lines_down_success",
        start_state="undirection_lines",
        command="down",
        arrange=lambda f: _set_state(f, "undirection_lines"),
        expected_state="undirection_lines",
        expected_success=True,
    ),
    FlowScenario(
        id="undirection_lines_up_boundary",
        start_state="undirection_lines",
        command="up",
        arrange=lambda f: _set_state(f, "undirection_lines"),
        expected_state="undirection_lines",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="undirection_lines_confirm_with_station",
        start_state="undirection_lines",
        command="enter",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "station", "central"),
            _set_state(f, "undirection_lines"),
        ),
        expected_state="undirection_sub_lines",
        expected_success=True,
    ),
    FlowScenario(
        id="undirection_lines_confirm_without_station",
        start_state="undirection_lines",
        command="enter",
        arrange=lambda f: _set_state(f, "undirection_lines"),
        expected_state="undirection_stations",
        expected_success=True,
    ),
    FlowScenario(
        id="undirection_lines_station_command",
        start_state="undirection_lines",
        command="s",
        arrange=lambda f: _set_state(f, "undirection_lines"),
        expected_state="undirection_stations",
        expected_success=True,
    ),
    FlowScenario(
        id="undirection_lines_auto_select_single_item",
        start_state="undirection_lines",
        command="",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "lines_display", _SINGLE_LINE),
            _set_state(f, "undirection_lines"),
        ),
        expected_state="undirection_stations",
        expected_success=True,
    ),

    # ── undirection_sub_lines ───────────────────────────────────────

    FlowScenario(
        id="undirection_sub_lines_down_success",
        start_state="undirection_sub_lines",
        command="down",
        arrange=lambda f: _set_state(f, "undirection_sub_lines"),
        expected_state="undirection_sub_lines",
        expected_success=True,
    ),
    FlowScenario(
        id="undirection_sub_lines_up_boundary",
        start_state="undirection_sub_lines",
        command="up",
        arrange=lambda f: _set_state(f, "undirection_sub_lines"),
        expected_state="undirection_sub_lines",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="undirection_sub_lines_confirm",
        start_state="undirection_sub_lines",
        command="enter",
        arrange=lambda f: (
            setattr(f.navigator["undirection"], "station", "central"),
            setattr(f.navigator["undirection"], "line", "blue"),
            _set_state(f, "undirection_sub_lines"),
        ),
        expected_state="undirection_run",
        expected_success=True,
    ),

    # ── source_stations ─────────────────────────────────────────────

    FlowScenario(
        id="source_stations_down_success",
        start_state="source_stations",
        command="down",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "stations_display", _MULTI_STATIONS),
            _set_state(f, "source_stations"),
        ),
        expected_state="source_stations",
        expected_success=True,
    ),
    FlowScenario(
        id="source_stations_up_boundary",
        start_state="source_stations",
        command="up",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "stations_display", _MULTI_STATIONS),
            _set_state(f, "source_stations"),
        ),
        expected_state="source_stations",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="source_stations_confirm_with_line",
        start_state="source_stations",
        command="enter",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "line", "blue"),
            setattr(f.navigator["direction"], "stations_display", _MULTI_STATIONS),
            _set_state(f, "source_stations"),
        ),
        expected_state="destination_lines",
        expected_success=True,
    ),
    FlowScenario(
        id="source_stations_confirm_without_line",
        start_state="source_stations",
        command="enter",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "stations_display", _MULTI_STATIONS),
            _set_state(f, "source_stations"),
        ),
        expected_state="source_lines",
        expected_success=True,
    ),
    FlowScenario(
        id="source_stations_line_command",
        start_state="source_stations",
        command="l",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "stations_display", _MULTI_STATIONS),
            _set_state(f, "source_stations"),
        ),
        expected_state="source_lines",
        expected_success=True,
    ),
    FlowScenario(
        id="source_stations_auto_select_single_item",
        start_state="source_stations",
        command="",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "stations_display", _SINGLE_STATION),
            _set_state(f, "source_stations"),
        ),
        expected_state="source_lines",
        expected_success=True,
    ),

    # ── source_lines ────────────────────────────────────────────────

    FlowScenario(
        id="source_lines_down_success",
        start_state="source_lines",
        command="down",
        arrange=lambda f: _set_state(f, "source_lines"),
        expected_state="source_lines",
        expected_success=True,
    ),
    FlowScenario(
        id="source_lines_up_boundary",
        start_state="source_lines",
        command="up",
        arrange=lambda f: _set_state(f, "source_lines"),
        expected_state="source_lines",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="source_lines_confirm_with_station",
        start_state="source_lines",
        command="enter",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "station", "central"),
            _set_state(f, "source_lines"),
        ),
        expected_state="destination_lines",
        expected_success=True,
    ),
    FlowScenario(
        id="source_lines_confirm_without_station",
        start_state="source_lines",
        command="enter",
        arrange=lambda f: _set_state(f, "source_lines"),
        expected_state="source_stations",
        expected_success=True,
    ),
    FlowScenario(
        id="source_lines_station_command",
        start_state="source_lines",
        command="s",
        arrange=lambda f: _set_state(f, "source_lines"),
        expected_state="source_stations",
        expected_success=True,
    ),
    FlowScenario(
        id="source_lines_auto_select_single_item",
        start_state="source_lines",
        command="",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "lines_display", _SINGLE_LINE),
            _set_state(f, "source_lines"),
        ),
        expected_state="source_stations",
        expected_success=True,
    ),

    # ── destination_stations ────────────────────────────────────────

    FlowScenario(
        id="destination_stations_down_success",
        start_state="destination_stations",
        command="down",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "stations_display", _MULTI_STATIONS),
            _set_state(f, "destination_stations"),
        ),
        expected_state="destination_stations",
        expected_success=True,
    ),
    FlowScenario(
        id="destination_stations_up_boundary",
        start_state="destination_stations",
        command="up",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "stations_display", _MULTI_STATIONS),
            _set_state(f, "destination_stations"),
        ),
        expected_state="destination_stations",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="destination_stations_confirm_with_line",
        start_state="destination_stations",
        command="enter",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "line", "blue"),
            setattr(f.navigator["direction"], "stations_display", _MULTI_STATIONS),
            _set_state(f, "destination_stations"),
        ),
        expected_state="plan_run",
        expected_success=True,
    ),
    FlowScenario(
        id="destination_stations_confirm_without_line",
        start_state="destination_stations",
        command="enter",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "stations_display", _MULTI_STATIONS),
            _set_state(f, "destination_stations"),
        ),
        expected_state="destination_lines",
        expected_success=True,
    ),
    FlowScenario(
        id="destination_stations_line_command",
        start_state="destination_stations",
        command="l",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "stations_display", _MULTI_STATIONS),
            _set_state(f, "destination_stations"),
        ),
        expected_state="destination_lines",
        expected_success=True,
    ),
    FlowScenario(
        id="destination_stations_auto_select_single_item",
        start_state="destination_stations",
        command="",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "stations_display", _SINGLE_STATION),
            _set_state(f, "destination_stations"),
        ),
        expected_state="destination_lines",
        expected_success=True,
    ),

    # ── destination_lines ───────────────────────────────────────────

    FlowScenario(
        id="destination_lines_down_success",
        start_state="destination_lines",
        command="down",
        arrange=lambda f: _set_state(f, "destination_lines"),
        expected_state="destination_lines",
        expected_success=True,
    ),
    FlowScenario(
        id="destination_lines_up_boundary",
        start_state="destination_lines",
        command="up",
        arrange=lambda f: _set_state(f, "destination_lines"),
        expected_state="destination_lines",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="destination_lines_confirm_with_station",
        start_state="destination_lines",
        command="enter",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "station", "central"),
            _set_state(f, "destination_lines"),
        ),
        expected_state="plan_run",
        expected_success=True,
    ),
    FlowScenario(
        id="destination_lines_confirm_without_station",
        start_state="destination_lines",
        command="enter",
        arrange=lambda f: _set_state(f, "destination_lines"),
        expected_state="destination_stations",
        expected_success=True,
    ),
    FlowScenario(
        id="destination_lines_station_command",
        start_state="destination_lines",
        command="s",
        arrange=lambda f: _set_state(f, "destination_lines"),
        expected_state="destination_stations",
        expected_success=True,
    ),
    FlowScenario(
        id="destination_lines_auto_select_single_item",
        start_state="destination_lines",
        command="",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "lines_display", _SINGLE_LINE),
            _set_state(f, "destination_lines"),
        ),
        expected_state="destination_stations",
        expected_success=True,
    ),

    # ── help ────────────────────────────────────────────────────────

    FlowScenario(
        id="help_enter_from_stations",
        start_state="help",
        command="",
        arrange=lambda f: _enter_help(f, "stations"),
        expected_state="help",
        expected_success=True,
    ),
    FlowScenario(
        id="help_down_success",
        start_state="help",
        command="down",
        arrange=lambda f: _enter_help(f, "direction_run"),
        expected_state="help",
        expected_success=True,
    ),
    FlowScenario(
        id="help_up_boundary",
        start_state="help",
        command="up",
        arrange=lambda f: _enter_help(f, "direction_run"),
        expected_state="help",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="help_confirm_invokes_help_item",
        start_state="help",
        command="enter",
        arrange=lambda f: _enter_help(f, "direction_run"),
        expected_state="mode",
        expected_success=True,
    ),
    FlowScenario(
        id="help_quit_returns_to_calling_state",
        start_state="help",
        command="q",
        arrange=lambda f: _enter_help(f, "direction_run"),
        expected_state="direction_run",
        expected_success=True,
    ),

    # ── mode / undirected browser return via background_state ──────

    FlowScenario(
        id="stations_home_success",
        start_state="stations",
        command="home",
        arrange=lambda f: _set_state(f, "stations"),
        expected_state="stations",
        expected_success=True,
    ),
    FlowScenario(
        id="stations_end_success",
        start_state="stations",
        command="end",
        arrange=lambda f: _set_state(f, "stations"),
        expected_state="stations",
        expected_success=True,
    ),
    FlowScenario(
        id="direction_run_help_h",
        start_state="direction_run",
        command="h",
        arrange=lambda f: (
            setattr(f.navigator["direction"], "source", "node_central_blue"),
            setattr(f.navigator["direction"], "destination", "node_north"),
            setattr(f.navigator["direction"], "current", "node_central_blue"),
            _set_state(f, "direction_run"),
        ),
        expected_state="help",
        expected_success=True,
    ),
    FlowScenario(
        id="mode_rejected_unknown_key",
        start_state="mode",
        command="xyzzy",
        arrange=lambda f: None,
        expected_state="mode",
        expected_success=False,
        expected_beep=True,
    ),
    FlowScenario(
        id="mode_rejected_help_from_mode",
        start_state="mode",
        command="h",
        arrange=lambda f: None,
        expected_state="mode",
        expected_success=False,
        expected_beep=True,
    ),
)
