from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from apps.access8graph.navigation.model import (
    ActionId,
    ActionResult,
    GuardId,
    NavigationCommand,
    NavigationContext,
    NavigationStateId,
    PresentationEffects,
)

# ---------------------------------------------------------------------------
# View Models
# ---------------------------------------------------------------------------


@dataclass
class ListViewModel:
    items: tuple[dict[str, Any], ...]
    current_index: int = 0
    hint: str = ""

    @property
    def selected_id(self) -> Any | None:
        if 0 <= self.current_index < len(self.items):
            item = self.items[self.current_index]
            raw = item.get("id")
            if raw is None:
                return None
            return raw
        return None

    @property
    def option_count(self) -> int:
        return len(self.items)

    @property
    def attribute(self) -> str:
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index].get("attribute", "")
        return ""

    @property
    def label(self) -> str:
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index].get("label", "")
        return ""

    @property
    def description(self) -> str:
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index].get("description", "")
        return ""

    @property
    def position(self) -> str:
        n = len(self.items)
        if n > 0:
            return f"{n} 之 {self.current_index + 1}"
        return ""

    @property
    def display(self) -> list[str]:
        return [self.attribute, self.label, self.description, self.position]

    @property
    def display_items(self) -> list[str]:
        return [item for item in self.display if item]

    def move_up(self) -> bool:
        if self.option_count == 0:
            return False
        if self.current_index <= 0:
            return False
        self.current_index -= 1
        return True

    def move_down(self) -> bool:
        if self.option_count == 0:
            return False
        if self.current_index >= self.option_count - 1:
            return False
        self.current_index += 1
        return True

    def move_home(self) -> bool:
        self.current_index = 0
        return True

    def move_end(self) -> bool:
        if self.option_count > 0:
            self.current_index = self.option_count - 1
        return True

    @classmethod
    def build(
        cls,
        data: list[dict[str, Any]],
        hint: str = "",
    ) -> ListViewModel:
        return cls(items=tuple(data), current_index=0, hint=hint)


@dataclass
class RunViewModel:
    current_data: dict[str, Any] = field(default_factory=dict)
    transfer_data: tuple[dict[str, Any], ...] = ()
    hint: str = ""

    @property
    def selected_id(self) -> Any | None:
        raw = self.current_data.get("id")
        if raw is None:
            return None
        return raw

    @property
    def attribute(self) -> str:
        return self.current_data.get("attribute", "")

    @property
    def label(self) -> str:
        return self.current_data.get("label", "")

    @property
    def description(self) -> str:
        return self.current_data.get("description", "")

    @property
    def extra(self) -> str:
        if len(self.transfer_data) > 0:
            return "可轉乘，如要轉乘請用上下鍵瀏覽並選擇項目"
        return ""

    @property
    def display(self) -> list[str]:
        return [self.attribute, self.label, self.description, self.extra]

    @property
    def display_items(self) -> list[str]:
        return [item for item in self.display if item]


# ---------------------------------------------------------------------------
# ActionId constants
# ---------------------------------------------------------------------------

A_NOOP = ActionId("noop")
A_LIST_MOVE_UP = ActionId("list_move_up")
A_LIST_MOVE_DOWN = ActionId("list_move_down")
A_LIST_MOVE_HOME = ActionId("list_move_home")
A_LIST_MOVE_END = ActionId("list_move_end")

A_SELECT_DIRECTION = ActionId("select_direction")
A_SELECT_UNDIRECTED = ActionId("select_undirected")
A_SELECT_PLAN = ActionId("select_plan")

A_STATIONS_CONFIRM = ActionId("stations_confirm")
A_LINES_CONFIRM = ActionId("lines_confirm")

A_DIRECTION_STATIONS_CONFIRM = ActionId("direction_stations_confirm")
A_DIRECTION_LINES_CONFIRM = ActionId("direction_lines_confirm")
A_DIRECTION_END_POINT_CONFIRM = ActionId("direction_end_point_confirm")

A_UNDIRECTION_STATIONS_CONFIRM = ActionId("undirection_stations_confirm")
A_UNDIRECTION_LINES_CONFIRM = ActionId("undirection_lines_confirm")
A_UNDIRECTION_SUB_LINES_CONFIRM = ActionId("undirection_sub_lines_confirm")

A_SOURCE_STATIONS_CONFIRM = ActionId("source_stations_confirm")
A_SOURCE_LINES_CONFIRM = ActionId("source_lines_confirm")
A_DESTINATION_STATIONS_CONFIRM = ActionId("destination_stations_confirm")
A_DESTINATION_LINES_CONFIRM = ActionId("destination_lines_confirm")

A_DIRECTION_LEFT = ActionId("direction_left")
A_DIRECTION_RIGHT = ActionId("direction_right")
A_UNDIRECTION_LEFT = ActionId("undirection_left")
A_UNDIRECTION_RIGHT = ActionId("undirection_right")
A_PLAN_LEFT = ActionId("plan_left")
A_PLAN_RIGHT = ActionId("plan_right")

A_DIRECTION_TRANSFER_UP = ActionId("direction_transfer_up")
A_DIRECTION_TRANSFER_DOWN = ActionId("direction_transfer_down")
A_DIRECTION_TRANSFER_CONFIRM = ActionId("direction_transfer_confirm")
A_DIRECTION_TRANSFER_QUIT = ActionId("direction_transfer_quit")

A_UNDIRECTION_TRANSFER_UP = ActionId("undirection_transfer_up")
A_UNDIRECTION_TRANSFER_DOWN = ActionId("undirection_transfer_down")
A_UNDIRECTION_TRANSFER_CONFIRM = ActionId("undirection_transfer_confirm")
A_UNDIRECTION_TRANSFER_QUIT = ActionId("undirection_transfer_quit")

A_EXPLORE_NEIGHBOR_CONFIRM = ActionId("explore_neighbor_confirm")
A_EXPLORE_NEIGHBOR_QUIT = ActionId("explore_neighbor_quit")
A_EXPLORE_SUB_LINE_CONFIRM = ActionId("explore_sub_line_confirm")
A_EXPLORE_SUB_LINE_QUIT = ActionId("explore_sub_line_quit")

A_RUN_MODE = ActionId("run_mode")
A_RUN_BROWSER = ActionId("run_browser")
A_DIRECTION_RUN_ENDPOINT = ActionId("direction_run_endpoint")

A_HELP_CONFIRM = ActionId("help_confirm")
A_HELP_QUIT = ActionId("help_quit")
A_DIRECTION_RUN_UP = ActionId("direction_run_up")
A_DIRECTION_RUN_DOWN = ActionId("direction_run_down")
A_UNDIRECTION_RUN_UP = ActionId("undirection_run_up")
A_UNDIRECTION_RUN_DOWN = ActionId("undirection_run_down")
A_OPEN_HELP = ActionId("open_help")

A_LIST_LINE_COMMAND = ActionId("list_line_command")
A_LIST_STATION_COMMAND = ActionId("list_station_command")

A_MODE_QUIT = ActionId("mode_quit")
A_STATIONS_QUIT = ActionId("stations_quit")
A_LINES_QUIT = ActionId("lines_quit")

A_DIRECTION_LINES_AUTO = ActionId("direction_lines_auto")
A_UNDIRECTION_LINES_AUTO = ActionId("undirection_lines_auto")
A_SOURCE_STATIONS_AUTO = ActionId("source_stations_auto")
A_SOURCE_LINES_AUTO = ActionId("source_lines_auto")
A_DESTINATION_STATIONS_AUTO = ActionId("destination_stations_auto")
A_DESTINATION_LINES_AUTO = ActionId("destination_lines_auto")


# ---------------------------------------------------------------------------
# GuardId constants
# ---------------------------------------------------------------------------

G_CAN_MOVE_UP = GuardId("can_move_up")
G_CAN_MOVE_DOWN = GuardId("can_move_down")

G_IS_DIRECTION_SELECTED = GuardId("is_direction_selected")
G_IS_UNDIRECTION_SELECTED = GuardId("is_undirection_selected")
G_IS_PLAN_SELECTED = GuardId("is_plan_selected")

G_HAS_ONE_OPTION = GuardId("has_one_option")
G_HAS_LINE = GuardId("has_line")
G_HAS_STATION = GuardId("has_station")
G_HAS_SOURCE = GuardId("has_source")
G_HAS_DEST = GuardId("has_dest")
G_HAS_NO_LINE = GuardId("has_no_line")
G_HAS_NO_STATION = GuardId("has_no_station")

G_HAS_NO_REVERSE = GuardId("has_no_reverse")
G_HAS_ONE_REVERSE = GuardId("has_one_reverse")
G_HAS_MULTI_REVERSE = GuardId("has_multi_reverse")
G_HAS_NO_FORWARD = GuardId("has_no_forward")
G_HAS_FORWARD = GuardId("has_forward")

G_HAS_TRANSFER = GuardId("has_transfer")
G_HAS_NO_TRANSFER = GuardId("has_no_transfer")
G_RUN_ACTIVE = GuardId("run_active")

G_RETURN_IS_DIRECTION_RUN = GuardId("return_is_direction_run")
G_RETURN_IS_PLAN_RUN = GuardId("return_is_plan_run")
G_RETURN_IS_UNDIRECTION_RUN = GuardId("return_is_undirection_run")
G_RETURN_IS_STATIONS = GuardId("return_is_stations")
G_RETURN_IS_LINES = GuardId("return_is_lines")
G_RETURN_IS_DIRECTION_STATIONS = GuardId("return_is_direction_stations")
G_RETURN_IS_DIRECTION_LINES = GuardId("return_is_direction_lines")
G_RETURN_IS_UNDIRECTION_STATIONS = GuardId("return_is_undirection_stations")
G_RETURN_IS_UNDIRECTION_LINES = GuardId("return_is_undirection_lines")
G_RETURN_IS_SOURCE_STATIONS = GuardId("return_is_source_stations")
G_RETURN_IS_SOURCE_LINES = GuardId("return_is_source_lines")
G_RETURN_IS_DESTINATION_STATIONS = GuardId("return_is_destination_stations")
G_RETURN_IS_DESTINATION_LINES = GuardId("return_is_destination_lines")

G_HAS_PREVIOUS = GuardId("has_previous")
G_HAS_NO_PREVIOUS = GuardId("has_no_previous")
G_HAS_NEXT = GuardId("has_next")
G_HAS_NO_NEXT = GuardId("has_no_next")

G_HELP_SELECTED_MODE = GuardId("help_selected_mode")
G_HELP_SELECTED_BROWSER = GuardId("help_selected_browser")
G_HELP_SELECTED_STATION = GuardId("help_selected_station")
G_HELP_SELECTED_LINE = GuardId("help_selected_line")
G_HELP_SELECTED_ENDPOINT = GuardId("help_selected_endpoint")

HELP_CONFIRM_GUARDS = {
    (return_state, selected_id): GuardId(
        f"help_{return_state.value}_selected_{selected_id}"
    )
    for return_state, selected_id in (
        (NavigationStateId.STATIONS, "l"),
        (NavigationStateId.LINES, "s"),
        (NavigationStateId.DIRECTION_STATIONS, "l"),
        (NavigationStateId.DIRECTION_LINES, "s"),
        (NavigationStateId.UNDIRECTION_STATIONS, "l"),
        (NavigationStateId.UNDIRECTION_LINES, "s"),
        (NavigationStateId.SOURCE_STATIONS, "l"),
        (NavigationStateId.SOURCE_LINES, "s"),
        (NavigationStateId.DESTINATION_STATIONS, "l"),
        (NavigationStateId.DESTINATION_LINES, "s"),
        (NavigationStateId.DIRECTION_RUN, "m"),
        (NavigationStateId.DIRECTION_RUN, "v"),
        (NavigationStateId.UNDIRECTION_RUN, "m"),
        (NavigationStateId.UNDIRECTION_RUN, "v"),
        (NavigationStateId.PLAN_RUN, "m"),
        (NavigationStateId.PLAN_RUN, "v"),
    )
}

G_UNDIRECTION_LEFT_HAS_NEXT = GuardId("undirection_left_has_next")
G_UNDIRECTION_LEFT_NO_NEXT_EXTRA = GuardId("undirection_left_no_next_extra")

G_UNDIRECTION_RIGHT_HAS_NEXT = GuardId("undirection_right_has_next")
G_UNDIRECTION_RIGHT_NO_NEXT_EXTRA = GuardId("undirection_right_no_next_extra")

G_HAS_SUB_LINE_TRANSFER = GuardId("has_sub_line_transfer")
G_HAS_NO_SUB_LINE_TRANSFER = GuardId("has_no_sub_line_transfer")


ALL_GUARD_IDS = frozenset({
    G_CAN_MOVE_UP,
    G_CAN_MOVE_DOWN,
    G_IS_DIRECTION_SELECTED,
    G_IS_UNDIRECTION_SELECTED,
    G_IS_PLAN_SELECTED,
    G_HAS_ONE_OPTION,
    G_HAS_LINE,
    G_HAS_STATION,
    G_HAS_SOURCE,
    G_HAS_DEST,
    G_HAS_NO_LINE,
    G_HAS_NO_STATION,
    G_HAS_NO_REVERSE,
    G_HAS_ONE_REVERSE,
    G_HAS_MULTI_REVERSE,
    G_HAS_NO_FORWARD,
    G_HAS_FORWARD,
    G_HAS_TRANSFER,
    G_HAS_NO_TRANSFER,
    G_RUN_ACTIVE,
    G_RETURN_IS_DIRECTION_RUN,
    G_RETURN_IS_PLAN_RUN,
    G_RETURN_IS_UNDIRECTION_RUN,
    G_RETURN_IS_STATIONS,
    G_RETURN_IS_LINES,
    G_RETURN_IS_DIRECTION_STATIONS,
    G_RETURN_IS_DIRECTION_LINES,
    G_RETURN_IS_UNDIRECTION_STATIONS,
    G_RETURN_IS_UNDIRECTION_LINES,
    G_RETURN_IS_SOURCE_STATIONS,
    G_RETURN_IS_SOURCE_LINES,
    G_RETURN_IS_DESTINATION_STATIONS,
    G_RETURN_IS_DESTINATION_LINES,
    G_HAS_PREVIOUS,
    G_HAS_NO_PREVIOUS,
    G_HAS_NEXT,
    G_HAS_NO_NEXT,
    G_HELP_SELECTED_MODE,
    G_HELP_SELECTED_BROWSER,
    G_HELP_SELECTED_STATION,
    G_HELP_SELECTED_LINE,
    G_HELP_SELECTED_ENDPOINT,
    *HELP_CONFIRM_GUARDS.values(),
    G_UNDIRECTION_LEFT_HAS_NEXT,
    G_UNDIRECTION_LEFT_NO_NEXT_EXTRA,
    G_UNDIRECTION_RIGHT_HAS_NEXT,
    G_UNDIRECTION_RIGHT_NO_NEXT_EXTRA,
    G_HAS_SUB_LINE_TRANSFER,
    G_HAS_NO_SUB_LINE_TRANSFER,
})

ALL_ACTION_IDS = frozenset((
    A_LIST_MOVE_UP,
    A_LIST_MOVE_DOWN,
    A_LIST_MOVE_HOME,
    A_LIST_MOVE_END,
    A_SELECT_DIRECTION,
    A_SELECT_UNDIRECTED,
    A_SELECT_PLAN,
    A_STATIONS_CONFIRM,
    A_LINES_CONFIRM,
    A_DIRECTION_STATIONS_CONFIRM,
    A_DIRECTION_LINES_CONFIRM,
    A_DIRECTION_END_POINT_CONFIRM,
    A_UNDIRECTION_STATIONS_CONFIRM,
    A_UNDIRECTION_LINES_CONFIRM,
    A_UNDIRECTION_SUB_LINES_CONFIRM,
    A_SOURCE_STATIONS_CONFIRM,
    A_SOURCE_LINES_CONFIRM,
    A_DESTINATION_STATIONS_CONFIRM,
    A_DESTINATION_LINES_CONFIRM,
    A_DIRECTION_LEFT,
    A_DIRECTION_RIGHT,
    A_UNDIRECTION_LEFT,
    A_UNDIRECTION_RIGHT,
    A_PLAN_LEFT,
    A_PLAN_RIGHT,
    A_DIRECTION_TRANSFER_UP,
    A_DIRECTION_TRANSFER_DOWN,
    A_DIRECTION_TRANSFER_CONFIRM,
    A_DIRECTION_TRANSFER_QUIT,
    A_UNDIRECTION_TRANSFER_UP,
    A_UNDIRECTION_TRANSFER_DOWN,
    A_UNDIRECTION_TRANSFER_CONFIRM,
    A_UNDIRECTION_TRANSFER_QUIT,
    A_EXPLORE_NEIGHBOR_CONFIRM,
    A_EXPLORE_NEIGHBOR_QUIT,
    A_EXPLORE_SUB_LINE_CONFIRM,
    A_EXPLORE_SUB_LINE_QUIT,
    A_RUN_MODE,
    A_RUN_BROWSER,
    A_DIRECTION_RUN_ENDPOINT,
    A_HELP_CONFIRM,
    A_HELP_QUIT,
    A_LIST_LINE_COMMAND,
    A_LIST_STATION_COMMAND,
    A_MODE_QUIT,
    A_STATIONS_QUIT,
    A_LINES_QUIT,
    A_DIRECTION_LINES_AUTO,
    A_UNDIRECTION_LINES_AUTO,
    A_SOURCE_STATIONS_AUTO,
    A_SOURCE_LINES_AUTO,
    A_DESTINATION_STATIONS_AUTO,
    A_DESTINATION_LINES_AUTO,
    A_DIRECTION_RUN_UP,
    A_DIRECTION_RUN_DOWN,
    A_UNDIRECTION_RUN_UP,
    A_UNDIRECTION_RUN_DOWN,
    A_OPEN_HELP,
))


# ---------------------------------------------------------------------------
# List movement helpers
# ---------------------------------------------------------------------------


def _get_list_vm(context: NavigationContext) -> ListViewModel | None:
    vm = context.view_model
    if isinstance(vm, ListViewModel):
        return vm
    return None


def _list_view_items(vm: ListViewModel) -> tuple[str, ...]:
    return tuple(item for item in vm.display if item)


def _to_str_id(val):
    if isinstance(val, str):
        return val
    if hasattr(val, "__iter__") and not isinstance(val, str):
        return str(list(val))
    return str(val)


# ---------------------------------------------------------------------------
# List movement actions
# ---------------------------------------------------------------------------


def _move_up(snapshot, context: NavigationContext) -> ActionResult:
    vm = _get_list_vm(context)
    if vm is None:
        return ActionResult.rejected()
    if vm.move_up():
        return ActionResult.accepted_with()
    return ActionResult.rejected()


def _move_down(snapshot, context: NavigationContext) -> ActionResult:
    vm = _get_list_vm(context)
    if vm is None:
        return ActionResult.rejected()
    if vm.move_down():
        return ActionResult.accepted_with()
    return ActionResult.rejected()


def _move_home(snapshot, context: NavigationContext) -> ActionResult:
    vm = _get_list_vm(context)
    if vm is None:
        return ActionResult.rejected()
    vm.move_home()
    return ActionResult.accepted_with()


def _move_end(snapshot, context: NavigationContext) -> ActionResult:
    vm = _get_list_vm(context)
    if vm is None:
        return ActionResult.rejected()
    vm.move_end()
    return ActionResult.accepted_with()


def _build_open_help():
    def open_help(snapshot, context: NavigationContext) -> ActionResult:
        context.return_state = snapshot.state
        return ActionResult.accepted_with()
    return open_help


def build_base_actions() -> dict[ActionId, callable]:
    actions: dict[ActionId, callable] = {}
    actions[A_LIST_MOVE_UP] = _move_up
    actions[A_LIST_MOVE_DOWN] = _move_down
    actions[A_LIST_MOVE_HOME] = _move_home
    actions[A_LIST_MOVE_END] = _move_end
    actions[A_OPEN_HELP] = _build_open_help()
    return actions


# ---------------------------------------------------------------------------
# Guard registry
# ---------------------------------------------------------------------------


def build_guard_registry(direction_nav=None, undirection_nav=None) -> dict[GuardId, callable]:
    guards: dict[GuardId, callable] = {}

    def _can_move_up(snapshot):
        return snapshot.option_count > 0 and snapshot.current_index > 0

    def _can_move_down(snapshot):
        return snapshot.option_count > 0 and snapshot.current_index < (snapshot.option_count - 1)

    guards[G_CAN_MOVE_UP] = _can_move_up
    guards[G_CAN_MOVE_DOWN] = _can_move_down

    def _is_direction(snapshot):
        vm = snapshot.selected_id
        return vm == "direction"

    def _is_undirection(snapshot):
        return snapshot.selected_id == "undirection"

    def _is_plan(snapshot):
        return snapshot.selected_id == "plan"

    guards[G_IS_DIRECTION_SELECTED] = _is_direction
    guards[G_IS_UNDIRECTION_SELECTED] = _is_undirection
    guards[G_IS_PLAN_SELECTED] = _is_plan

    def _has_one_option(snapshot):
        return snapshot.option_count == 1

    guards[G_HAS_ONE_OPTION] = _has_one_option

    def _has_line(snapshot):
        return snapshot.has_line

    def _has_station(snapshot):
        return snapshot.has_station

    def _has_source(snapshot):
        return snapshot.has_source

    def _has_dest(snapshot):
        return snapshot.has_destination

    def _has_no_line(snapshot):
        return not snapshot.has_line

    def _has_no_station(snapshot):
        return not snapshot.has_station

    guards[G_HAS_LINE] = _has_line
    guards[G_HAS_STATION] = _has_station
    guards[G_HAS_SOURCE] = _has_source
    guards[G_HAS_DEST] = _has_dest
    guards[G_HAS_NO_LINE] = _has_no_line
    guards[G_HAS_NO_STATION] = _has_no_station

    def _has_no_reverse(snapshot):
        return snapshot.neighbor_count == 0

    def _has_one_reverse(snapshot):
        return snapshot.neighbor_count == 1

    def _has_multi_reverse(snapshot):
        return snapshot.neighbor_count > 1

    def _has_no_forward(snapshot):
        return snapshot.transfer_count == 0

    def _has_forward(snapshot):
        return snapshot.transfer_count > 0

    guards[G_HAS_NO_REVERSE] = _has_no_reverse
    guards[G_HAS_ONE_REVERSE] = _has_one_reverse
    guards[G_HAS_MULTI_REVERSE] = _has_multi_reverse
    guards[G_HAS_NO_FORWARD] = _has_no_forward
    guards[G_HAS_FORWARD] = _has_forward

    def _has_transfer(snapshot):
        return snapshot.transfer_count > 0

    def _has_no_transfer(snapshot):
        return snapshot.transfer_count == 0

    guards[G_HAS_TRANSFER] = _has_transfer
    guards[G_HAS_NO_TRANSFER] = _has_no_transfer

    def _run_active(snapshot):
        return snapshot.run_active

    guards[G_RUN_ACTIVE] = _run_active

    def _return_is_direction_run(snapshot):
        return snapshot.return_state == NavigationStateId.DIRECTION_RUN

    def _return_is_plan_run(snapshot):
        return snapshot.return_state == NavigationStateId.PLAN_RUN

    def _return_is_undirection_run(snapshot):
        return snapshot.return_state == NavigationStateId.UNDIRECTION_RUN

    def _return_is_stations(snapshot):
        return snapshot.return_state == NavigationStateId.STATIONS

    def _return_is_lines(snapshot):
        return snapshot.return_state == NavigationStateId.LINES

    def _return_is_direction_stations(snapshot):
        return snapshot.return_state == NavigationStateId.DIRECTION_STATIONS

    def _return_is_direction_lines(snapshot):
        return snapshot.return_state == NavigationStateId.DIRECTION_LINES

    def _return_is_undirection_stations(snapshot):
        return snapshot.return_state == NavigationStateId.UNDIRECTION_STATIONS

    def _return_is_undirection_lines(snapshot):
        return snapshot.return_state == NavigationStateId.UNDIRECTION_LINES

    def _return_is_source_stations(snapshot):
        return snapshot.return_state == NavigationStateId.SOURCE_STATIONS

    def _return_is_source_lines(snapshot):
        return snapshot.return_state == NavigationStateId.SOURCE_LINES

    def _return_is_destination_stations(snapshot):
        return snapshot.return_state == NavigationStateId.DESTINATION_STATIONS

    def _return_is_destination_lines(snapshot):
        return snapshot.return_state == NavigationStateId.DESTINATION_LINES

    guards[G_RETURN_IS_DIRECTION_RUN] = _return_is_direction_run
    guards[G_RETURN_IS_PLAN_RUN] = _return_is_plan_run
    guards[G_RETURN_IS_UNDIRECTION_RUN] = _return_is_undirection_run
    guards[G_RETURN_IS_STATIONS] = _return_is_stations
    guards[G_RETURN_IS_LINES] = _return_is_lines
    guards[G_RETURN_IS_DIRECTION_STATIONS] = _return_is_direction_stations
    guards[G_RETURN_IS_DIRECTION_LINES] = _return_is_direction_lines
    guards[G_RETURN_IS_UNDIRECTION_STATIONS] = _return_is_undirection_stations
    guards[G_RETURN_IS_UNDIRECTION_LINES] = _return_is_undirection_lines
    guards[G_RETURN_IS_SOURCE_STATIONS] = _return_is_source_stations
    guards[G_RETURN_IS_SOURCE_LINES] = _return_is_source_lines
    guards[G_RETURN_IS_DESTINATION_STATIONS] = _return_is_destination_stations
    guards[G_RETURN_IS_DESTINATION_LINES] = _return_is_destination_lines

    def _has_previous(snapshot):
        return snapshot.neighbor_count > 0

    def _has_no_previous(snapshot):
        return snapshot.neighbor_count == 0

    def _has_next(snapshot):
        return snapshot.transfer_count > 0

    def _has_no_next(snapshot):
        return snapshot.transfer_count == 0

    guards[G_HAS_PREVIOUS] = _has_previous
    guards[G_HAS_NO_PREVIOUS] = _has_no_previous
    guards[G_HAS_NEXT] = _has_next
    guards[G_HAS_NO_NEXT] = _has_no_next

    def _help_selected_mode(snapshot):
        return snapshot.selected_id == "m"

    def _help_selected_browser(snapshot):
        return snapshot.selected_id == "v"

    def _help_selected_station(snapshot):
        return snapshot.selected_id == "s"

    def _help_selected_line(snapshot):
        return snapshot.selected_id == "l"

    def _help_selected_endpoint(snapshot):
        return snapshot.selected_id == "e"

    guards[G_HELP_SELECTED_MODE] = _help_selected_mode
    guards[G_HELP_SELECTED_BROWSER] = _help_selected_browser
    guards[G_HELP_SELECTED_STATION] = _help_selected_station
    guards[G_HELP_SELECTED_LINE] = _help_selected_line
    guards[G_HELP_SELECTED_ENDPOINT] = _help_selected_endpoint
    for (return_state, selected_id), guard_id in HELP_CONFIRM_GUARDS.items():
        guards[guard_id] = lambda snapshot, rs=return_state, sid=selected_id: (
            snapshot.return_state == rs and snapshot.selected_id == sid
        )

    def _und_left_has_next(snapshot):
        return snapshot.neighbor_count > 0

    def _und_left_no_next_extra(snapshot):
        return snapshot.neighbor_count == 0 and snapshot.transfer_count > 0

    def _und_right_has_next(snapshot):
        return snapshot.neighbor_count > 0

    def _und_right_no_next_extra(snapshot):
        return snapshot.neighbor_count == 0 and snapshot.transfer_count > 0

    guards[G_UNDIRECTION_LEFT_HAS_NEXT] = _und_left_has_next
    guards[G_UNDIRECTION_LEFT_NO_NEXT_EXTRA] = _und_left_no_next_extra
    guards[G_UNDIRECTION_RIGHT_HAS_NEXT] = _und_right_has_next
    guards[G_UNDIRECTION_RIGHT_NO_NEXT_EXTRA] = _und_right_no_next_extra

    def _has_sub_line_transfer(snapshot):
        return snapshot.sub_line_count > 0

    def _has_no_sub_line_transfer(snapshot):
        return snapshot.sub_line_count == 0

    guards[G_HAS_SUB_LINE_TRANSFER] = _has_sub_line_transfer
    guards[G_HAS_NO_SUB_LINE_TRANSFER] = _has_no_sub_line_transfer

    return guards


# ---------------------------------------------------------------------------
# Entry effects
# ---------------------------------------------------------------------------


def _build_run_view(direction_nav) -> RunViewModel:
    return RunViewModel(
        current_data=direction_nav.current_display,
        transfer_data=tuple(direction_nav.transfer_display),
        hint="請使用左右鍵在車站間移動",
    )


def _build_plan_run_view(direction_nav) -> RunViewModel:
    return RunViewModel(
        current_data=direction_nav.current_display,
        transfer_data=(),
        hint="路線規劃模式：請使用左右鍵在車站間移動",
    )


def _build_undirection_run_view(undirection_nav) -> RunViewModel:
    return RunViewModel(
        current_data=undirection_nav.current_display,
        transfer_data=tuple(undirection_nav.transfer_display),
        hint="請使用左右鍵在車站間移動",
    )


def build_entry_effects(
    direction_nav=None, undirection_nav=None
) -> dict[NavigationStateId, callable]:
    entry: dict[NavigationStateId, callable] = {}

    def mode_entry(snapshot, context):
        context.view_model = ListViewModel.build(
            data=[
                {"id": "direction", "label": "方向探索"},
                {"id": "undirection", "label": "線性探索"},
                {"id": "plan", "label": "路線規劃"},
            ],
            hint="請使用上下鍵選擇導航模式",
        )
        return PresentationEffects(open_messages=("功能選單開啟",))

    entry[NavigationStateId.MODE] = mode_entry

    if direction_nav is not None:
        def stations_entry(snapshot, context):
            context.view_model = ListViewModel.build(
                data=direction_nav.stations_display,
                hint="切換至車站列表，請使用上下鍵選擇瀏覽車站所在的路線",
            )
            return PresentationEffects()

        entry[NavigationStateId.STATIONS] = stations_entry

        def lines_entry(snapshot, context):
            context.view_model = ListViewModel.build(
                data=direction_nav.lines_display,
                hint="切換至路線列表，請使用上下鍵選擇瀏覽路線包含的車站",
            )
            return PresentationEffects()

        entry[NavigationStateId.LINES] = lines_entry

        def direction_stations_entry(snapshot, context):
            context.view_model = ListViewModel.build(
                data=direction_nav.stations_display,
                hint="切換至車站列表，請使用上下鍵選擇起點車站",
            )
            return PresentationEffects()

        entry[NavigationStateId.DIRECTION_STATIONS] = direction_stations_entry

        def direction_lines_entry(snapshot, context):
            context.view_model = ListViewModel.build(
                data=direction_nav.lines_display,
                hint="切換至路線列表，請使用上下鍵選擇路線",
            )
            return PresentationEffects()

        entry[NavigationStateId.DIRECTION_LINES] = direction_lines_entry

        def direction_end_point_entry(snapshot, context):
            context.view_model = ListViewModel.build(
                data=direction_nav.end_points,
                hint="請用上下鍵瀏覽並選擇終點方向",
            )
            return PresentationEffects()

        entry[NavigationStateId.DIRECTION_END_POINT] = direction_end_point_entry

        def direction_run_entry(snapshot, context):
            context.view_model = _build_run_view(direction_nav)
            return PresentationEffects()

        entry[NavigationStateId.DIRECTION_RUN] = direction_run_entry

        def plan_run_entry(snapshot, context):
            context.view_model = _build_plan_run_view(direction_nav)
            return PresentationEffects()

        entry[NavigationStateId.PLAN_RUN] = plan_run_entry

        def direction_transfer_entry(snapshot, context):
            context.view_model = ListViewModel.build(
                data=direction_nav.transfer_display,
                hint="",
            )
            return PresentationEffects(
                open_messages=("轉乘選單開啟",),
            )

        entry[NavigationStateId.DIRECTION_TRANSFER] = direction_transfer_entry

        def explore_neighbor_entry(snapshot, context):
            context.view_model = ListViewModel.build(
                data=direction_nav.reverse_display,
                hint="請使用上下鍵選擇探索的下一站",
            )
            return PresentationEffects(open_messages=("探索選單開啟",))

        entry[NavigationStateId.EXPLORE_NEIGHBOR] = explore_neighbor_entry

        def source_stations_entry(snapshot, context):
            context.view_model = ListViewModel.build(
                data=direction_nav.stations_display,
                hint="切換至車站列表，請使用上下鍵選擇起點車站",
            )
            return PresentationEffects()

        entry[NavigationStateId.SOURCE_STATIONS] = source_stations_entry

        def source_lines_entry(snapshot, context):
            context.view_model = ListViewModel.build(
                data=direction_nav.lines_display,
                hint="切換至路線列表，請使用上下鍵選擇路線",
            )
            return PresentationEffects()

        entry[NavigationStateId.SOURCE_LINES] = source_lines_entry

        def destination_stations_entry(snapshot, context):
            context.view_model = ListViewModel.build(
                data=direction_nav.stations_display,
                hint="切換至車站列表，請使用上下鍵選擇目的車站",
            )
            return PresentationEffects()

        entry[NavigationStateId.DESTINATION_STATIONS] = destination_stations_entry

        def destination_lines_entry(snapshot, context):
            context.view_model = ListViewModel.build(
                data=direction_nav.lines_display,
                hint="切換至路線列表，請使用上下鍵選擇路線",
            )
            return PresentationEffects()

        entry[NavigationStateId.DESTINATION_LINES] = destination_lines_entry

    if undirection_nav is not None:
        def undirection_run_entry(snapshot, context):
            context.view_model = _build_undirection_run_view(undirection_nav)
            return PresentationEffects()

        entry[NavigationStateId.UNDIRECTION_RUN] = undirection_run_entry

        def undirection_transfer_entry(snapshot, context):
            context.view_model = ListViewModel.build(
                data=undirection_nav.transfer_display,
                hint="",
            )
            return PresentationEffects(open_messages=("轉乘選單開啟",))

        entry[NavigationStateId.UNDIRECTION_TRANSFER] = undirection_transfer_entry

        def explore_sub_line_entry(snapshot, context):
            context.view_model = ListViewModel.build(
                data=undirection_nav.transfer_display,
                hint="請使用上下鍵選擇路線",
            )
            return PresentationEffects(open_messages=("路線選單開啟",))

        entry[NavigationStateId.EXPLORE_SUB_LINE] = explore_sub_line_entry

        def undirection_stations_entry(snapshot, context):
            context.view_model = ListViewModel.build(
                data=undirection_nav.stations_display,
                hint="切換至車站列表，請使用上下鍵選擇起點車站",
            )
            return PresentationEffects()

        entry[NavigationStateId.UNDIRECTION_STATIONS] = undirection_stations_entry

        def undirection_lines_entry(snapshot, context):
            context.view_model = ListViewModel.build(
                data=undirection_nav.lines_display,
                hint="切換至路線列表，請使用上下鍵選擇路線",
            )
            return PresentationEffects()

        entry[NavigationStateId.UNDIRECTION_LINES] = undirection_lines_entry

        def undirection_sub_lines_entry(snapshot, context):
            context.view_model = ListViewModel.build(
                data=undirection_nav.sub_lines_display,
                hint="切換至子路線列表，請使用上下鍵選擇子路線",
            )
            return PresentationEffects()

        entry[NavigationStateId.UNDIRECTION_SUB_LINES] = undirection_sub_lines_entry

    def help_entry(snapshot, context):
        help_items = []
        rs = context.return_state
        if rs is not None:
            if rs == NavigationStateId.STATIONS:
                help_items = [{"key": "l", "doc": "切換至路線列表"}]
            elif rs == NavigationStateId.LINES:
                help_items = [{"key": "s", "doc": "切換至車站列表"}]
            elif rs == NavigationStateId.DIRECTION_STATIONS:
                help_items = [{"key": "l", "doc": "切換至路線列表"}]
            elif rs == NavigationStateId.DIRECTION_LINES:
                help_items = [{"key": "s", "doc": "切換至車站列表"}]
            elif rs == NavigationStateId.UNDIRECTION_STATIONS:
                help_items = [{"key": "l", "doc": "切換至路線列表"}]
            elif rs == NavigationStateId.UNDIRECTION_LINES:
                help_items = [{"key": "s", "doc": "切換至車站列表"}]
            elif rs == NavigationStateId.SOURCE_STATIONS:
                help_items = [{"key": "l", "doc": "切換至路線列表"}]
            elif rs == NavigationStateId.SOURCE_LINES:
                help_items = [{"key": "s", "doc": "切換至車站列表"}]
            elif rs == NavigationStateId.DESTINATION_STATIONS:
                help_items = [{"key": "l", "doc": "切換至路線列表"}]
            elif rs == NavigationStateId.DESTINATION_LINES:
                help_items = [{"key": "s", "doc": "切換至車站列表"}]
            elif rs in (
                NavigationStateId.DIRECTION_RUN,
                NavigationStateId.UNDIRECTION_RUN,
                NavigationStateId.PLAN_RUN,
            ):
                help_items = [
                    {"key": "m", "doc": "重新選擇導航模式"},
                    {"key": "v", "doc": "瀏覽車站與路線列表"},
                ]
            elif rs == NavigationStateId.DIRECTION_END_POINT:
                help_items = []

        context.view_model = ListViewModel.build(
            data=[
                {"id": item["key"], "label": item["doc"],
                 "description": f'按鍵{item["key"]}'}
                for item in help_items
            ],
            hint="請使用上下鍵瀏覽說明選單",
        )
        return PresentationEffects(open_messages=("說明選單開啟",))

    entry[NavigationStateId.HELP] = help_entry

    return entry


# ---------------------------------------------------------------------------
# Exit effects
# ---------------------------------------------------------------------------


def build_exit_effects(
    direction_nav=None, undirection_nav=None
) -> dict[NavigationStateId, callable]:
    exit_map: dict[NavigationStateId, callable] = {}

    def direction_transfer_exit(snapshot, context):
        return PresentationEffects(close_messages=("轉乘選單關閉",))

    exit_map[NavigationStateId.DIRECTION_TRANSFER] = direction_transfer_exit

    def undirection_transfer_exit(snapshot, context):
        return PresentationEffects(close_messages=("轉乘選單關閉",))

    exit_map[NavigationStateId.UNDIRECTION_TRANSFER] = undirection_transfer_exit

    def explore_neighbor_exit(snapshot, context):
        return PresentationEffects(close_messages=("探索選單關閉",))

    exit_map[NavigationStateId.EXPLORE_NEIGHBOR] = explore_neighbor_exit

    def explore_sub_line_exit(snapshot, context):
        return PresentationEffects(close_messages=("路線選單關閉",))

    exit_map[NavigationStateId.EXPLORE_SUB_LINE] = explore_sub_line_exit

    def help_exit(snapshot, context):
        return PresentationEffects(close_messages=("說明選單關閉",))

    exit_map[NavigationStateId.HELP] = help_exit

    return exit_map


# ---------------------------------------------------------------------------
# Snapshot factory builder
# ---------------------------------------------------------------------------


def build_snapshot_factory(direction_nav, undirection_nav):
    class _Factory:
        direction = direction_nav
        undirection = undirection_nav

        @staticmethod
        def create(context: NavigationContext) -> "NavigationSnapshot":
            from apps.access8graph.navigation.snapshot import NavigationSnapshot

            vm = context.view_model
            selected_id = getattr(vm, "selected_id", None)
            current_index = getattr(vm, "current_index", 0)
            option_count = getattr(vm, "option_count", 0)

            st = context.current_state

            has_line = False
            has_station = False
            has_source = False
            has_dest = False
            neighbor_count = 0
            transfer_count = 0
            sub_line_count = 0
            run_active = False

            dnav = _Factory.direction
            unav = _Factory.undirection

            if dnav is not None:
                if st in {
                    NavigationStateId.DIRECTION_STATIONS,
                    NavigationStateId.DIRECTION_LINES,
                    NavigationStateId.DIRECTION_END_POINT,
                    NavigationStateId.DIRECTION_RUN,
                    NavigationStateId.DIRECTION_TRANSFER,
                    NavigationStateId.EXPLORE_NEIGHBOR,
                    NavigationStateId.SOURCE_STATIONS,
                    NavigationStateId.SOURCE_LINES,
                    NavigationStateId.DESTINATION_STATIONS,
                    NavigationStateId.DESTINATION_LINES,
                    NavigationStateId.PLAN_RUN,
                    NavigationStateId.STATIONS,
                    NavigationStateId.LINES,
                }:
                    has_line = bool(dnav.line)
                    has_station = bool(dnav.station)
                    has_source = bool(dnav.source)
                    has_dest = bool(dnav.destination)
                    run_active = dnav.run

                    if st == NavigationStateId.DIRECTION_RUN:
                        neighbor_count = len(dnav.reverse)
                        transfer_count = len(dnav.forward)

                if st == NavigationStateId.PLAN_RUN:
                    has_source = bool(dnav.source)
                    has_dest = bool(dnav.destination)
                    neighbor_count = 1 if getattr(dnav, "previous", None) else 0
                    transfer_count = 1 if getattr(dnav, "next", None) else 0

            if unav is not None:
                if st in {
                    NavigationStateId.UNDIRECTION_STATIONS,
                    NavigationStateId.UNDIRECTION_LINES,
                    NavigationStateId.UNDIRECTION_SUB_LINES,
                    NavigationStateId.UNDIRECTION_RUN,
                    NavigationStateId.UNDIRECTION_TRANSFER,
                    NavigationStateId.EXPLORE_SUB_LINE,
                }:
                    has_line = bool(unav.line)
                    has_station = bool(unav.station)
                    has_source = False
                    has_dest = False

                    if st == NavigationStateId.UNDIRECTION_RUN:
                        neighbor_count = 1 if unav.previous else 0
                        transfer_count = 1 if unav.next else 0
                        sub_line_count = len(getattr(unav, "transfer_same_sub_line", []))

            return NavigationSnapshot(
                state=context.current_state,
                return_state=context.return_state,
                selected_id=selected_id,
                current_index=current_index,
                option_count=option_count,
                selected_mode=context.selected_mode,
                has_line=has_line,
                has_station=has_station,
                has_source=has_source,
                has_destination=has_dest,
                neighbor_count=neighbor_count,
                transfer_count=transfer_count,
                sub_line_count=sub_line_count,
                run_active=run_active,
            )

    return _Factory
