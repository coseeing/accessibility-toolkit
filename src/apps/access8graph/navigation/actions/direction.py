from __future__ import annotations

from apps.access8graph.navigation.model import (
    ActionId,
    ActionResult,
    NavigationContext,
    NavigationStateId,
    PresentationEffects,
)

from apps.access8graph.navigation.actions.common import (
    _build_run_view,
    _get_list_vm,
    _move_up,
    _move_down,
    A_DIRECTION_STATIONS_CONFIRM,
    A_DIRECTION_LINES_CONFIRM,
    A_DIRECTION_END_POINT_CONFIRM,
    A_DIRECTION_LEFT,
    A_DIRECTION_RIGHT,
    A_DIRECTION_RUN_ENDPOINT,
    A_DIRECTION_TRANSFER_UP,
    A_DIRECTION_TRANSFER_DOWN,
    A_DIRECTION_TRANSFER_CONFIRM,
    A_DIRECTION_TRANSFER_QUIT,
    A_DIRECTION_RUN_UP,
    A_DIRECTION_RUN_DOWN,
    A_EXPLORE_NEIGHBOR_CONFIRM,
    A_EXPLORE_NEIGHBOR_QUIT,
    A_SOURCE_STATIONS_CONFIRM,
    A_SOURCE_LINES_CONFIRM,
    A_DESTINATION_STATIONS_CONFIRM,
    A_DESTINATION_LINES_CONFIRM,
    A_DIRECTION_LINES_AUTO,
    A_UNDIRECTION_LINES_AUTO,
    A_SOURCE_STATIONS_AUTO,
    A_SOURCE_LINES_AUTO,
    A_DESTINATION_STATIONS_AUTO,
    A_DESTINATION_LINES_AUTO,
)


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


def _build_direction_end_point_confirm(direction_nav):
    def direction_end_point_confirm(
        snapshot, context: NavigationContext
    ) -> ActionResult:
        if snapshot.selected_id is not None:
            direction_nav.destination = snapshot.selected_id
        return ActionResult.accepted_with()

    return direction_end_point_confirm


def _build_direction_run_actions(direction_nav):
    def direction_left(snapshot, context: NavigationContext) -> ActionResult:
        pointer = direction_nav.reverse
        if len(pointer) == 1:
            direction_nav.source = direction_nav.current = pointer[0]
            context.view_model = _build_run_view(direction_nav)
            return ActionResult.accepted_with()
        if len(pointer) > 1:
            return ActionResult.accepted_with()
        return ActionResult.rejected()

    def direction_right(snapshot, context: NavigationContext) -> ActionResult:
        pointer = direction_nav.forward
        if len(pointer) == 1:
            direction_nav.current = pointer[0]
            context.view_model = _build_run_view(direction_nav)
            return ActionResult.accepted_with()
        if len(pointer) > 1:
            direction_nav.current = pointer[0]
            context.view_model = _build_run_view(direction_nav)
            return ActionResult.accepted_with()
        return ActionResult.rejected()

    def direction_run_endpoint(snapshot, context: NavigationContext) -> ActionResult:
        direction_nav.source = direction_nav.current
        direction_nav.destination = None
        return ActionResult.accepted_with()

    return direction_left, direction_right, direction_run_endpoint


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


def _build_auto_actions(direction_nav, undirection_nav):
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
                undirection_nav.line = raw_id
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


def build_actions(direction_nav=None, undirection_nav=None) -> dict[ActionId, callable]:
    actions: dict[ActionId, callable] = {}

    if direction_nav is not None:
        dsc, dlc = _build_direction_stations_lines_confirm(direction_nav)
        actions[A_DIRECTION_STATIONS_CONFIRM] = dsc
        actions[A_DIRECTION_LINES_CONFIRM] = dlc

        depc = _build_direction_end_point_confirm(direction_nav)
        actions[A_DIRECTION_END_POINT_CONFIRM] = depc

        dl, dr, de = _build_direction_run_actions(direction_nav)
        actions[A_DIRECTION_LEFT] = dl
        actions[A_DIRECTION_RIGHT] = dr
        actions[A_DIRECTION_RUN_ENDPOINT] = de

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

        (
            dla,
            ula,
            ssa,
            sla,
            dsa,
            dla2,
        ) = _build_auto_actions(direction_nav, undirection_nav)
        actions[A_DIRECTION_LINES_AUTO] = dla
        actions[A_UNDIRECTION_LINES_AUTO] = ula
        actions[A_SOURCE_STATIONS_AUTO] = ssa
        actions[A_SOURCE_LINES_AUTO] = sla
        actions[A_DESTINATION_STATIONS_AUTO] = dsa
        actions[A_DESTINATION_LINES_AUTO] = dla2

    return actions
