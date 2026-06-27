from __future__ import annotations

from apps.access8graph.navigation.model import (
    NavigationCommand,
    NavigationStateId,
    TransitionRule,
)

from apps.access8graph.navigation.actions.common import (
    G_IS_DIRECTION_SELECTED,
    G_IS_UNDIRECTION_SELECTED,
    G_IS_PLAN_SELECTED,
    G_RETURN_IS_DIRECTION_RUN,
    G_RETURN_IS_PLAN_RUN,
)


def _r(source, command, target, action, guard=None):
    return TransitionRule(source, command, target, action, guard)


def build_rules() -> tuple[TransitionRule, ...]:
    from apps.access8graph.navigation.actions.common import (
        A_SELECT_DIRECTION,
        A_SELECT_UNDIRECTED,
        A_SELECT_PLAN,
        A_MODE_QUIT,
    )

    rules: list[TransitionRule] = []

    M = NavigationStateId.MODE
    rules.append(
        _r(M, NavigationCommand.CONFIRM, NavigationStateId.DIRECTION_LINES,
           A_SELECT_DIRECTION, G_IS_DIRECTION_SELECTED)
    )
    rules.append(
        _r(M, NavigationCommand.CONFIRM, NavigationStateId.UNDIRECTION_LINES,
           A_SELECT_UNDIRECTED, G_IS_UNDIRECTION_SELECTED)
    )
    rules.append(
        _r(M, NavigationCommand.CONFIRM, NavigationStateId.SOURCE_LINES,
           A_SELECT_PLAN, G_IS_PLAN_SELECTED)
    )
    rules.append(
        _r(M, NavigationCommand.SELECT_DIRECTION, NavigationStateId.DIRECTION_LINES,
           A_SELECT_DIRECTION)
    )
    rules.append(
        _r(M, NavigationCommand.SELECT_UNDIRECTED, NavigationStateId.UNDIRECTION_LINES,
           A_SELECT_UNDIRECTED)
    )
    rules.append(
        _r(M, NavigationCommand.SELECT_PLAN, NavigationStateId.SOURCE_LINES,
           A_SELECT_PLAN)
    )
    rules.append(
        _r(M, NavigationCommand.QUIT, NavigationStateId.DIRECTION_RUN,
           A_MODE_QUIT, G_RETURN_IS_DIRECTION_RUN)
    )
    rules.append(
        _r(M, NavigationCommand.QUIT, NavigationStateId.PLAN_RUN,
           A_MODE_QUIT, G_RETURN_IS_PLAN_RUN)
    )

    return tuple(rules)
