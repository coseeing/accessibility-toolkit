import pytest

from apps.access8graph.navigation.model import (
    ActionId,
    NavigationCommand,
    NavigationStateId,
    TransitionRule,
)
from apps.access8graph.navigation.table import (
    TransitionTableValidationError,
    validate_transition_table,
)


def rule(source, command, target, action="noop", guard=None):
    return TransitionRule(source, command, target, ActionId(action), guard)


def test_validator_rejects_duplicate_unguarded_rules():
    rules = (
        rule(NavigationStateId.MODE, NavigationCommand.DOWN, NavigationStateId.MODE),
        rule(NavigationStateId.MODE, NavigationCommand.DOWN, NavigationStateId.MODE),
    )

    with pytest.raises(TransitionTableValidationError, match="duplicate"):
        validate_transition_table(
            rules=rules,
            initial_state=NavigationStateId.MODE,
            action_ids={ActionId("noop")},
            guard_ids=set(),
        )


def test_validator_rejects_unknown_action():
    rules = (
        rule(NavigationStateId.MODE, NavigationCommand.DOWN, NavigationStateId.MODE),
    )

    with pytest.raises(TransitionTableValidationError, match="action"):
        validate_transition_table(
            rules=rules,
            initial_state=NavigationStateId.MODE,
            action_ids=set(),
            guard_ids=set(),
        )


def test_validator_rejects_unknown_guard():
    rules = (
        rule(
            NavigationStateId.MODE,
            NavigationCommand.DOWN,
            NavigationStateId.MODE,
            guard="unknown_guard",
        ),
    )

    with pytest.raises(TransitionTableValidationError, match="guard"):
        validate_transition_table(
            rules=rules,
            initial_state=NavigationStateId.MODE,
            action_ids={ActionId("noop")},
            guard_ids=set(),
        )


def test_validator_rejects_unguarded_plus_guarded_conflict():
    rules = (
        rule(NavigationStateId.MODE, NavigationCommand.DOWN, NavigationStateId.MODE),
        rule(
            NavigationStateId.MODE,
            NavigationCommand.DOWN,
            NavigationStateId.STATIONS,
            guard="some_guard",
        ),
    )

    with pytest.raises(TransitionTableValidationError, match="guarded.*unguarded"):
        validate_transition_table(
            rules=rules,
            initial_state=NavigationStateId.MODE,
            action_ids={ActionId("noop")},
            guard_ids={"some_guard"},
        )


def test_validator_rejects_invalid_initial_state():
    rules = (
        rule(NavigationStateId.MODE, NavigationCommand.DOWN, NavigationStateId.MODE),
    )

    with pytest.raises(TransitionTableValidationError, match="initial"):
        validate_transition_table(
            rules=rules,
            initial_state=NavigationStateId.HELP,
            action_ids={ActionId("noop")},
            guard_ids=set(),
        )


def test_validator_rejects_unreachable_state():
    rules = (
        rule(NavigationStateId.MODE, NavigationCommand.DOWN, NavigationStateId.MODE),
        rule(
            NavigationStateId.HELP,
            NavigationCommand.DOWN,
            NavigationStateId.HELP,
        ),
    )

    with pytest.raises(TransitionTableValidationError, match="unreachable"):
        validate_transition_table(
            rules=rules,
            initial_state=NavigationStateId.MODE,
            action_ids={ActionId("noop")},
            guard_ids=set(),
        )


def test_validator_rejects_missing_help_return():
    rules = (
        rule(NavigationStateId.MODE, NavigationCommand.DOWN, NavigationStateId.MODE),
        rule(
            NavigationStateId.MODE,
            NavigationCommand.OPEN_HELP,
            NavigationStateId.HELP,
        ),
    )

    with pytest.raises(TransitionTableValidationError, match="HELP.*return"):
        validate_transition_table(
            rules=rules,
            initial_state=NavigationStateId.MODE,
            action_ids={ActionId("noop")},
            guard_ids=set(),
        )


def test_validator_rejects_static_auto_cycle():
    rules = (
        rule(
            NavigationStateId.MODE,
            NavigationCommand.AUTO,
            NavigationStateId.STATIONS,
        ),
        rule(
            NavigationStateId.STATIONS,
            NavigationCommand.AUTO,
            NavigationStateId.MODE,
        ),
    )

    with pytest.raises(TransitionTableValidationError, match="AUTO.*cycle"):
        validate_transition_table(
            rules=rules,
            initial_state=NavigationStateId.MODE,
            action_ids={ActionId("noop")},
            guard_ids=set(),
        )
