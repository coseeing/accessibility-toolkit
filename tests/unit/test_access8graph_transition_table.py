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


def test_validator_rejects_incomplete_help_confirm_coverage():
    rules = (
        rule(
            NavigationStateId.MODE,
            NavigationCommand.OPEN_HELP,
            NavigationStateId.HELP,
        ),
        rule(
            NavigationStateId.HELP,
            NavigationCommand.QUIT,
            NavigationStateId.MODE,
            guard="return_is_mode",
        ),
    )

    with pytest.raises(TransitionTableValidationError, match="HELP.*CONFIRM.*mode"):
        validate_transition_table(
            rules=rules,
            initial_state=NavigationStateId.MODE,
            action_ids={ActionId("noop")},
            guard_ids={"return_is_mode"},
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


# ---------------------------------------------------------------------------
# Helper builders for parameterized negative validation tests
# ---------------------------------------------------------------------------


def _build_duplicate_rules():
    return (
        rule(NavigationStateId.MODE, NavigationCommand.DOWN, NavigationStateId.MODE),
        rule(NavigationStateId.MODE, NavigationCommand.DOWN, NavigationStateId.MODE),
    )


def _build_mixed_rules():
    return (
        rule(NavigationStateId.MODE, NavigationCommand.DOWN, NavigationStateId.MODE),
        rule(
            NavigationStateId.MODE,
            NavigationCommand.DOWN,
            NavigationStateId.STATIONS,
            guard="some_guard",
        ),
    )


def _build_unknown_action_rules():
    return (
        rule(NavigationStateId.MODE, NavigationCommand.DOWN, NavigationStateId.MODE),
    )


def _build_unknown_guard_rules():
    return (
        rule(
            NavigationStateId.MODE,
            NavigationCommand.DOWN,
            NavigationStateId.MODE,
            guard="unknown_guard",
        ),
    )


def _build_unreachable_rules():
    return (
        rule(NavigationStateId.MODE, NavigationCommand.DOWN, NavigationStateId.MODE),
        rule(
            NavigationStateId.HELP,
            NavigationCommand.DOWN,
            NavigationStateId.HELP,
        ),
    )


def _build_valid_rules():
    return (
        rule(NavigationStateId.MODE, NavigationCommand.DOWN, NavigationStateId.MODE),
    )


def _build_no_help_rules():
    return (
        rule(NavigationStateId.MODE, NavigationCommand.DOWN, NavigationStateId.MODE),
        rule(
            NavigationStateId.MODE,
            NavigationCommand.OPEN_HELP,
            NavigationStateId.HELP,
        ),
    )


def _build_auto_cycle_rules():
    return (
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


INVALID_CASES = (
    ("duplicate unguarded", _build_duplicate_rules(), "duplicate"),
    ("unguarded+guarded conflict", _build_mixed_rules(), "unguarded"),
    ("unknown action", _build_unknown_action_rules(), "action"),
    ("unknown guard", _build_unknown_guard_rules(), "guard"),
    ("unreachable state", _build_unreachable_rules(), "unreachable"),
    ("invalid initial state", _build_valid_rules(), "initial"),
    ("missing HELP return", _build_no_help_rules(), "HELP"),
    ("AUTO cycle", _build_auto_cycle_rules(), "AUTO"),
)


@pytest.mark.parametrize("name,rules,match", INVALID_CASES)
def test_validator_rejects_invalid_configuration(name, rules, match):
    from apps.access8graph.navigation.model import GuardId

    action_ids = {r.action_id for r in rules}
    guard_ids = {GuardId(r.guard_id) for r in rules if r.guard_id is not None}

    if name == "unknown action":
        action_ids = set()
    elif name == "unknown guard":
        guard_ids = set()

    if name == "invalid initial state":
        initial_state = NavigationStateId.HELP
    else:
        initial_state = NavigationStateId.MODE

    with pytest.raises(TransitionTableValidationError, match=match):
        validate_transition_table(
            rules=rules,
            initial_state=initial_state,
            action_ids=action_ids,
            guard_ids=guard_ids,
        )


def test_validator_accepts_linear_auto_chain():
    rules = (
        rule(NavigationStateId.MODE, NavigationCommand.AUTO, NavigationStateId.STATIONS),
        rule(NavigationStateId.STATIONS, NavigationCommand.AUTO, NavigationStateId.LINES),
        rule(
            NavigationStateId.LINES,
            NavigationCommand.AUTO,
            NavigationStateId.DIRECTION_RUN,
        ),
        rule(
            NavigationStateId.DIRECTION_RUN,
            NavigationCommand.DOWN,
            NavigationStateId.MODE,
        ),
        rule(
            NavigationStateId.HELP,
            NavigationCommand.QUIT,
            NavigationStateId.MODE,
            guard="return_is_mode",
        ),
        rule(
            NavigationStateId.HELP,
            NavigationCommand.CONFIRM,
            NavigationStateId.MODE,
            guard="help_mode_selected_m",
        ),
        rule(
            NavigationStateId.MODE,
            NavigationCommand.OPEN_HELP,
            NavigationStateId.HELP,
        ),
    )

    result = validate_transition_table(
        rules=rules,
        initial_state=NavigationStateId.MODE,
        action_ids={ActionId("noop")},
        guard_ids={"return_is_mode", "help_mode_selected_m"},
    )
    assert result is not None
    assert result.initial_state == NavigationStateId.MODE
