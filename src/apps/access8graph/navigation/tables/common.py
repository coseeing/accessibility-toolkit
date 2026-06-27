from __future__ import annotations

from apps.access8graph.navigation.model import (
    NavigationCommand,
    NavigationStateId,
    TransitionRule,
)

from apps.access8graph.navigation.actions.common import (
    G_RETURN_IS_DIRECTION_RUN,
    G_RETURN_IS_PLAN_RUN,
)


def _r(source, command, target, action, guard=None):
    return TransitionRule(source, command, target, action, guard)


def build_rules() -> tuple[TransitionRule, ...]:
    from apps.access8graph.navigation.actions.common import (
        A_STATIONS_CONFIRM,
        A_LINES_CONFIRM,
        A_LIST_LINE_COMMAND,
        A_LIST_STATION_COMMAND,
        A_STATIONS_QUIT,
        A_LINES_QUIT,
        A_OPEN_HELP,
    )

    rules: list[TransitionRule] = []

    S = NavigationStateId.STATIONS
    rules.append(
        _r(S, NavigationCommand.CONFIRM, NavigationStateId.LINES, A_STATIONS_CONFIRM)
    )
    rules.append(
        _r(S, NavigationCommand.SELECT_LINE, NavigationStateId.LINES,
           A_LIST_LINE_COMMAND)
    )
    rules.append(
        _r(S, NavigationCommand.QUIT, NavigationStateId.DIRECTION_RUN,
           A_STATIONS_QUIT, G_RETURN_IS_DIRECTION_RUN)
    )
    rules.append(
        _r(S, NavigationCommand.QUIT, NavigationStateId.PLAN_RUN,
           A_STATIONS_QUIT, G_RETURN_IS_PLAN_RUN)
    )
    rules.append(
        _r(S, NavigationCommand.OPEN_HELP, NavigationStateId.HELP, A_OPEN_HELP)
    )

    L = NavigationStateId.LINES
    rules.append(
        _r(L, NavigationCommand.CONFIRM, NavigationStateId.STATIONS, A_LINES_CONFIRM)
    )
    rules.append(
        _r(L, NavigationCommand.SELECT_STATION, NavigationStateId.STATIONS,
           A_LIST_STATION_COMMAND)
    )
    rules.append(
        _r(L, NavigationCommand.QUIT, NavigationStateId.DIRECTION_RUN,
           A_LINES_QUIT, G_RETURN_IS_DIRECTION_RUN)
    )
    rules.append(
        _r(L, NavigationCommand.QUIT, NavigationStateId.PLAN_RUN,
           A_LINES_QUIT, G_RETURN_IS_PLAN_RUN)
    )
    rules.append(
        _r(L, NavigationCommand.OPEN_HELP, NavigationStateId.HELP, A_OPEN_HELP)
    )

    return tuple(rules)
