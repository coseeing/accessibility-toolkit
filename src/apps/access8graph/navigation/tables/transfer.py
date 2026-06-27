from __future__ import annotations

from apps.access8graph.navigation.model import (
    NavigationCommand,
    NavigationStateId,
    TransitionRule,
)

from apps.access8graph.navigation.actions.common import (
    G_RETURN_IS_DIRECTION_RUN,
    G_HELP_SELECTED_MODE,
    G_HELP_SELECTED_BROWSER,
    G_HELP_SELECTED_STATION,
    G_HELP_SELECTED_LINE,
    G_HELP_SELECTED_ENDPOINT,
)


def _r(source, command, target, action, guard=None):
    return TransitionRule(source, command, target, action, guard)


def build_rules() -> tuple[TransitionRule, ...]:
    from apps.access8graph.navigation.actions.common import (
        A_DIRECTION_TRANSFER_CONFIRM,
        A_DIRECTION_TRANSFER_QUIT,
        A_UNDIRECTION_TRANSFER_CONFIRM,
        A_UNDIRECTION_TRANSFER_QUIT,
        A_EXPLORE_NEIGHBOR_CONFIRM,
        A_EXPLORE_NEIGHBOR_QUIT,
        A_EXPLORE_SUB_LINE_CONFIRM,
        A_EXPLORE_SUB_LINE_QUIT,
        A_HELP_CONFIRM,
        A_HELP_QUIT,
    )

    rules: list[TransitionRule] = []

    DR = NavigationStateId.DIRECTION_RUN
    UR = NavigationStateId.UNDIRECTION_RUN
    M = NavigationStateId.MODE
    L = NavigationStateId.LINES
    DS = NavigationStateId.DIRECTION_STATIONS
    DL = NavigationStateId.DIRECTION_LINES
    DEP = NavigationStateId.DIRECTION_END_POINT

    # ── DIRECTION_TRANSFER ───────────────────────────────────────────
    DT = NavigationStateId.DIRECTION_TRANSFER
    rules.append(
        _r(DT, NavigationCommand.CONFIRM, DR, A_DIRECTION_TRANSFER_CONFIRM)
    )
    rules.append(
        _r(DT, NavigationCommand.QUIT, DR, A_DIRECTION_TRANSFER_QUIT)
    )

    # ── UNDIRECTION_TRANSFER ─────────────────────────────────────────
    UT = NavigationStateId.UNDIRECTION_TRANSFER
    rules.append(
        _r(UT, NavigationCommand.CONFIRM, UR, A_UNDIRECTION_TRANSFER_CONFIRM)
    )
    rules.append(
        _r(UT, NavigationCommand.QUIT, UR, A_UNDIRECTION_TRANSFER_QUIT)
    )

    # ── EXPLORE_NEIGHBOR ─────────────────────────────────────────────
    EN = NavigationStateId.EXPLORE_NEIGHBOR
    rules.append(
        _r(EN, NavigationCommand.CONFIRM, DR, A_EXPLORE_NEIGHBOR_CONFIRM)
    )
    rules.append(
        _r(EN, NavigationCommand.QUIT, DR, A_EXPLORE_NEIGHBOR_QUIT)
    )

    # ── EXPLORE_SUB_LINE ─────────────────────────────────────────────
    ES = NavigationStateId.EXPLORE_SUB_LINE
    rules.append(
        _r(ES, NavigationCommand.CONFIRM, UR, A_EXPLORE_SUB_LINE_CONFIRM)
    )
    rules.append(
        _r(ES, NavigationCommand.QUIT, UR, A_EXPLORE_SUB_LINE_QUIT)
    )

    # ── HELP ─────────────────────────────────────────────────────────
    H = NavigationStateId.HELP
    rules.append(_r(H, NavigationCommand.CONFIRM, M,
                    A_HELP_CONFIRM, G_HELP_SELECTED_MODE))
    rules.append(_r(H, NavigationCommand.CONFIRM, L,
                    A_HELP_CONFIRM, G_HELP_SELECTED_BROWSER))
    rules.append(_r(H, NavigationCommand.CONFIRM, DS,
                    A_HELP_CONFIRM, G_HELP_SELECTED_STATION))
    rules.append(_r(H, NavigationCommand.CONFIRM, DL,
                    A_HELP_CONFIRM, G_HELP_SELECTED_LINE))
    rules.append(_r(H, NavigationCommand.CONFIRM, DEP,
                    A_HELP_CONFIRM, G_HELP_SELECTED_ENDPOINT))
    rules.append(_r(H, NavigationCommand.QUIT, DR,
                    A_HELP_QUIT, G_RETURN_IS_DIRECTION_RUN))

    return tuple(rules)
