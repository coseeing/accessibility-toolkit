from __future__ import annotations

from apps.access8graph.navigation.actions import (
    common,
    mode_selection,
    direction,
    undirected,
    route_plan,
    transfer,
)


class DuplicateActionError(Exception):
    pass


class DuplicateGuardError(Exception):
    pass


def build_action_registry(
    direction_nav=None, undirection_nav=None
) -> dict[str, callable]:
    from apps.access8graph.navigation.model import ActionId

    actions: dict[ActionId, callable] = {}
    actions.update(common.build_base_actions())

    for module in [mode_selection, direction, undirected, route_plan, transfer]:
        module_actions = module.build_actions(direction_nav, undirection_nav)
        for key, val in module_actions.items():
            if key in actions and actions[key] is not val:
                raise DuplicateActionError(
                    f"Duplicate action ID '{key.value}' from multiple family modules"
                )
            actions[key] = val

    return actions


build_guard_registry = common.build_guard_registry
build_entry_effects = common.build_entry_effects
build_exit_effects = common.build_exit_effects
build_snapshot_factory = common.build_snapshot_factory

# Re-export everything for backward compatibility
from apps.access8graph.navigation.actions.common import (
    ListViewModel,
    RunViewModel,
    A_NOOP,
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
    A_DIRECTION_RUN_UP,
    A_DIRECTION_RUN_DOWN,
    A_UNDIRECTION_RUN_UP,
    A_UNDIRECTION_RUN_DOWN,
    A_OPEN_HELP,
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
    ALL_ACTION_IDS,
    ALL_GUARD_IDS,
)
