from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass

from apps.access8graph.navigation.model import (
    ActionId,
    GuardId,
    NavigationCommand,
    NavigationStateId,
    TransitionRule,
)
from apps.access8graph.navigation.actions import (
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
    A_DIRECTION_RUN_UP,
    A_DIRECTION_RUN_DOWN,
    A_UNDIRECTION_RUN_UP,
    A_UNDIRECTION_RUN_DOWN,
    G_CAN_MOVE_UP,
    G_CAN_MOVE_DOWN,
    G_IS_DIRECTION_SELECTED,
    G_IS_UNDIRECTION_SELECTED,
    G_IS_PLAN_SELECTED,
    G_HAS_ONE_OPTION,
    G_HAS_LINE,
    G_HAS_STATION,
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
    G_HAS_SUB_LINE_TRANSFER,
)


class TransitionTableValidationError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class TransitionTable:
    rules: frozenset[TransitionRule]
    index: dict[tuple[NavigationStateId, NavigationCommand], tuple[TransitionRule, ...]]
    initial_state: NavigationStateId
    action_ids: frozenset[ActionId]
    guard_ids: frozenset[GuardId]

    def lookup(
        self, source: NavigationStateId, command: NavigationCommand
    ) -> tuple[TransitionRule, ...]:
        return self.index.get((source, command), ())


def validate_transition_table(
    *,
    rules: Iterable[TransitionRule],
    initial_state: NavigationStateId,
    action_ids: set[ActionId] | frozenset[ActionId],
    guard_ids: set[GuardId] | frozenset[GuardId],
) -> TransitionTable:
    rules_tuple = tuple(rules)

    if not rules_tuple:
        raise TransitionTableValidationError("transition table must have at least one rule")

    _validate_ids(rules_tuple, action_ids, guard_ids)
    index = _build_index(rules_tuple)
    _validate_unguarded_conflicts(index)
    _validate_reachability(index, initial_state)
    _validate_auto_cycles(index)
    _validate_help_return(index)

    immutable_index = {
        key: tuple(rules_list) for key, rules_list in index.items()
    }

    return TransitionTable(
        rules=frozenset(rules_tuple),
        index=immutable_index,
        initial_state=initial_state,
        action_ids=frozenset(action_ids) if isinstance(action_ids, set) else action_ids,
        guard_ids=frozenset(guard_ids) if isinstance(guard_ids, set) else guard_ids,
    )


def _guard_val(g: GuardId | str) -> str:
    return g.value if isinstance(g, GuardId) else str(g)


def _validate_ids(
    rules: tuple[TransitionRule, ...],
    action_ids: set[ActionId] | frozenset[ActionId],
    guard_ids: set[GuardId] | frozenset[GuardId],
) -> None:
    action_set = set(action_ids)
    guard_set = {_guard_val(g) for g in guard_ids}
    action_values = {a.value for a in action_set}

    for r in rules:
        if r.action_id.value not in action_values:
            raise TransitionTableValidationError(
                f"unknown action id '{r.action_id.value}' in rule {r.source}->{r.target}"
            )
        if r.guard_id is not None and _guard_val(r.guard_id) not in guard_set:
            raise TransitionTableValidationError(
                f"unknown guard id '{_guard_val(r.guard_id)}' in rule {r.source}->{r.target}"
            )


def _build_index(
    rules: tuple[TransitionRule, ...],
) -> dict[tuple[NavigationStateId, NavigationCommand], list[TransitionRule]]:
    index: dict[tuple[NavigationStateId, NavigationCommand], list[TransitionRule]] = {}
    for r in rules:
        key = (r.source, r.command)
        index.setdefault(key, []).append(r)
    return index


def _validate_unguarded_conflicts(
    index: dict[tuple[NavigationStateId, NavigationCommand], list[TransitionRule]],
) -> None:
    for key, rule_list in index.items():
        unguarded = [r for r in rule_list if r.guard_id is None]
        guarded = [r for r in rule_list if r.guard_id is not None]

        if len(unguarded) > 1:
            raise TransitionTableValidationError(
                f"duplicate unguarded rules for source={key[0].value} command={key[1].value}"
            )
        if unguarded and guarded:
            raise TransitionTableValidationError(
                f"guarded and unguarded rules conflict for "
                f"source={key[0].value} command={key[1].value}"
            )


def _validate_reachability(
    index: dict[tuple[NavigationStateId, NavigationCommand], list[TransitionRule]],
    initial_state: NavigationStateId,
) -> None:
    all_states: set[NavigationStateId] = set()
    for key, rule_list in index.items():
        all_states.add(key[0])
        for r in rule_list:
            all_states.add(r.target)

    if initial_state not in all_states:
        raise TransitionTableValidationError(
            f"invalid initial state '{initial_state.value}': not referenced in any rule"
        )

    reachable: set[NavigationStateId] = set()
    queue: deque[NavigationStateId] = deque([initial_state])
    while queue:
        state = queue.popleft()
        if state in reachable:
            continue
        reachable.add(state)
        for command in NavigationCommand:
            key = (state, command)
            for r in index.get(key, ()):
                if r.target not in reachable:
                    queue.append(r.target)

    unreachable = all_states - reachable
    if unreachable:
        names = ", ".join(sorted(s.value for s in unreachable))
        raise TransitionTableValidationError(
            f"unreachable states from initial state '{initial_state.value}': {names}"
        )


def _validate_help_return(
    index: dict[tuple[NavigationStateId, NavigationCommand], list[TransitionRule]],
) -> None:
    help_state = NavigationStateId.HELP
    help_outgoing = False

    for (source, _command), rule_list in index.items():
        for r in rule_list:
            if source == help_state and r.target != help_state:
                help_outgoing = True

    if not help_outgoing:
        raise TransitionTableValidationError(
            "missing HELP return edge: need at least one rule from HELP to another state"
        )


def _validate_auto_cycles(
    index: dict[tuple[NavigationStateId, NavigationCommand], list[TransitionRule]],
) -> None:
    def _dfs(state: NavigationStateId, path: list[NavigationStateId]) -> list[list[NavigationStateId]] | None:
        if state in path:
            return [path + [state]]
        cycles: list[list[NavigationStateId]] = []
        auto_rules = index.get((state, NavigationCommand.AUTO), ())
        for r in auto_rules:
            if r.guard_id is not None:
                continue
            result = _dfs(r.target, path + [state])
            if result is not None:
                cycles.extend(result)
        return cycles if cycles else None

    for (source, _command), rule_list in index.items():
        for r in rule_list:
            if r.command != NavigationCommand.AUTO or r.guard_id is not None:
                continue
            cycles = _dfs(source, [])
            if cycles is not None:
                cycle_paths = " | ".join(
                    " -> ".join(s.value for s in c) for c in cycles
                )
                raise TransitionTableValidationError(
                    f"static AUTO cycle detected: {cycle_paths}"
                )


# ---------------------------------------------------------------------------
# Complete transition table builder
# ---------------------------------------------------------------------------


def _r(source, command, target, action, guard=None):
    return TransitionRule(source, command, target, action, guard)


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

_STATES_WITH_HELP = {
    NavigationStateId.STATIONS,
    NavigationStateId.LINES,
    NavigationStateId.DIRECTION_STATIONS,
    NavigationStateId.DIRECTION_LINES,
    NavigationStateId.UNDIRECTION_STATIONS,
    NavigationStateId.UNDIRECTION_LINES,
    NavigationStateId.SOURCE_STATIONS,
    NavigationStateId.SOURCE_LINES,
    NavigationStateId.DESTINATION_STATIONS,
    NavigationStateId.DESTINATION_LINES,
    NavigationStateId.DIRECTION_RUN,
    NavigationStateId.UNDIRECTION_RUN,
    NavigationStateId.PLAN_RUN,
}

_RUN_STATES = {
    NavigationStateId.DIRECTION_RUN,
    NavigationStateId.UNDIRECTION_RUN,
    NavigationStateId.PLAN_RUN,
}


def build_transition_rules() -> list[TransitionRule]:
    rules: list[TransitionRule] = []

    # ── Universal list movement ──────────────────────────────────────
    for st in _LIST_STATES:
        rules.append(_r(st, NavigationCommand.UP, st, A_LIST_MOVE_UP, G_CAN_MOVE_UP))
        rules.append(
            _r(st, NavigationCommand.DOWN, st, A_LIST_MOVE_DOWN, G_CAN_MOVE_DOWN)
        )
        rules.append(_r(st, NavigationCommand.HOME, st, A_LIST_MOVE_HOME))
        rules.append(_r(st, NavigationCommand.END, st, A_LIST_MOVE_END))

    # ── MODE ─────────────────────────────────────────────────────────
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

    # ── STATIONS (browser) ───────────────────────────────────────────
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

    # ── LINES (browser) ──────────────────────────────────────────────
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

    return rules
