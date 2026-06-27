from __future__ import annotations

from apps.access8graph.navigation.model import (
    ActionId,
    ActionResult,
    NavigationContext,
)

from apps.access8graph.navigation.actions.common import (
    A_HELP_CONFIRM,
    A_HELP_QUIT,
)


def _build_help_actions(direction_nav, undirection_nav):
    def help_confirm(snapshot, context: NavigationContext) -> ActionResult:
        selected = snapshot.selected_id
        if selected == "m":
            context.selected_mode = None
            return ActionResult.accepted_with()
        if selected == "v":
            return ActionResult.accepted_with()
        if selected == "s":
            direction_nav.station = None
            return ActionResult.accepted_with()
        if selected == "l":
            direction_nav.line = None
            return ActionResult.accepted_with()
        if selected == "e":
            direction_nav.source = direction_nav.current
            direction_nav.destination = None
            return ActionResult.accepted_with()
        return ActionResult.accepted_with()

    def help_quit(snapshot, context: NavigationContext) -> ActionResult:
        return ActionResult.accepted_with()

    return help_confirm, help_quit


def build_actions(direction_nav=None, undirection_nav=None) -> dict[ActionId, callable]:
    actions: dict[ActionId, callable] = {}

    if undirection_nav is not None and direction_nav is not None:
        hc, hq = _build_help_actions(direction_nav, undirection_nav)
        actions[A_HELP_CONFIRM] = hc
        actions[A_HELP_QUIT] = hq

    return actions
