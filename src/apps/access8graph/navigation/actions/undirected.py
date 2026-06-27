from __future__ import annotations

from apps.access8graph.navigation.model import (
    ActionId,
    ActionResult,
    NavigationContext,
    NavigationStateId,
    PresentationEffects,
)

from apps.access8graph.navigation.actions.common import (
    _build_undirection_run_view,
    _get_list_vm,
    _move_up,
    _move_down,
    A_UNDIRECTION_LEFT,
    A_UNDIRECTION_RIGHT,
    A_UNDIRECTION_TRANSFER_UP,
    A_UNDIRECTION_TRANSFER_DOWN,
    A_UNDIRECTION_TRANSFER_CONFIRM,
    A_UNDIRECTION_TRANSFER_QUIT,
    A_UNDIRECTION_RUN_UP,
    A_UNDIRECTION_RUN_DOWN,
    A_EXPLORE_SUB_LINE_CONFIRM,
    A_EXPLORE_SUB_LINE_QUIT,
    A_UNDIRECTION_STATIONS_CONFIRM,
    A_UNDIRECTION_LINES_CONFIRM,
    A_UNDIRECTION_SUB_LINES_CONFIRM,
)


def _build_undirection_run_actions(undirection_nav):
    def undirection_left(snapshot, context: NavigationContext) -> ActionResult:
        pointer = undirection_nav.previous
        if pointer:
            undirection_nav.current = pointer
            context.view_model = _build_undirection_run_view(undirection_nav)
            return ActionResult.accepted_with()
        return ActionResult.rejected()

    def undirection_right(snapshot, context: NavigationContext) -> ActionResult:
        pointer = undirection_nav.next
        if pointer:
            undirection_nav.current = pointer
            context.view_model = _build_undirection_run_view(undirection_nav)
            return ActionResult.accepted_with()
        return ActionResult.rejected()

    return undirection_left, undirection_right


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


def build_actions(direction_nav=None, undirection_nav=None) -> dict[ActionId, callable]:
    actions: dict[ActionId, callable] = {}

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

    return actions
