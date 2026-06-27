from __future__ import annotations

from apps.access8graph.navigation.model import (
    NavigationCommand,
    NavigationStateId,
    TransitionRule,
)

from apps.access8graph.navigation.actions.common import (
    G_RETURN_IS_DIRECTION_RUN,
    G_RETURN_IS_PLAN_RUN,
    G_RETURN_IS_UNDIRECTION_RUN,
    G_RETURN_IS_STATIONS,
    G_RETURN_IS_LINES,
    G_RETURN_IS_DIRECTION_STATIONS,
    G_RETURN_IS_DIRECTION_LINES,
    G_RETURN_IS_UNDIRECTION_STATIONS,
    G_RETURN_IS_UNDIRECTION_LINES,
    G_RETURN_IS_SOURCE_STATIONS,
    G_RETURN_IS_SOURCE_LINES,
    G_RETURN_IS_DESTINATION_STATIONS,
    G_RETURN_IS_DESTINATION_LINES,
    HELP_CONFIRM_GUARDS,
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
    M = NavigationStateId.MODE
    L = NavigationStateId.LINES
    S = NavigationStateId.STATIONS
    DS = NavigationStateId.DIRECTION_STATIONS
    DL = NavigationStateId.DIRECTION_LINES
    DR = NavigationStateId.DIRECTION_RUN
    UR = NavigationStateId.UNDIRECTION_RUN
    US = NavigationStateId.UNDIRECTION_STATIONS
    UL = NavigationStateId.UNDIRECTION_LINES
    PR = NavigationStateId.PLAN_RUN
    SS = NavigationStateId.SOURCE_STATIONS
    SL = NavigationStateId.SOURCE_LINES
    DS2 = NavigationStateId.DESTINATION_STATIONS
    DL2 = NavigationStateId.DESTINATION_LINES
    help_confirm_targets = {
        (S, "l"): L,
        (L, "s"): S,
        (DS, "l"): DL,
        (DL, "s"): DS,
        (US, "l"): UL,
        (UL, "s"): US,
        (SS, "l"): SL,
        (SL, "s"): SS,
        (DS2, "l"): DL2,
        (DL2, "s"): DS2,
        (DR, "m"): M,
        (DR, "v"): L,
        (UR, "m"): M,
        (UR, "v"): L,
        (PR, "m"): M,
        (PR, "v"): L,
    }
    for key, target in help_confirm_targets.items():
        rules.append(
            _r(
                H,
                NavigationCommand.CONFIRM,
                target,
                A_HELP_CONFIRM,
                HELP_CONFIRM_GUARDS[key],
            )
        )

    # HELP QUIT — return to the stored return_state (mutually exclusive guards)
    rules.append(_r(H, NavigationCommand.QUIT, DR,
                    A_HELP_QUIT, G_RETURN_IS_DIRECTION_RUN))
    rules.append(_r(H, NavigationCommand.QUIT, UR,
                    A_HELP_QUIT, G_RETURN_IS_UNDIRECTION_RUN))
    rules.append(_r(H, NavigationCommand.QUIT, PR,
                    A_HELP_QUIT, G_RETURN_IS_PLAN_RUN))
    rules.append(_r(H, NavigationCommand.QUIT, S,
                    A_HELP_QUIT, G_RETURN_IS_STATIONS))
    rules.append(_r(H, NavigationCommand.QUIT, L,
                    A_HELP_QUIT, G_RETURN_IS_LINES))
    rules.append(_r(H, NavigationCommand.QUIT, DS,
                    A_HELP_QUIT, G_RETURN_IS_DIRECTION_STATIONS))
    rules.append(_r(H, NavigationCommand.QUIT, DL,
                    A_HELP_QUIT, G_RETURN_IS_DIRECTION_LINES))
    rules.append(_r(H, NavigationCommand.QUIT, US,
                    A_HELP_QUIT, G_RETURN_IS_UNDIRECTION_STATIONS))
    rules.append(_r(H, NavigationCommand.QUIT, UL,
                    A_HELP_QUIT, G_RETURN_IS_UNDIRECTION_LINES))
    rules.append(_r(H, NavigationCommand.QUIT, SS,
                    A_HELP_QUIT, G_RETURN_IS_SOURCE_STATIONS))
    rules.append(_r(H, NavigationCommand.QUIT, SL,
                    A_HELP_QUIT, G_RETURN_IS_SOURCE_LINES))
    rules.append(_r(H, NavigationCommand.QUIT, DS2,
                    A_HELP_QUIT, G_RETURN_IS_DESTINATION_STATIONS))
    rules.append(_r(H, NavigationCommand.QUIT, DL2,
                    A_HELP_QUIT, G_RETURN_IS_DESTINATION_LINES))

    return tuple(rules)
