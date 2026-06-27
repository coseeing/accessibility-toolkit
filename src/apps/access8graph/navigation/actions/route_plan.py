from __future__ import annotations

from apps.access8graph.navigation.model import (
    ActionId,
    ActionResult,
    NavigationContext,
)

from apps.access8graph.navigation.actions.common import (
    A_PLAN_LEFT,
    A_PLAN_RIGHT,
)


def _build_plan_run_actions(direction_nav):
    def plan_left(snapshot, context: NavigationContext) -> ActionResult:
        pointer = getattr(direction_nav, "previous", None)
        if pointer:
            direction_nav.current = pointer
            return ActionResult.accepted_with()
        return ActionResult.rejected()

    def plan_right(snapshot, context: NavigationContext) -> ActionResult:
        pointer = getattr(direction_nav, "next", None)
        if pointer:
            direction_nav.current = pointer
            return ActionResult.accepted_with()
        return ActionResult.rejected()

    return plan_left, plan_right


def build_actions(direction_nav=None, undirection_nav=None) -> dict[ActionId, callable]:
    actions: dict[ActionId, callable] = {}

    if direction_nav is not None:
        pl, pr = _build_plan_run_actions(direction_nav)
        actions[A_PLAN_LEFT] = pl
        actions[A_PLAN_RIGHT] = pr

    return actions
