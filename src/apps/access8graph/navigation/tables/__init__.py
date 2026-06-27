from __future__ import annotations

from apps.access8graph.navigation.model import (
    NavigationCommand,
    NavigationStateId,
    TransitionRule,
)

from apps.access8graph.navigation.tables import (
    common,
    mode_selection,
    direction,
    undirected,
    route_plan,
    transfer,
)

from apps.access8graph.navigation.actions.common import (
    A_LIST_MOVE_UP,
    A_LIST_MOVE_DOWN,
    A_LIST_MOVE_HOME,
    A_LIST_MOVE_END,
    G_CAN_MOVE_UP,
    G_CAN_MOVE_DOWN,
)


_LIST_STATES = {
    NavigationStateId.MODE,
    NavigationStateId.STATIONS,
    NavigationStateId.LINES,
    NavigationStateId.DIRECTION_STATIONS,
    NavigationStateId.DIRECTION_LINES,
    NavigationStateId.DIRECTION_END_POINT,
    NavigationStateId.DIRECTION_TRANSFER,
    NavigationStateId.UNDIRECTION_TRANSFER,
    NavigationStateId.EXPLORE_NEIGHBOR,
    NavigationStateId.EXPLORE_SUB_LINE,
    NavigationStateId.UNDIRECTION_STATIONS,
    NavigationStateId.UNDIRECTION_LINES,
    NavigationStateId.UNDIRECTION_SUB_LINES,
    NavigationStateId.SOURCE_STATIONS,
    NavigationStateId.SOURCE_LINES,
    NavigationStateId.DESTINATION_STATIONS,
    NavigationStateId.DESTINATION_LINES,
    NavigationStateId.HELP,
}


def _r(source, command, target, action, guard=None):
    return TransitionRule(source, command, target, action, guard)


def build_transition_rules() -> list[TransitionRule]:
    rules: list[TransitionRule] = []

    # Universal list movement
    for st in _LIST_STATES:
        rules.append(_r(st, NavigationCommand.UP, st, A_LIST_MOVE_UP, G_CAN_MOVE_UP))
        rules.append(
            _r(st, NavigationCommand.DOWN, st, A_LIST_MOVE_DOWN, G_CAN_MOVE_DOWN)
        )
        rules.append(_r(st, NavigationCommand.HOME, st, A_LIST_MOVE_HOME))
        rules.append(_r(st, NavigationCommand.END, st, A_LIST_MOVE_END))

    # Family-specific rules in deterministic order
    rules.extend(mode_selection.build_rules())
    rules.extend(common.build_rules())
    rules.extend(direction.build_rules())
    rules.extend(undirected.build_rules())
    rules.extend(route_plan.build_rules())
    rules.extend(transfer.build_rules())

    return rules
