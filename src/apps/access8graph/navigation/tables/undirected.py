from __future__ import annotations

from apps.access8graph.navigation.model import (
    NavigationCommand,
    NavigationStateId,
    TransitionRule,
)

from apps.access8graph.navigation.actions.common import (
    G_HAS_PREVIOUS,
    G_HAS_NO_PREVIOUS,
    G_HAS_NEXT,
    G_HAS_NO_NEXT,
    G_HAS_LINE,
    G_HAS_NO_LINE,
    G_HAS_STATION,
    G_HAS_NO_STATION,
    G_HAS_ONE_OPTION,
)


def _r(source, command, target, action, guard=None):
    return TransitionRule(source, command, target, action, guard)


def build_rules() -> tuple[TransitionRule, ...]:
    from apps.access8graph.navigation.actions.common import (
        A_UNDIRECTION_LEFT,
        A_UNDIRECTION_RIGHT,
        A_UNDIRECTION_RUN_UP,
        A_UNDIRECTION_RUN_DOWN,
        A_RUN_MODE,
        A_RUN_BROWSER,
        A_UNDIRECTION_STATIONS_CONFIRM,
        A_UNDIRECTION_LINES_CONFIRM,
        A_UNDIRECTION_SUB_LINES_CONFIRM,
        A_LIST_LINE_COMMAND,
        A_LIST_STATION_COMMAND,
        A_OPEN_HELP,
        A_UNDIRECTION_LINES_AUTO,
    )

    rules: list[TransitionRule] = []

    M = NavigationStateId.MODE
    L = NavigationStateId.LINES

    # ── UNDIRECTION_RUN ──────────────────────────────────────────────
    UR = NavigationStateId.UNDIRECTION_RUN
    rules.append(
        _r(UR, NavigationCommand.LEFT, UR, A_UNDIRECTION_LEFT, G_HAS_PREVIOUS)
    )
    rules.append(
        _r(UR, NavigationCommand.LEFT, NavigationStateId.EXPLORE_SUB_LINE,
           A_UNDIRECTION_LEFT, G_HAS_NO_PREVIOUS)
    )
    rules.append(
        _r(UR, NavigationCommand.RIGHT, UR, A_UNDIRECTION_RIGHT, G_HAS_NEXT)
    )
    rules.append(
        _r(UR, NavigationCommand.RIGHT, NavigationStateId.EXPLORE_SUB_LINE,
           A_UNDIRECTION_RIGHT, G_HAS_NO_NEXT)
    )
    rules.append(
        _r(UR, NavigationCommand.UP, NavigationStateId.UNDIRECTION_TRANSFER,
           A_UNDIRECTION_RUN_UP)
    )
    rules.append(
        _r(UR, NavigationCommand.DOWN, NavigationStateId.UNDIRECTION_TRANSFER,
           A_UNDIRECTION_RUN_DOWN)
    )
    rules.append(
        _r(UR, NavigationCommand.OPEN_MODE, M, A_RUN_MODE)
    )
    rules.append(
        _r(UR, NavigationCommand.OPEN_BROWSER, L, A_RUN_BROWSER)
    )
    rules.append(
        _r(UR, NavigationCommand.OPEN_HELP, NavigationStateId.HELP, A_OPEN_HELP)
    )

    # ── UNDIRECTION_STATIONS ─────────────────────────────────────────
    US = NavigationStateId.UNDIRECTION_STATIONS
    rules.append(
        _r(US, NavigationCommand.CONFIRM, NavigationStateId.UNDIRECTION_SUB_LINES,
           A_UNDIRECTION_STATIONS_CONFIRM, G_HAS_LINE)
    )
    rules.append(
        _r(US, NavigationCommand.CONFIRM, NavigationStateId.UNDIRECTION_LINES,
           A_UNDIRECTION_STATIONS_CONFIRM, G_HAS_NO_LINE)
    )
    rules.append(
        _r(US, NavigationCommand.SELECT_LINE, NavigationStateId.UNDIRECTION_LINES,
           A_LIST_LINE_COMMAND)
    )
    rules.append(
        _r(US, NavigationCommand.OPEN_HELP, NavigationStateId.HELP, A_OPEN_HELP)
    )

    # ── UNDIRECTION_LINES ────────────────────────────────────────────
    UL = NavigationStateId.UNDIRECTION_LINES
    rules.append(
        _r(UL, NavigationCommand.CONFIRM, NavigationStateId.UNDIRECTION_SUB_LINES,
           A_UNDIRECTION_LINES_CONFIRM, G_HAS_STATION)
    )
    rules.append(
        _r(UL, NavigationCommand.CONFIRM, NavigationStateId.UNDIRECTION_STATIONS,
           A_UNDIRECTION_LINES_CONFIRM, G_HAS_NO_STATION)
    )
    rules.append(
        _r(UL, NavigationCommand.SELECT_STATION, NavigationStateId.UNDIRECTION_STATIONS,
           A_LIST_STATION_COMMAND)
    )
    rules.append(
        _r(UL, NavigationCommand.AUTO, NavigationStateId.UNDIRECTION_STATIONS,
           A_UNDIRECTION_LINES_AUTO, G_HAS_ONE_OPTION)
    )
    rules.append(
        _r(UL, NavigationCommand.OPEN_HELP, NavigationStateId.HELP, A_OPEN_HELP)
    )

    # ── UNDIRECTION_SUB_LINES ────────────────────────────────────────
    USL = NavigationStateId.UNDIRECTION_SUB_LINES
    rules.append(
        _r(USL, NavigationCommand.CONFIRM, UR, A_UNDIRECTION_SUB_LINES_CONFIRM)
    )

    return tuple(rules)
