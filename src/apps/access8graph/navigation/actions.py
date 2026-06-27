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
    def selected_id(self) -> str | None:
        if 0 <= self.current_index < len(self.items):
            item = self.items[self.current_index]
            raw = item.get("id")
            if raw is None:
                return None
            return str(raw)
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
    def selected_id(self) -> str | None:
        raw = self.current_data.get("id")
        if raw is None:
            return None
        return str(raw)

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

G_HAS_PREVIOUS = GuardId("has_previous")
G_HAS_NO_PREVIOUS = GuardId("has_no_previous")
G_HAS_NEXT = GuardId("has_next")
G_HAS_NO_NEXT = GuardId("has_no_next")

G_HELP_SELECTED_MODE = GuardId("help_selected_mode")
G_HELP_SELECTED_BROWSER = GuardId("help_selected_browser")
G_HELP_SELECTED_STATION = GuardId("help_selected_station")
G_HELP_SELECTED_LINE = GuardId("help_selected_line")
G_HELP_SELECTED_ENDPOINT = GuardId("help_selected_endpoint")

G_UNDIRECTION_LEFT_HAS_NEXT = GuardId("undirection_left_has_next")
G_UNDIRECTION_LEFT_NO_NEXT_EXTRA = GuardId("undirection_left_no_next_extra")

G_UNDIRECTION_RIGHT_HAS_NEXT = GuardId("undirection_right_has_next")
G_UNDIRECTION_RIGHT_NO_NEXT_EXTRA = GuardId("undirection_right_no_next_extra")

G_HAS_SUB_LINE_TRANSFER = GuardId("has_sub_line_transfer")
G_HAS_NO_SUB_LINE_TRANSFER = GuardId("has_no_sub_line_transfer")


# ---------------------------------------------------------------------------
# List movement actions
# ---------------------------------------------------------------------------


def _get_list_vm(context: NavigationContext) -> ListViewModel | None:
    vm = context.view_model
    if isinstance(vm, ListViewModel):
        return vm
    return None


def _list_view_items(vm: ListViewModel) -> tuple[str, ...]:
    return tuple(item for item in vm.display if item)


def _move_up(snapshot, context: NavigationContext) -> ActionResult:
    vm = _get_list_vm(context)
    if vm is None:
        return ActionResult.rejected()
    if vm.move_up():
        return ActionResult.accepted_with(
            PresentationEffects(view_items=_list_view_items(vm))
        )
    return ActionResult.rejected()


def _move_down(snapshot, context: NavigationContext) -> ActionResult:
    vm = _get_list_vm(context)
    if vm is None:
        return ActionResult.rejected()
    if vm.move_down():
        return ActionResult.accepted_with(
            PresentationEffects(view_items=_list_view_items(vm))
        )
    return ActionResult.rejected()


def _move_home(snapshot, context: NavigationContext) -> ActionResult:
    vm = _get_list_vm(context)
    if vm is None:
        return ActionResult.rejected()
    vm.move_home()
    return ActionResult.accepted_with(
        PresentationEffects(view_items=_list_view_items(vm))
    )


def _move_end(snapshot, context: NavigationContext) -> ActionResult:
    vm = _get_list_vm(context)
    if vm is None:
        return ActionResult.rejected()
    vm.move_end()
    return ActionResult.accepted_with(
        PresentationEffects(view_items=_list_view_items(vm))
    )


# ---------------------------------------------------------------------------
# Mode selection actions (capture navigator via closure)
# ---------------------------------------------------------------------------


def _build_mode_select_actions(direction_nav, undirection_nav):
    def select_direction(snapshot, context: NavigationContext) -> ActionResult:
        context.return_state = NavigationStateId.DIRECTION_RUN
        direction_nav.line = None
        direction_nav.station = None
        context.selected_mode = "direction"
        return ActionResult.accepted_with()

    def select_undirected(snapshot, context: NavigationContext) -> ActionResult:
        undirection_nav.line = None
        undirection_nav.station = None
        context.selected_mode = "undirection"
        return ActionResult.accepted_with()

    def select_plan(snapshot, context: NavigationContext) -> ActionResult:
        context.return_state = NavigationStateId.PLAN_RUN
        direction_nav.line = None
        direction_nav.station = None
        context.selected_mode = "plan"
        return ActionResult.accepted_with()

    return select_direction, select_undirected, select_plan


# ---------------------------------------------------------------------------
# Stations/Lines confirm (browser states)
# ---------------------------------------------------------------------------


def _build_stations_lines_confirm(direction_nav):
    def stations_confirm(snapshot, context: NavigationContext) -> ActionResult:
        if snapshot.selected_id is not None:
            direction_nav.station = snapshot.selected_id
        return ActionResult.accepted_with()

    def lines_confirm(snapshot, context: NavigationContext) -> ActionResult:
        if snapshot.selected_id is not None:
            direction_nav.line = snapshot.selected_id
        return ActionResult.accepted_with()

    return stations_confirm, lines_confirm


# ---------------------------------------------------------------------------
# Cross-navigation list commands (l/s from stations/lines)
# ---------------------------------------------------------------------------


def _build_list_cross_commands(direction_nav):
    def list_line_command(snapshot, context: NavigationContext) -> ActionResult:
        direction_nav.line = None
        return ActionResult.accepted_with()

    def list_station_command(snapshot, context: NavigationContext) -> ActionResult:
        direction_nav.station = None
        return ActionResult.accepted_with()

    return list_line_command, list_station_command


# ---------------------------------------------------------------------------
# Direction stations/lines confirm
# ---------------------------------------------------------------------------


def _build_direction_stations_lines_confirm(direction_nav):
    def direction_stations_confirm(snapshot, context: NavigationContext) -> ActionResult:
        if snapshot.selected_id is not None:
            direction_nav.station = snapshot.selected_id
        if snapshot.has_line and direction_nav.station:
            result = list(
                direction_nav.model.get_node_from_station_id_line_id(
                    direction_nav.station, direction_nav.line
                )
            )[0]
            direction_nav.current = direction_nav.source = result
            direction_nav.line = None
            direction_nav.station = None
        return ActionResult.accepted_with()

    def direction_lines_confirm(snapshot, context: NavigationContext) -> ActionResult:
        if snapshot.selected_id is not None:
            direction_nav.line = snapshot.selected_id
        if snapshot.has_station and direction_nav.line:
            result = list(
                direction_nav.model.get_node_from_station_id_line_id(
                    direction_nav.station, direction_nav.line
                )
            )[0]
            direction_nav.current = direction_nav.source = result
            direction_nav.line = None
            direction_nav.station = None
        return ActionResult.accepted_with()

    return direction_stations_confirm, direction_lines_confirm


# ---------------------------------------------------------------------------
# Direction end point confirm
# ---------------------------------------------------------------------------


def _build_direction_end_point_confirm(direction_nav):
    def direction_end_point_confirm(
        snapshot, context: NavigationContext
    ) -> ActionResult:
        if snapshot.selected_id is not None:
            direction_nav.destination = snapshot.selected_id
        return ActionResult.accepted_with()

    return direction_end_point_confirm


# ---------------------------------------------------------------------------
# Direction run movement actions
# ---------------------------------------------------------------------------


def _build_direction_run_actions(direction_nav):
    def direction_left(snapshot, context: NavigationContext) -> ActionResult:
        pointer = direction_nav.reverse
        if len(pointer) == 1:
            direction_nav.source = direction_nav.current = pointer[0]
            return ActionResult.accepted_with()
        if len(pointer) > 1:
            return ActionResult.accepted_with()
        return ActionResult.rejected()

    def direction_right(snapshot, context: NavigationContext) -> ActionResult:
        pointer = direction_nav.forward
        if len(pointer) == 1:
            direction_nav.current = pointer[0]
            return ActionResult.accepted_with()
        if len(pointer) > 1:
            direction_nav.current = pointer[0]
            return ActionResult.accepted_with()
        return ActionResult.rejected()

    def direction_run_endpoint(snapshot, context: NavigationContext) -> ActionResult:
        direction_nav.source = direction_nav.current
        direction_nav.destination = None
        return ActionResult.accepted_with()

    return direction_left, direction_right, direction_run_endpoint


# ---------------------------------------------------------------------------
# Direction run transfer actions (check transfer_display)
# ---------------------------------------------------------------------------


def _build_direction_run_transfer_actions(direction_nav):
    def direction_run_up(snapshot, context: NavigationContext) -> ActionResult:
        if len(direction_nav.transfer_display) == 0:
            return ActionResult.rejected()
        return ActionResult.accepted_with()

    def direction_run_down(snapshot, context: NavigationContext) -> ActionResult:
        if len(direction_nav.transfer_display) == 0:
            return ActionResult.rejected()
        return ActionResult.accepted_with()

    return direction_run_up, direction_run_down


# ---------------------------------------------------------------------------
# Undirection run transfer actions (check transfer_display)
# ---------------------------------------------------------------------------


def _build_undirection_run_transfer_actions(undirection_nav):
    def undirection_run_up(snapshot, context: NavigationContext) -> ActionResult:
        if len(undirection_nav.transfer_display) == 0:
            return ActionResult.rejected()
        return ActionResult.accepted_with()

    def undirection_run_down(snapshot, context: NavigationContext) -> ActionResult:
        if len(undirection_nav.transfer_display) == 0:
            return ActionResult.rejected()
        return ActionResult.accepted_with()

    return undirection_run_up, undirection_run_down


# ---------------------------------------------------------------------------
# Undirection run movement actions
# ---------------------------------------------------------------------------


def _build_undirection_run_actions(undirection_nav):
    def undirection_left(snapshot, context: NavigationContext) -> ActionResult:
        pointer = undirection_nav.previous
        if pointer:
            undirection_nav.current = pointer
            return ActionResult.accepted_with()
        return ActionResult.rejected()

    def undirection_right(snapshot, context: NavigationContext) -> ActionResult:
        pointer = undirection_nav.next
        if pointer:
            undirection_nav.current = pointer
            return ActionResult.accepted_with()
        return ActionResult.rejected()

    return undirection_left, undirection_right


# ---------------------------------------------------------------------------
# Plan run movement actions
# ---------------------------------------------------------------------------


def _build_plan_run_actions(direction_nav):
    def plan_left(snapshot, context: NavigationContext) -> ActionResult:
        pointer = getattr(direction_nav, "previous", None)
        if pointer:
            direction_nav.current = pointer
            return ActionResult.accepted_with()
        return ActionResult.rejected()

    def plan_right(snapshot, context: NavigationContext) -> ActionResult:
        pointer = getattr(direction_nav, "next", None)
        if pointer:
            direction_nav.current = pointer
            return ActionResult.accepted_with()
        return ActionResult.rejected()

    return plan_left, plan_right


# ---------------------------------------------------------------------------
# Direction transfer actions
# ---------------------------------------------------------------------------


def _build_direction_transfer_actions(direction_nav):
    def direction_transfer_up(snapshot, context: NavigationContext) -> ActionResult:
        return _move_up(snapshot, context)

    def direction_transfer_down(snapshot, context: NavigationContext) -> ActionResult:
        return _move_down(snapshot, context)

    def direction_transfer_confirm(
        snapshot, context: NavigationContext
    ) -> ActionResult:
        transfer_id = snapshot.selected_id
        if transfer_id is not None and isinstance(transfer_id, (list, tuple)):
            direction_nav.source = direction_nav.current = transfer_id[0]
            direction_nav.destination = transfer_id[1]
        elif transfer_id is not None:
            vm = _get_list_vm(context)
            if vm is not None and 0 <= vm.current_index < len(vm.items):
                raw_id = vm.items[vm.current_index].get("id")
                if isinstance(raw_id, (list, tuple)) and len(raw_id) >= 2:
                    direction_nav.source = direction_nav.current = raw_id[0]
                    direction_nav.destination = raw_id[1]
        dd = direction_nav.destination_display
        line = dd.get("label", {}).get("line", "")
        name = dd.get("label", {}).get("name", "")
        msg = f"轉乘{line}往{name}"
        return ActionResult.accepted_with(
            PresentationEffects(open_messages=(msg,))
        )

    def direction_transfer_quit(snapshot, context: NavigationContext) -> ActionResult:
        return ActionResult.accepted_with()

    return (
        direction_transfer_up,
        direction_transfer_down,
        direction_transfer_confirm,
        direction_transfer_quit,
    )


# ---------------------------------------------------------------------------
# Undirection transfer actions
# ---------------------------------------------------------------------------


def _build_undirection_transfer_actions(undirection_nav):
    def undirection_transfer_up(snapshot, context: NavigationContext) -> ActionResult:
        return _move_up(snapshot, context)

    def undirection_transfer_down(snapshot, context: NavigationContext) -> ActionResult:
        return _move_down(snapshot, context)

    def undirection_transfer_confirm(
        snapshot, context: NavigationContext
    ) -> ActionResult:
        vm = _get_list_vm(context)
        if vm is not None and 0 <= vm.current_index < len(vm.items):
            raw_id = vm.items[vm.current_index].get("id")
            if isinstance(raw_id, dict):
                undirection_nav.current = raw_id.get("current")
                undirection_nav.sub_line = raw_id.get("sub_line")
        line = undirection_nav.line_name_display.get("label", "")
        left = undirection_nav.left_point_name_display.get("label", "")
        right = undirection_nav.right_point_name_display.get("label", "")
        msg = f"轉乘{line}，{left}往{right}"
        return ActionResult.accepted_with(
            PresentationEffects(open_messages=(msg,))
        )

    def undirection_transfer_quit(
        snapshot, context: NavigationContext
    ) -> ActionResult:
        return ActionResult.accepted_with()

    return (
        undirection_transfer_up,
        undirection_transfer_down,
        undirection_transfer_confirm,
        undirection_transfer_quit,
    )


# ---------------------------------------------------------------------------
# Explore neighbor actions
# ---------------------------------------------------------------------------


def _build_explore_neighbor_actions(direction_nav):
    def explore_neighbor_confirm(
        snapshot, context: NavigationContext
    ) -> ActionResult:
        if snapshot.selected_id is not None:
            direction_nav.source = direction_nav.current = snapshot.selected_id
        return ActionResult.accepted_with()

    def explore_neighbor_quit(snapshot, context: NavigationContext) -> ActionResult:
        return ActionResult.accepted_with()

    return explore_neighbor_confirm, explore_neighbor_quit


# ---------------------------------------------------------------------------
# Explore sub line actions
# ---------------------------------------------------------------------------


def _build_explore_sub_line_actions(undirection_nav):
    def explore_sub_line_confirm(
        snapshot, context: NavigationContext
    ) -> ActionResult:
        vm = _get_list_vm(context)
        if vm is not None and 0 <= vm.current_index < len(vm.items):
            raw_id = vm.items[vm.current_index].get("id")
            if undirection_nav.mode == "left" and isinstance(raw_id, (list, tuple)):
                undirection_nav.current = raw_id[-1]
            elif undirection_nav.mode == "right" and isinstance(raw_id, (list, tuple)):
                undirection_nav.current = raw_id[0]
            undirection_nav.sub_line = raw_id
        return ActionResult.accepted_with()

    def explore_sub_line_quit(snapshot, context: NavigationContext) -> ActionResult:
        return ActionResult.accepted_with()

    return explore_sub_line_confirm, explore_sub_line_quit


# ---------------------------------------------------------------------------
# Undirection stations/lines/sub_lines confirm
# ---------------------------------------------------------------------------


def _build_undirection_stations_lines_confirm(undirection_nav):
    def undirection_stations_confirm(
        snapshot, context: NavigationContext
    ) -> ActionResult:
        if snapshot.selected_id is not None:
            undirection_nav.station = snapshot.selected_id
        return ActionResult.accepted_with()

    def undirection_lines_confirm(
        snapshot, context: NavigationContext
    ) -> ActionResult:
        if snapshot.selected_id is not None:
            undirection_nav.line = snapshot.selected_id
        return ActionResult.accepted_with()

    def undirection_sub_lines_confirm(
        snapshot, context: NavigationContext
    ) -> ActionResult:
        if snapshot.selected_id is not None:
            undirection_nav.sub_line = snapshot.selected_id
        result = list(
            undirection_nav.model.get_node_from_station_id_line_id(
                undirection_nav.station, undirection_nav.line
            )
        )[0]
        undirection_nav.current = result
        return ActionResult.accepted_with()

    return (
        undirection_stations_confirm,
        undirection_lines_confirm,
        undirection_sub_lines_confirm,
    )


# ---------------------------------------------------------------------------
# Source stations/lines confirm
# ---------------------------------------------------------------------------


def _build_source_stations_lines_confirm(direction_nav):
    def source_stations_confirm(
        snapshot, context: NavigationContext
    ) -> ActionResult:
        if snapshot.selected_id is not None:
            direction_nav.station = snapshot.selected_id
        if snapshot.has_line and direction_nav.station:
            result = list(
                direction_nav.model.get_node_from_station_id_line_id(
                    direction_nav.station, direction_nav.line
                )
            )[0]
            direction_nav.current = direction_nav.source = result
            direction_nav.line = None
            direction_nav.station = None
        return ActionResult.accepted_with()

    def source_lines_confirm(
        snapshot, context: NavigationContext
    ) -> ActionResult:
        if snapshot.selected_id is not None:
            direction_nav.line = snapshot.selected_id
        if snapshot.has_station and direction_nav.line:
            result = list(
                direction_nav.model.get_node_from_station_id_line_id(
                    direction_nav.station, direction_nav.line
                )
            )[0]
            direction_nav.current = direction_nav.source = result
            direction_nav.line = None
            direction_nav.station = None
        return ActionResult.accepted_with()

    return source_stations_confirm, source_lines_confirm


# ---------------------------------------------------------------------------
# Destination stations/lines confirm
# ---------------------------------------------------------------------------


def _build_destination_stations_lines_confirm(direction_nav):
    def destination_stations_confirm(
        snapshot, context: NavigationContext
    ) -> ActionResult:
        if snapshot.selected_id is not None:
            direction_nav.station = snapshot.selected_id
        if snapshot.has_line and direction_nav.station:
            result = list(
                direction_nav.model.get_node_from_station_id_line_id(
                    direction_nav.station, direction_nav.line
                )
            )[0]
            direction_nav.destination = result
            direction_nav.line = None
            direction_nav.station = None
        return ActionResult.accepted_with()

    def destination_lines_confirm(
        snapshot, context: NavigationContext
    ) -> ActionResult:
        if snapshot.selected_id is not None:
            direction_nav.line = snapshot.selected_id
        if snapshot.has_station and direction_nav.line:
            result = list(
                direction_nav.model.get_node_from_station_id_line_id(
                    direction_nav.station, direction_nav.line
                )
            )[0]
            direction_nav.destination = result
            direction_nav.line = None
            direction_nav.station = None
        return ActionResult.accepted_with()

    return destination_stations_confirm, destination_lines_confirm


# ---------------------------------------------------------------------------
# Help actions
# ---------------------------------------------------------------------------


def _build_help_actions(direction_nav, undirection_nav):
    def help_confirm(snapshot, context: NavigationContext) -> ActionResult:
        selected = snapshot.selected_id
        if selected == "m":
            context.selected_mode = None
            return ActionResult.accepted_with()
        if selected == "v":
            return ActionResult.accepted_with()
        if selected == "s":
            direction_nav.station = None
            return ActionResult.accepted_with()
        if selected == "l":
            direction_nav.line = None
            return ActionResult.accepted_with()
        if selected == "e":
            direction_nav.source = direction_nav.current
            direction_nav.destination = None
            return ActionResult.accepted_with()
        return ActionResult.accepted_with()

    def help_quit(snapshot, context: NavigationContext) -> ActionResult:
        return ActionResult.accepted_with()

    return help_confirm, help_quit


# ---------------------------------------------------------------------------
# Run common actions (mode, browser)
# ---------------------------------------------------------------------------


def _build_run_common_actions(direction_nav, undirection_nav):
    def run_mode(snapshot, context: NavigationContext) -> ActionResult:
        return ActionResult.accepted_with()

    def run_browser(snapshot, context: NavigationContext) -> ActionResult:
        return ActionResult.accepted_with()

    return run_mode, run_browser


# ---------------------------------------------------------------------------
# Mode/Stations/Lines quit actions
# ---------------------------------------------------------------------------


def _build_quit_actions(direction_nav):
    def mode_quit(snapshot, context: NavigationContext) -> ActionResult:
        return ActionResult.accepted_with(
            PresentationEffects(
                close_messages=("功能選單關閉",),
            )
        )

    def stations_quit(snapshot, context: NavigationContext) -> ActionResult:
        direction_nav.line = None
        direction_nav.station = None
        return ActionResult.accepted_with(
            PresentationEffects(
                close_messages=("車站瀏覽選單關閉",),
            )
        )

    def lines_quit(snapshot, context: NavigationContext) -> ActionResult:
        direction_nav.line = None
        direction_nav.station = None
        return ActionResult.accepted_with(
            PresentationEffects(
                close_messages=("車站瀏覽選單關閉",),
            )
        )

    return mode_quit, stations_quit, lines_quit


# ---------------------------------------------------------------------------
# AUTO actions (for single-option auto-progression)
# ---------------------------------------------------------------------------


def _build_auto_actions(direction_nav):
    def direction_lines_auto(snapshot, context: NavigationContext) -> ActionResult:
        vm = _get_list_vm(context)
        if vm is not None and vm.option_count > 0:
            raw_id = vm.items[0].get("id")
            if raw_id is not None:
                direction_nav.line = raw_id
        return ActionResult.accepted_with()

    def undirection_lines_auto(snapshot, context: NavigationContext) -> ActionResult:
        vm = _get_list_vm(context)
        if vm is not None and vm.option_count > 0:
            raw_id = vm.items[0].get("id")
            if raw_id is not None:
                line_val = raw_id
        return ActionResult.accepted_with()

    def source_stations_auto(snapshot, context: NavigationContext) -> ActionResult:
        vm = _get_list_vm(context)
        if vm is not None and vm.option_count > 0:
            raw_id = vm.items[0].get("id")
            if raw_id is not None:
                direction_nav.station = raw_id
        return ActionResult.accepted_with()

    def source_lines_auto(snapshot, context: NavigationContext) -> ActionResult:
        vm = _get_list_vm(context)
        if vm is not None and vm.option_count > 0:
            raw_id = vm.items[0].get("id")
            if raw_id is not None:
                direction_nav.line = raw_id
        return ActionResult.accepted_with()

    def destination_stations_auto(
        snapshot, context: NavigationContext
    ) -> ActionResult:
        vm = _get_list_vm(context)
        if vm is not None and vm.option_count > 0:
            raw_id = vm.items[0].get("id")
            if raw_id is not None:
                direction_nav.station = raw_id
        return ActionResult.accepted_with()

    def destination_lines_auto(snapshot, context: NavigationContext) -> ActionResult:
        vm = _get_list_vm(context)
        if vm is not None and vm.option_count > 0:
            raw_id = vm.items[0].get("id")
            if raw_id is not None:
                direction_nav.line = raw_id
        return ActionResult.accepted_with()

    return (
        direction_lines_auto,
        undirection_lines_auto,
        source_stations_auto,
        source_lines_auto,
        destination_stations_auto,
        destination_lines_auto,
    )


# ---------------------------------------------------------------------------
# Undirection cross-navigation commands (l/s in undirection list states)
# ---------------------------------------------------------------------------


def _build_undirection_cross_commands(undirection_nav):
    def list_line_command(snapshot, context: NavigationContext) -> ActionResult:
        undirection_nav.line = None
        return ActionResult.accepted_with()

    def list_station_command(snapshot, context: NavigationContext) -> ActionResult:
        undirection_nav.station = None
        return ActionResult.accepted_with()

    return list_line_command, list_station_command


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

    guards[G_RETURN_IS_DIRECTION_RUN] = _return_is_direction_run
    guards[G_RETURN_IS_PLAN_RUN] = _return_is_plan_run

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
    G_HAS_PREVIOUS,
    G_HAS_NO_PREVIOUS,
    G_HAS_NEXT,
    G_HAS_NO_NEXT,
    G_HELP_SELECTED_MODE,
    G_HELP_SELECTED_BROWSER,
    G_HELP_SELECTED_STATION,
    G_HELP_SELECTED_LINE,
    G_HELP_SELECTED_ENDPOINT,
    G_UNDIRECTION_LEFT_HAS_NEXT,
    G_UNDIRECTION_LEFT_NO_NEXT_EXTRA,
    G_UNDIRECTION_RIGHT_HAS_NEXT,
    G_UNDIRECTION_RIGHT_NO_NEXT_EXTRA,
    G_HAS_SUB_LINE_TRANSFER,
    G_HAS_NO_SUB_LINE_TRANSFER,
})


# ---------------------------------------------------------------------------
# Action registry builder
# ---------------------------------------------------------------------------


def _to_str_id(val):
    if isinstance(val, str):
        return val
    if hasattr(val, "__iter__") and not isinstance(val, str):
        return str(list(val))
    return str(val)


def _build_open_help():
    def open_help(snapshot, context: NavigationContext) -> ActionResult:
        context.return_state = snapshot.state
        return ActionResult.accepted_with()
    return open_help


def build_action_registry(
    direction_nav=None, undirection_nav=None
) -> dict[ActionId, callable]:
    actions: dict[ActionId, callable] = {}

    actions[A_LIST_MOVE_UP] = _move_up
    actions[A_LIST_MOVE_DOWN] = _move_down
    actions[A_LIST_MOVE_HOME] = _move_home
    actions[A_LIST_MOVE_END] = _move_end
    actions[A_OPEN_HELP] = _build_open_help()

    if direction_nav is not None:
        sel_dir, sel_undir, sel_plan = _build_mode_select_actions(
            direction_nav, undirection_nav
        )
        actions[A_SELECT_DIRECTION] = sel_dir
        actions[A_SELECT_UNDIRECTED] = sel_undir
        actions[A_SELECT_PLAN] = sel_plan

        sc, lc = _build_stations_lines_confirm(direction_nav)
        actions[A_STATIONS_CONFIRM] = sc
        actions[A_LINES_CONFIRM] = lc

        lcl, lcs = _build_list_cross_commands(direction_nav)
        actions[A_LIST_LINE_COMMAND] = lcl
        actions[A_LIST_STATION_COMMAND] = lcs

        dsc, dlc = _build_direction_stations_lines_confirm(direction_nav)
        actions[A_DIRECTION_STATIONS_CONFIRM] = dsc
        actions[A_DIRECTION_LINES_CONFIRM] = dlc

        depc = _build_direction_end_point_confirm(direction_nav)
        actions[A_DIRECTION_END_POINT_CONFIRM] = depc

        dl, dr, de = _build_direction_run_actions(direction_nav)
        actions[A_DIRECTION_LEFT] = dl
        actions[A_DIRECTION_RIGHT] = dr
        actions[A_DIRECTION_RUN_ENDPOINT] = de

        pl, pr = _build_plan_run_actions(direction_nav)
        actions[A_PLAN_LEFT] = pl
        actions[A_PLAN_RIGHT] = pr

        (
            dtu,
            dtd,
            dtc,
            dtq,
        ) = _build_direction_transfer_actions(direction_nav)
        actions[A_DIRECTION_TRANSFER_UP] = dtu
        actions[A_DIRECTION_TRANSFER_DOWN] = dtd
        actions[A_DIRECTION_TRANSFER_CONFIRM] = dtc
        actions[A_DIRECTION_TRANSFER_QUIT] = dtq

        dru, drd = _build_direction_run_transfer_actions(direction_nav)
        actions[A_DIRECTION_RUN_UP] = dru
        actions[A_DIRECTION_RUN_DOWN] = drd

        enc, enq = _build_explore_neighbor_actions(direction_nav)
        actions[A_EXPLORE_NEIGHBOR_CONFIRM] = enc
        actions[A_EXPLORE_NEIGHBOR_QUIT] = enq

        src_sc, src_lc = _build_source_stations_lines_confirm(direction_nav)
        actions[A_SOURCE_STATIONS_CONFIRM] = src_sc
        actions[A_SOURCE_LINES_CONFIRM] = src_lc

        dst_sc, dst_lc = _build_destination_stations_lines_confirm(direction_nav)
        actions[A_DESTINATION_STATIONS_CONFIRM] = dst_sc
        actions[A_DESTINATION_LINES_CONFIRM] = dst_lc

        mq, sq, lq = _build_quit_actions(direction_nav)
        actions[A_MODE_QUIT] = mq
        actions[A_STATIONS_QUIT] = sq
        actions[A_LINES_QUIT] = lq

        (
            dla,
            ula,
            ssa,
            sla,
            dsa,
            dla2,
        ) = _build_auto_actions(direction_nav)
        actions[A_DIRECTION_LINES_AUTO] = dla
        actions[A_UNDIRECTION_LINES_AUTO] = ula
        actions[A_SOURCE_STATIONS_AUTO] = ssa
        actions[A_SOURCE_LINES_AUTO] = sla
        actions[A_DESTINATION_STATIONS_AUTO] = dsa
        actions[A_DESTINATION_LINES_AUTO] = dla2

    if undirection_nav is not None and direction_nav is not None:
        hc, hq = _build_help_actions(direction_nav, undirection_nav)
        actions[A_HELP_CONFIRM] = hc
        actions[A_HELP_QUIT] = hq

        rm, rb = _build_run_common_actions(direction_nav, undirection_nav)
        actions[A_RUN_MODE] = rm
        actions[A_RUN_BROWSER] = rb

    if undirection_nav is not None:
        ul, ur = _build_undirection_run_actions(undirection_nav)
        actions[A_UNDIRECTION_LEFT] = ul
        actions[A_UNDIRECTION_RIGHT] = ur

        (
            utu,
            utd,
            utc,
            utq,
        ) = _build_undirection_transfer_actions(undirection_nav)
        actions[A_UNDIRECTION_TRANSFER_UP] = utu
        actions[A_UNDIRECTION_TRANSFER_DOWN] = utd
        actions[A_UNDIRECTION_TRANSFER_CONFIRM] = utc
        actions[A_UNDIRECTION_TRANSFER_QUIT] = utq

        uru, urd = _build_undirection_run_transfer_actions(undirection_nav)
        actions[A_UNDIRECTION_RUN_UP] = uru
        actions[A_UNDIRECTION_RUN_DOWN] = urd

        eslc, eslq = _build_explore_sub_line_actions(undirection_nav)
        actions[A_EXPLORE_SUB_LINE_CONFIRM] = eslc
        actions[A_EXPLORE_SUB_LINE_QUIT] = eslq

        usc, ulc, uslc = _build_undirection_stations_lines_confirm(undirection_nav)
        actions[A_UNDIRECTION_STATIONS_CONFIRM] = usc
        actions[A_UNDIRECTION_LINES_CONFIRM] = ulc
        actions[A_UNDIRECTION_SUB_LINES_CONFIRM] = uslc

        ulcl, ulcs = _build_undirection_cross_commands(undirection_nav)
        actions[A_LIST_LINE_COMMAND] = ulcl
        actions[A_LIST_STATION_COMMAND] = ulcs

    return actions


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
# Entry effects (lifecycle handlers)
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
        if snapshot.return_state is not None:
            rs = snapshot.return_state
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
# Exit effects (lifecycle handlers)
# ---------------------------------------------------------------------------


def build_exit_effects(
    direction_nav=None, undirection_nav=None
) -> dict[NavigationStateId, callable]:
    exit_map: dict[NavigationStateId, callable] = {}

    def mode_exit(snapshot, context):
        return PresentationEffects(close_messages=("功能選單關閉",))

    exit_map[NavigationStateId.MODE] = mode_exit

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

    def stations_exit(snapshot, context):
        return PresentationEffects(close_messages=("車站瀏覽選單關閉",))

    exit_map[NavigationStateId.STATIONS] = stations_exit
    exit_map[NavigationStateId.LINES] = stations_exit

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
