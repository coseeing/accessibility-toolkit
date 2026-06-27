from __future__ import annotations

from apps.access8graph.navigation.actions import (
    common,
    mode_selection,
    direction,
    undirected,
    route_plan,
    transfer,
)


class DuplicateActionError(Exception):
    pass


class DuplicateGuardError(Exception):
    pass


def build_action_registry(
    direction_nav=None, undirection_nav=None
) -> dict[str, callable]:
    from apps.access8graph.navigation.model import ActionId

    actions: dict[ActionId, callable] = {}
    actions.update(common.build_base_actions())

    for module in [mode_selection, direction, undirected, route_plan, transfer]:
        module_actions = module.build_actions(direction_nav, undirection_nav)
        for key, val in module_actions.items():
            if key in actions and actions[key] is not val:
                raise DuplicateActionError(
                    f"Duplicate action ID '{key.value}' from multiple family modules"
                )
            actions[key] = val

    return actions


build_guard_registry = common.build_guard_registry
build_entry_effects = common.build_entry_effects
build_exit_effects = common.build_exit_effects
build_snapshot_factory = common.build_snapshot_factory

from apps.access8graph.navigation.actions.common import (
    ALL_ACTION_IDS,
    ALL_GUARD_IDS,
    ListViewModel,
    RunViewModel,
)
