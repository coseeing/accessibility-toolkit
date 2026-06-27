from __future__ import annotations

from apps.access8graph.navigation.model import (
    NavigationCommand,
    NavigationStateId,
    TransitionRule,
)

from apps.access8graph.navigation.actions.common import (
    G_HAS_PREVIOUS,
    G_HAS_NEXT,
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
        A_PLAN_LEFT,
        A_PLAN_RIGHT,
        A_RUN_MODE,
        A_RUN_BROWSER,
        A_SOURCE_STATIONS_CONFIRM,
        A_SOURCE_LINES_CONFIRM,
        A_DESTINATION_STATIONS_CONFIRM,
        A_DESTINATION_LINES_CONFIRM,
        A_LIST_LINE_COMMAND,
        A_LIST_STATION_COMMAND,
        A_OPEN_HELP,
        A_SOURCE_STATIONS_AUTO,
        A_SOURCE_LINES_AUTO,
        A_DESTINATION_STATIONS_AUTO,
        A_DESTINATION_LINES_AUTO,
    )

    rules: list[TransitionRule] = []

    M = NavigationStateId.MODE
    L = NavigationStateId.LINES

    # ── PLAN_RUN ─────────────────────────────────────────────────────
    PR = NavigationStateId.PLAN_RUN
    rules.append(
        _r(PR, NavigationCommand.LEFT, PR, A_PLAN_LEFT, G_HAS_PREVIOUS)
    )
    rules.append(
        _r(PR, NavigationCommand.RIGHT, PR, A_PLAN_RIGHT, G_HAS_NEXT)
    )
    rules.append(
        _r(PR, NavigationCommand.OPEN_MODE, M, A_RUN_MODE)
    )
    rules.append(
        _r(PR, NavigationCommand.OPEN_BROWSER, L, A_RUN_BROWSER)
    )
    rules.append(
        _r(PR, NavigationCommand.OPEN_HELP, NavigationStateId.HELP, A_OPEN_HELP)
    )

    # ── SOURCE_STATIONS ──────────────────────────────────────────────
    SS = NavigationStateId.SOURCE_STATIONS
    rules.append(
        _r(SS, NavigationCommand.CONFIRM, NavigationStateId.DESTINATION_LINES,
           A_SOURCE_STATIONS_CONFIRM, G_HAS_LINE)
    )
    rules.append(
        _r(SS, NavigationCommand.CONFIRM, NavigationStateId.SOURCE_LINES,
           A_SOURCE_STATIONS_CONFIRM, G_HAS_NO_LINE)
    )
    rules.append(
        _r(SS, NavigationCommand.SELECT_LINE, NavigationStateId.SOURCE_LINES,
           A_LIST_LINE_COMMAND)
    )
    rules.append(
        _r(SS, NavigationCommand.AUTO, NavigationStateId.SOURCE_LINES,
           A_SOURCE_STATIONS_AUTO, G_HAS_ONE_OPTION)
    )
    rules.append(
        _r(SS, NavigationCommand.OPEN_HELP, NavigationStateId.HELP, A_OPEN_HELP)
    )

    # ── SOURCE_LINES ─────────────────────────────────────────────────
    SL = NavigationStateId.SOURCE_LINES
    rules.append(
        _r(SL, NavigationCommand.CONFIRM, NavigationStateId.DESTINATION_LINES,
           A_SOURCE_LINES_CONFIRM, G_HAS_STATION)
    )
    rules.append(
        _r(SL, NavigationCommand.CONFIRM, NavigationStateId.SOURCE_STATIONS,
           A_SOURCE_LINES_CONFIRM, G_HAS_NO_STATION)
    )
    rules.append(
        _r(SL, NavigationCommand.SELECT_STATION, NavigationStateId.SOURCE_STATIONS,
           A_LIST_STATION_COMMAND)
    )
    rules.append(
        _r(SL, NavigationCommand.AUTO, NavigationStateId.SOURCE_STATIONS,
           A_SOURCE_LINES_AUTO, G_HAS_ONE_OPTION)
    )
    rules.append(
        _r(SL, NavigationCommand.OPEN_HELP, NavigationStateId.HELP, A_OPEN_HELP)
    )

    # ── DESTINATION_STATIONS ─────────────────────────────────────────
    DS2 = NavigationStateId.DESTINATION_STATIONS
    rules.append(
        _r(DS2, NavigationCommand.CONFIRM, NavigationStateId.PLAN_RUN,
           A_DESTINATION_STATIONS_CONFIRM, G_HAS_LINE)
    )
    rules.append(
        _r(DS2, NavigationCommand.CONFIRM, NavigationStateId.DESTINATION_LINES,
           A_DESTINATION_STATIONS_CONFIRM, G_HAS_NO_LINE)
    )
    rules.append(
        _r(DS2, NavigationCommand.SELECT_LINE, NavigationStateId.DESTINATION_LINES,
           A_LIST_LINE_COMMAND)
    )
    rules.append(
        _r(DS2, NavigationCommand.AUTO, NavigationStateId.DESTINATION_LINES,
           A_DESTINATION_STATIONS_AUTO, G_HAS_ONE_OPTION)
    )
    rules.append(
        _r(DS2, NavigationCommand.OPEN_HELP, NavigationStateId.HELP, A_OPEN_HELP)
    )

    # ── DESTINATION_LINES ────────────────────────────────────────────
    DL2 = NavigationStateId.DESTINATION_LINES
    rules.append(
        _r(DL2, NavigationCommand.CONFIRM, NavigationStateId.PLAN_RUN,
           A_DESTINATION_LINES_CONFIRM, G_HAS_STATION)
    )
    rules.append(
        _r(DL2, NavigationCommand.CONFIRM, NavigationStateId.DESTINATION_STATIONS,
           A_DESTINATION_LINES_CONFIRM, G_HAS_NO_STATION)
    )
    rules.append(
        _r(DL2, NavigationCommand.SELECT_STATION, NavigationStateId.DESTINATION_STATIONS,
           A_LIST_STATION_COMMAND)
    )
    rules.append(
        _r(DL2, NavigationCommand.AUTO, NavigationStateId.DESTINATION_STATIONS,
           A_DESTINATION_LINES_AUTO, G_HAS_ONE_OPTION)
    )
    rules.append(
        _r(DL2, NavigationCommand.OPEN_HELP, NavigationStateId.HELP, A_OPEN_HELP)
    )

    return tuple(rules)
