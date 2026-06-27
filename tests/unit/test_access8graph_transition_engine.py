import pytest

from apps.access8graph.navigation.model import (
    ActionId,
    ActionResult,
    GuardId,
    NavigationCommand,
    NavigationContext,
    NavigationStateId,
    PresentationEffects,
    TransitionRule,
)
from apps.access8graph.navigation.snapshot import (
    NavigationSnapshotFactory,
)


# ---------------------------------------------------------------------------
# engine import (will fail until engine.py exists)
# ---------------------------------------------------------------------------


def test_imports():
    """Smoke test that the engine module is importable."""
    from apps.access8graph.navigation.engine import (  # noqa: F401
        AmbiguousTransitionError,
        AutomaticTransitionCycleError,
        TransitionEngine,
    )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _noop_result(*args, **kwargs):
    return ActionResult.accepted_with()


def _help_edges():
    """Return two rules that satisfy the HELP return validation."""
    return (
        TransitionRule(
            source=NavigationStateId.MODE,
            command=NavigationCommand.OPEN_HELP,
            target=NavigationStateId.HELP,
            action_id=ActionId("noop"),
        ),
        TransitionRule(
            source=NavigationStateId.HELP,
            command=NavigationCommand.QUIT,
            target=NavigationStateId.MODE,
            action_id=ActionId("noop"),
        ),
    )


def _resolve_guards(raw_guards):
    """Convert guards dict keys to GuardId if they are strings."""
    if raw_guards is None:
        return {}
    resolved = {}
    for k, v in raw_guards.items():
        key = GuardId(k) if isinstance(k, str) else k
        resolved[key] = v
    return resolved


def build_engine(
    *,
    guarded_rules=(),
    guards=None,
    actions=None,
    initial_state=NavigationStateId.MODE,
    current_state=None,
    exit_effects=None,
    entry_effects=None,
):
    from apps.access8graph.navigation.engine import TransitionEngine

    state = current_state or initial_state
    rules = list(_help_edges())

    for i, guard_name in enumerate(guarded_rules):
        rules.append(
            TransitionRule(
                source=state,
                command=NavigationCommand.CONFIRM,
                target=state,
                action_id=ActionId(f"action_{i}"),
                guard_id=GuardId(guard_name),
            )
        )

    all_rules = tuple(rules)
    all_action_ids = {r.action_id for r in all_rules}
    all_guard_ids = {r.guard_id for r in all_rules if r.guard_id is not None}

    from apps.access8graph.navigation.table import validate_transition_table

    table = validate_transition_table(
        rules=all_rules,
        initial_state=initial_state,
        action_ids=all_action_ids,
        guard_ids=all_guard_ids,
    )

    if actions is None:
        actions = {}

    resolved_actions = {}
    for action_id in table.action_ids:
        if action_id in actions:
            resolved_actions[action_id] = actions[action_id]
        else:
            resolved_actions[action_id] = _noop_result

    context = NavigationContext(current_state=state)
    snapshot_factory = NavigationSnapshotFactory()

    return TransitionEngine(
        table=table,
        guards=_resolve_guards(guards),
        actions=resolved_actions,
        snapshot_factory=snapshot_factory,
        context=context,
        exit_effects=exit_effects,
        entry_effects=entry_effects,
    )


# ---------------------------------------------------------------------------
# Step 1: Rule selection and shared-snapshot tests
# ---------------------------------------------------------------------------


def test_all_candidate_guards_receive_the_same_snapshot():
    seen = []

    def first(snapshot):
        seen.append(snapshot)
        return True

    def second(snapshot):
        seen.append(snapshot)
        return False

    engine = build_engine(
        guarded_rules=("first", "second"),
        guards={"first": first, "second": second},
    )

    engine.dispatch(NavigationCommand.CONFIRM)

    assert len(seen) == 2
    assert seen[0] is seen[1]


def test_zero_matching_guards_returns_rejected():
    def never(snapshot):
        return False

    engine = build_engine(
        guarded_rules=("never",),
        guards={"never": never},
    )

    result = engine.dispatch(NavigationCommand.CONFIRM)

    assert result.outcome == "rejected"
    assert result.source == result.target


def test_two_matching_guards_raises_ambiguous_error():
    from apps.access8graph.navigation.engine import AmbiguousTransitionError

    def always(snapshot):
        return True

    engine = build_engine(
        guarded_rules=("a", "b"),
        guards={"a": always, "b": always},
    )

    with pytest.raises(AmbiguousTransitionError):
        engine.dispatch(NavigationCommand.CONFIRM)


def test_action_rejection_does_not_commit_target():
    def always(snapshot):
        return True

    def reject_action(snapshot, context):
        return ActionResult.rejected()

    engine = build_engine(
        guarded_rules=("always",),
        guards={"always": always},
        actions={ActionId("action_0"): reject_action},
    )

    old_state = engine.context.current_state
    result = engine.dispatch(NavigationCommand.CONFIRM)

    assert result.outcome == "rejected"
    assert engine.context.current_state == old_state


def test_action_success_commits_target_after_action():
    def always(snapshot):
        return True

    target = NavigationStateId.STATIONS

    rules = (
        TransitionRule(
            source=NavigationStateId.MODE,
            command=NavigationCommand.CONFIRM,
            target=target,
            action_id=ActionId("action_0"),
            guard_id=GuardId("always"),
        ),
    )

    engine = _build_engine_with_rules(
        rules=rules,
        guards={"always": always},
        current_state=NavigationStateId.MODE,
    )

    result = engine.dispatch(NavigationCommand.CONFIRM)

    assert result.outcome == "transitioned"
    assert engine.context.current_state == target


def test_action_exception_does_not_commit_target():
    def always(snapshot):
        return True

    def boom(snapshot, context):
        raise RuntimeError("boom")

    target = NavigationStateId.STATIONS

    rules = (
        TransitionRule(
            source=NavigationStateId.MODE,
            command=NavigationCommand.CONFIRM,
            target=target,
            action_id=ActionId("action_0"),
            guard_id=GuardId("always"),
        ),
    )

    engine = _build_engine_with_rules(
        rules=rules,
        guards={"always": always},
        actions={ActionId("action_0"): boom},
        current_state=NavigationStateId.MODE,
    )

    with pytest.raises(RuntimeError, match="boom"):
        engine.dispatch(NavigationCommand.CONFIRM)

    assert engine.context.current_state == NavigationStateId.MODE


def test_list_order_does_not_select_winning_guard():
    from apps.access8graph.navigation.engine import AmbiguousTransitionError

    def always(snapshot):
        return True

    engine = build_engine(
        guarded_rules=("a", "b"),
        guards={"a": always, "b": always},
    )

    with pytest.raises(AmbiguousTransitionError):
        engine.dispatch(NavigationCommand.CONFIRM)


# ---------------------------------------------------------------------------
# Step 4: AUTO tests
# ---------------------------------------------------------------------------


def test_two_step_auto_chain_presents_one_macrostep_result():
    def guard_true(snapshot):
        return True

    def goto_stations(snapshot, context):
        return ActionResult.accepted_with()

    def goto_lines(snapshot, context):
        return ActionResult.accepted_with()

    rules = (
        TransitionRule(
            source=NavigationStateId.MODE,
            command=NavigationCommand.CONFIRM,
            target=NavigationStateId.STATIONS,
            action_id=ActionId("a1"),
            guard_id=GuardId("g1"),
        ),
        TransitionRule(
            source=NavigationStateId.STATIONS,
            command=NavigationCommand.AUTO,
            target=NavigationStateId.LINES,
            action_id=ActionId("a2"),
            guard_id=GuardId("g1"),
        ),
    )

    engine = _build_engine_with_rules(
        rules=rules,
        guards={"g1": guard_true},
        actions={ActionId("a1"): goto_stations, ActionId("a2"): goto_lines},
        current_state=NavigationStateId.MODE,
    )

    result = engine.dispatch(NavigationCommand.CONFIRM)

    assert result.outcome == "transitioned"
    assert result.source == NavigationStateId.MODE
    assert result.target == NavigationStateId.LINES
    assert engine.context.current_state == NavigationStateId.LINES


def test_new_snapshot_built_after_each_accepted_transition():
    snapshots = []

    class RecordingFactory(NavigationSnapshotFactory):
        @staticmethod
        def create(context, **kwargs):
            snapshots.append(context.current_state)
            return NavigationSnapshotFactory.create(context, **kwargs)

    def guard_true(snapshot):
        return True

    rules = (
        TransitionRule(
            source=NavigationStateId.MODE,
            command=NavigationCommand.CONFIRM,
            target=NavigationStateId.STATIONS,
            action_id=ActionId("a1"),
            guard_id=GuardId("g1"),
        ),
        TransitionRule(
            source=NavigationStateId.STATIONS,
            command=NavigationCommand.AUTO,
            target=NavigationStateId.LINES,
            action_id=ActionId("a2"),
            guard_id=GuardId("g1"),
        ),
    )

    engine = _build_engine_with_rules(
        rules=rules,
        guards={"g1": guard_true},
        snapshot_factory=RecordingFactory(),
        current_state=NavigationStateId.MODE,
    )

    engine.dispatch(NavigationCommand.CONFIRM)

    assert len(snapshots) >= 2
    assert snapshots[0] == NavigationStateId.MODE
    assert snapshots[1] == NavigationStateId.STATIONS


def test_repeated_state_rule_raises_cycle_error():
    from apps.access8graph.navigation.engine import AutomaticTransitionCycleError

    def guard_true(snapshot):
        return True

    rules = (
        TransitionRule(
            source=NavigationStateId.MODE,
            command=NavigationCommand.CONFIRM,
            target=NavigationStateId.STATIONS,
            action_id=ActionId("a1"),
            guard_id=GuardId("g1"),
        ),
        TransitionRule(
            source=NavigationStateId.STATIONS,
            command=NavigationCommand.AUTO,
            target=NavigationStateId.MODE,
            action_id=ActionId("a2"),
            guard_id=GuardId("g1"),
        ),
        TransitionRule(
            source=NavigationStateId.MODE,
            command=NavigationCommand.AUTO,
            target=NavigationStateId.STATIONS,
            action_id=ActionId("a3"),
            guard_id=GuardId("g1"),
        ),
    )

    engine = _build_engine_with_rules(
        rules=rules,
        guards={"g1": guard_true},
        current_state=NavigationStateId.MODE,
    )

    with pytest.raises(AutomaticTransitionCycleError):
        engine.dispatch(NavigationCommand.CONFIRM)


def test_33_automatic_steps_raises_cycle_error():
    from apps.access8graph.navigation.engine import AutomaticTransitionCycleError

    S1 = NavigationStateId.MODE
    S2 = NavigationStateId.STATIONS

    step_counter = [0]

    def make_guard(n):
        def guard(snapshot):
            return step_counter[0] == n
        return guard

    def counting_action(snapshot, context):
        step_counter[0] += 1
        return ActionResult.accepted_with()

    # Initial external command rule
    rules = [
        TransitionRule(
            source=S1,
            command=NavigationCommand.CONFIRM,
            target=S2,
            action_id=ActionId("init"),
            guard_id=GuardId("g_init"),
        )
    ]

    guards = {"g_init": lambda s: True}
    actions = {ActionId("init"): counting_action}

    # 33 AUTO rules, alternating between S1 and S2
    for i in range(33):
        src = S1 if i % 2 == 0 else S2
        tgt = S2 if i % 2 == 0 else S1
        rules.append(
            TransitionRule(
                source=src,
                command=NavigationCommand.AUTO,
                target=tgt,
                action_id=ActionId(f"a_{i}"),
                guard_id=GuardId(f"g_{i}"),
            )
        )
        guards[f"g_{i}"] = make_guard(i)
        actions[ActionId(f"a_{i}")] = counting_action

    engine = _build_engine_with_rules(
        rules=tuple(rules),
        guards=guards,
        actions=actions,
        current_state=S1,
    )

    with pytest.raises(AutomaticTransitionCycleError):
        engine.dispatch(NavigationCommand.CONFIRM)


def test_entry_handler_cannot_change_state():
    def guard_true(snapshot):
        return True

    def entry_effect(snapshot, context):
        context.current_state = NavigationStateId.HELP
        return PresentationEffects()

    target = NavigationStateId.STATIONS

    rules = (
        TransitionRule(
            source=NavigationStateId.MODE,
            command=NavigationCommand.CONFIRM,
            target=target,
            action_id=ActionId("a1"),
            guard_id=GuardId("g1"),
        ),
    )

    engine = _build_engine_with_rules(
        rules=rules,
        guards={"g1": guard_true},
        entry_effects={target: entry_effect},
        current_state=NavigationStateId.MODE,
    )

    engine.dispatch(NavigationCommand.CONFIRM)

    assert engine.context.current_state == target


# ---------------------------------------------------------------------------
# helper for building engine with custom rules
# ---------------------------------------------------------------------------


def _build_engine_with_rules(
    *,
    rules,
    guards=None,
    actions=None,
    snapshot_factory=None,
    exit_effects=None,
    entry_effects=None,
    initial_state=NavigationStateId.MODE,
    current_state=None,
    action_ids=None,
    guard_ids=None,
):
    from apps.access8graph.navigation.engine import TransitionEngine
    from apps.access8graph.navigation.table import validate_transition_table

    state = current_state or initial_state
    all_rules = tuple(rules) + _help_edges()

    if action_ids is None:
        action_ids = {r.action_id for r in all_rules}
    if guard_ids is None:
        guard_ids = {r.guard_id for r in all_rules if r.guard_id is not None}

    table = validate_transition_table(
        rules=all_rules,
        initial_state=initial_state,
        action_ids=action_ids,
        guard_ids=guard_ids,
    )

    if actions is None:
        actions = {}

    resolved_actions = {}
    for action_id in table.action_ids:
        if action_id in actions:
            resolved_actions[action_id] = actions[action_id]
        else:
            resolved_actions[action_id] = _noop_result

    context = NavigationContext(current_state=state)
    factory = snapshot_factory or NavigationSnapshotFactory()

    return TransitionEngine(
        table=table,
        guards=_resolve_guards(guards),
        actions=resolved_actions,
        snapshot_factory=factory,
        context=context,
        exit_effects=exit_effects,
        entry_effects=entry_effects,
    )
