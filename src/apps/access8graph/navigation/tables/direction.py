from __future__ import annotations

from apps.access8graph.navigation.model import (
    NavigationCommand,
    NavigationStateId,
    TransitionRule,
)

from apps.access8graph.navigation.actions.common import (
    G_HAS_LINE,
    G_HAS_NO_LINE,
    G_HAS_STATION,
    G_HAS_NO_STATION,
    G_HAS_ONE_OPTION,
    G_HAS_ONE_REVERSE,
    G_HAS_MULTI_REVERSE,
)


def _r(source, command, target, action, guard=None):
    return TransitionRule(source, command, target, action, guard)


def build_rules() -> tuple[TransitionRule, ...]:
    from apps.access8graph.navigation.actions.common import (
        A_DIRECTION_STATIONS_CONFIRM,
        A_DIRECTION_LINES_CONFIRM,
        A_DIRECTION_END_POINT_CONFIRM,
        A_DIRECTION_LEFT,
        A_DIRECTION_RIGHT,
        A_DIRECTION_RUN_ENDPOINT,
        A_DIRECTION_RUN_UP,
        A_DIRECTION_RUN_DOWN,
        A_RUN_MODE,
        A_RUN_BROWSER,
        A_LIST_LINE_COMMAND,
        A_LIST_STATION_COMMAND,
        A_OPEN_HELP,
        A_DIRECTION_LINES_AUTO,
    )

    rules: list[TransitionRule] = []

    # ── DIRECTION_STATIONS ───────────────────────────────────────────
    DS = NavigationStateId.DIRECTION_STATIONS
    rules.append(
        _r(DS, NavigationCommand.CONFIRM, NavigationStateId.DIRECTION_END_POINT,
           A_DIRECTION_STATIONS_CONFIRM, G_HAS_LINE)
    )
    rules.append(
        _r(DS, NavigationCommand.CONFIRM, NavigationStateId.DIRECTION_LINES,
           A_DIRECTION_STATIONS_CONFIRM, G_HAS_NO_LINE)
    )
    rules.append(
        _r(DS, NavigationCommand.SELECT_LINE, NavigationStateId.DIRECTION_LINES,
           A_LIST_LINE_COMMAND)
    )
    rules.append(
        _r(DS, NavigationCommand.OPEN_HELP, NavigationStateId.HELP, A_OPEN_HELP)
    )

    # ── DIRECTION_LINES ──────────────────────────────────────────────
    DL = NavigationStateId.DIRECTION_LINES
    rules.append(
        _r(DL, NavigationCommand.CONFIRM, NavigationStateId.DIRECTION_END_POINT,
           A_DIRECTION_LINES_CONFIRM, G_HAS_STATION)
    )
    rules.append(
        _r(DL, NavigationCommand.CONFIRM, NavigationStateId.DIRECTION_STATIONS,
           A_DIRECTION_LINES_CONFIRM, G_HAS_NO_STATION)
    )
    rules.append(
        _r(DL, NavigationCommand.SELECT_STATION, NavigationStateId.DIRECTION_STATIONS,
           A_LIST_STATION_COMMAND)
    )
    rules.append(
        _r(DL, NavigationCommand.AUTO, NavigationStateId.DIRECTION_STATIONS,
           A_DIRECTION_LINES_AUTO, G_HAS_ONE_OPTION)
    )
    rules.append(
        _r(DL, NavigationCommand.OPEN_HELP, NavigationStateId.HELP, A_OPEN_HELP)
    )

    # ── DIRECTION_END_POINT ──────────────────────────────────────────
    DEP = NavigationStateId.DIRECTION_END_POINT
    rules.append(
        _r(DEP, NavigationCommand.CONFIRM, NavigationStateId.DIRECTION_RUN,
           A_DIRECTION_END_POINT_CONFIRM)
    )

    # ── DIRECTION_RUN ────────────────────────────────────────────────
    M = NavigationStateId.MODE
    L = NavigationStateId.LINES
    DR = NavigationStateId.DIRECTION_RUN
    rules.append(
        _r(DR, NavigationCommand.LEFT, DR, A_DIRECTION_LEFT, G_HAS_ONE_REVERSE)
    )
    rules.append(
        _r(DR, NavigationCommand.LEFT, NavigationStateId.EXPLORE_NEIGHBOR,
           A_DIRECTION_LEFT, G_HAS_MULTI_REVERSE)
    )
    rules.append(
        _r(DR, NavigationCommand.RIGHT, DR, A_DIRECTION_RIGHT)
    )
    rules.append(
        _r(DR, NavigationCommand.UP, NavigationStateId.DIRECTION_TRANSFER,
           A_DIRECTION_RUN_UP)
    )
    rules.append(
        _r(DR, NavigationCommand.DOWN, NavigationStateId.DIRECTION_TRANSFER,
           A_DIRECTION_RUN_DOWN)
    )
    rules.append(
        _r(DR, NavigationCommand.OPEN_MODE, M, A_RUN_MODE)
    )
    rules.append(
        _r(DR, NavigationCommand.OPEN_BROWSER, L, A_RUN_BROWSER)
    )
    rules.append(
        _r(DR, NavigationCommand.SELECT_ENDPOINT, NavigationStateId.DIRECTION_END_POINT,
           A_DIRECTION_RUN_ENDPOINT)
    )
    rules.append(
        _r(DR, NavigationCommand.OPEN_HELP, NavigationStateId.HELP, A_OPEN_HELP)
    )

    return tuple(rules)
