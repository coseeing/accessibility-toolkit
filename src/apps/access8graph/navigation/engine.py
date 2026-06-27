from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from apps.access8graph.navigation.model import (
    ActionId,
    ActionResult,
    GuardId,
    NavigationCommand,
    NavigationContext,
    NavigationStateId,
    PresentationEffects,
    TransitionOutcome,
    TransitionResult,
    TransitionRule,
)

if TYPE_CHECKING:
    from apps.access8graph.navigation.snapshot import NavigationSnapshot
    from apps.access8graph.navigation.table import TransitionTable


class AmbiguousTransitionError(Exception):
    pass


class AutomaticTransitionCycleError(Exception):
    pass


class TransitionEngine:
    MAX_AUTO_STEPS = 32  # up to 32 automatic transitions per macrostep; the 33rd raises

    def __init__(
        self,
        *,
        table: TransitionTable,
        guards: dict[GuardId, Callable[[NavigationSnapshot], bool]],
        actions: dict[ActionId, Callable[..., ActionResult]],
        snapshot_factory: Callable[[NavigationContext], NavigationSnapshot],
        context: NavigationContext,
        exit_effects: dict[NavigationStateId, Callable[..., PresentationEffects]] | None = None,
        entry_effects: dict[NavigationStateId, Callable[..., PresentationEffects]] | None = None,
    ):
        self._table = table
        self._guards = guards
        self._actions = actions
        self._snapshot_factory = snapshot_factory
        self.context = context
        self._exit_effects = exit_effects or {}
        self._entry_effects = entry_effects or {}

    def dispatch(self, command: NavigationCommand) -> TransitionResult:
        snapshot = self._build_snapshot()
        return self._dispatch_external(command, snapshot)

    def start(self) -> TransitionResult:
        source = self.context.current_state
        effects = PresentationEffects()
        entry_handler = self._entry_effects.get(source)
        if entry_handler is not None:
            effects = entry_handler(self._build_snapshot(), self.context)
        self.context.hint_pending = True
        effects = _merge_effects(effects, _current_view_effects(self.context))
        return TransitionResult.transitioned(
            source=source,
            target=source,
            effects=effects,
        )

    # ------------------------------------------------------------------
    # external command dispatch (non-AUTO)
    # ------------------------------------------------------------------

    def _dispatch_external(
        self, command: NavigationCommand, snapshot: NavigationSnapshot
    ) -> TransitionResult:
        rules = list(self._table.lookup(self.context.current_state, command))

        if not rules:
            return TransitionResult.rejected(
                source=self.context.current_state,
                effects=_current_view_effects(self.context),
            )

        matching = self._evaluate_guards(rules, snapshot)

        if len(matching) == 0:
            return TransitionResult.rejected(
                source=self.context.current_state,
                effects=_current_view_effects(self.context),
            )
        if len(matching) > 1:
            raise AmbiguousTransitionError(
                f"multiple rules match {self.context.current_state.value} + {command.value}"
            )

        rule = matching[0]
        return self._apply_rule(rule, snapshot, is_auto=False)

    # ------------------------------------------------------------------
    # AUTO loop
    # ------------------------------------------------------------------

    def _run_auto_loop(
        self,
        initial_source: NavigationStateId,
        initial_effects: PresentationEffects,
        visited: set[tuple[NavigationStateId, TransitionRule]],
    ) -> TransitionResult:
        effects = initial_effects
        current_source = initial_source
        steps = 0

        while True:
            snapshot = self._build_snapshot()
            rules = list(
                self._table.lookup(self.context.current_state, NavigationCommand.AUTO)
            )

            if not rules:
                break

            matching = self._evaluate_guards(rules, snapshot)

            if len(matching) == 0:
                break
            if len(matching) > 1:
                raise AmbiguousTransitionError(
                    f"multiple AUTO rules match state {self.context.current_state.value}"
                )

            if steps >= self.MAX_AUTO_STEPS:
                raise AutomaticTransitionCycleError(
                    f"exceeded maximum AUTO steps ({self.MAX_AUTO_STEPS})"
                )

            rule = matching[0]

            state_rule_key = (self.context.current_state, rule)
            if state_rule_key in visited:
                raise AutomaticTransitionCycleError(
                    f"AUTO cycle detected at state {self.context.current_state.value}"
                )
            visited.add(state_rule_key)

            result = self._apply_rule(rule, snapshot, is_auto=True)
            effects = _merge_effects(effects, result.effects)
            steps += 1

        return TransitionResult.transitioned(
            source=current_source,
            target=self.context.current_state,
            effects=effects,
        )

    # ------------------------------------------------------------------
    # rule application (shared by external and AUTO paths)
    # ------------------------------------------------------------------

    def _apply_rule(
        self,
        rule: TransitionRule,
        snapshot: NavigationSnapshot,
        *,
        is_auto: bool,
    ) -> TransitionResult:
        action = self._actions[rule.action_id]
        action_result = action(snapshot, self.context)

        if not action_result.accepted:
            effects = _merge_effects(
                action_result.effects, _current_view_effects(self.context)
            )
            return TransitionResult.rejected(
                source=self.context.current_state,
                effects=effects,
            )

        effects = action_result.effects
        old_state = self.context.current_state
        same_target = (rule.source == rule.target)

        if same_target:
            effects = _merge_effects(effects, _current_view_effects(self.context))
            return TransitionResult.handled(
                source=old_state,
                effects=effects,
            )

        # run source exit effects
        exit_handler = self._exit_effects.get(rule.source)
        if exit_handler is not None:
            exit_effects = exit_handler(snapshot, self.context)
            effects = _merge_effects(effects, exit_effects)

        # commit target
        self.context.current_state = rule.target
        self.context.hint_pending = True

        # build fresh snapshot for entry handler
        fresh_snapshot = self._build_snapshot()

        # run target entry effects
        entry_handler = self._entry_effects.get(rule.target)
        if entry_handler is not None:
            entry_effects = entry_handler(fresh_snapshot, self.context)
            effects = _merge_effects(effects, entry_effects)

        # re-affirm state after entry handler (it must not change state)
        self.context.current_state = rule.target

        # add view display and hint (if first time) from the view model
        effects = _merge_effects(effects, _current_view_effects(self.context))

        if not is_auto:
            return self._run_auto_loop(old_state, effects, visited=set())

        return TransitionResult.transitioned(
            source=old_state,
            target=rule.target,
            effects=effects,
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _build_snapshot(self) -> NavigationSnapshot:
        return self._snapshot_factory.create(self.context)

    def _evaluate_guards(
        self,
        rules: list[TransitionRule],
        snapshot: NavigationSnapshot,
    ) -> list[TransitionRule]:
        matching: list[TransitionRule] = []
        for rule in rules:
            if rule.guard_id is None:
                matching.append(rule)
            else:
                guard = self._guards[rule.guard_id]
                if guard(snapshot):
                    matching.append(rule)
        return matching


# ------------------------------------------------------------------
# effects merging
# ------------------------------------------------------------------


def _merge_effects(
    a: PresentationEffects, b: PresentationEffects
) -> PresentationEffects:
    return PresentationEffects(
        close_messages=a.close_messages + b.close_messages,
        open_messages=a.open_messages + b.open_messages,
        hints=a.hints + b.hints,
        view_items=a.view_items + b.view_items,
    )


def _current_view_effects(context: NavigationContext) -> PresentationEffects:
    vm = context.view_model
    if vm is None:
        return PresentationEffects()
    hint = None
    if context.hint_pending:
        hint = getattr(vm, "hint", None)
        if hint:
            context.hint_pending = False
    display = getattr(vm, "display", ())
    items = tuple(item for item in display if item)
    return PresentationEffects(
        hints=(hint,) if hint else (),
        view_items=items,
    )
