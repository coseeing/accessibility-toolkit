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
    help_sources = {
        source
        for (source, command), rule_list in index.items()
        if command == NavigationCommand.OPEN_HELP
        and any(rule.target == help_state for rule in rule_list)
    }
    outgoing = [
        rule
        for (source, _command), rule_list in index.items()
        if source == help_state
        for rule in rule_list
        if rule.target != help_state
    ]

    if help_sources and not outgoing:
        raise TransitionTableValidationError(
            "missing HELP return edge: need at least one rule from HELP to another state"
        )

    quit_rules = index.get((help_state, NavigationCommand.QUIT), ())
    confirm_rules = index.get((help_state, NavigationCommand.CONFIRM), ())
    for source in help_sources:
        if not any(rule.target == source for rule in quit_rules):
            raise TransitionTableValidationError(
                f"missing HELP QUIT return coverage for {source.value}"
            )
        guard_prefix = f"help_{source.value}_selected_"
        if not any(
            rule.guard_id is not None
            and _guard_val(rule.guard_id).startswith(guard_prefix)
            for rule in confirm_rules
        ):
            raise TransitionTableValidationError(
                f"missing HELP CONFIRM return coverage for {source.value}"
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
