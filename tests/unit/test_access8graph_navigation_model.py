from dataclasses import FrozenInstanceError

import pytest

from apps.access8graph.navigation.model import (
    ActionId,
    GuardId,
    NavigationCommand,
    NavigationStateId,
    TransitionOutcome,
    TransitionRule,
)


def test_command_and_state_ids_are_closed_string_enums():
    assert NavigationCommand.DOWN.value == "down"
    assert NavigationCommand.AUTO.value == "auto"
    assert NavigationStateId.MODE.value == "mode"
    assert NavigationStateId.HELP.value == "help"


def test_transition_rule_has_one_fixed_target():
    rule = TransitionRule(
        source=NavigationStateId.MODE,
        command=NavigationCommand.DOWN,
        target=NavigationStateId.MODE,
        action_id=ActionId("move_down"),
        guard_id=GuardId("can_move_down"),
    )

    with pytest.raises(FrozenInstanceError):
        rule.target = NavigationStateId.LINES
    assert not hasattr(rule, "allowed_targets")
