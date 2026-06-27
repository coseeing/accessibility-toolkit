from __future__ import annotations

from apps.access8graph.navigation.model import (
    ActionId,
    ActionResult,
    NavigationContext,
    NavigationStateId,
    PresentationEffects,
)

from apps.access8graph.navigation.actions.common import (
    A_SELECT_DIRECTION,
    A_SELECT_UNDIRECTED,
    A_SELECT_PLAN,
    A_STATIONS_CONFIRM,
    A_LINES_CONFIRM,
    A_LIST_LINE_COMMAND,
    A_LIST_STATION_COMMAND,
    A_MODE_QUIT,
    A_STATIONS_QUIT,
    A_LINES_QUIT,
    A_RUN_MODE,
    A_RUN_BROWSER,
)


def _build_mode_select_actions(direction_nav, undirection_nav):
    def select_direction(snapshot, context: NavigationContext) -> ActionResult:
        context.return_state = NavigationStateId.DIRECTION_RUN
        direction_nav.line = None
        direction_nav.station = None
        context.selected_mode = "direction"
        return ActionResult.accepted_with()

    def select_undirected(snapshot, context: NavigationContext) -> ActionResult:
        undirection_nav.line = None
        undirection_nav.station = None
        context.selected_mode = "undirection"
        return ActionResult.accepted_with()

    def select_plan(snapshot, context: NavigationContext) -> ActionResult:
        context.return_state = NavigationStateId.PLAN_RUN
        direction_nav.line = None
        direction_nav.station = None
        context.selected_mode = "plan"
        return ActionResult.accepted_with()

    return select_direction, select_undirected, select_plan


def _build_stations_lines_confirm(direction_nav):
    def stations_confirm(snapshot, context: NavigationContext) -> ActionResult:
        if snapshot.selected_id is not None:
            direction_nav.station = snapshot.selected_id
        return ActionResult.accepted_with()

    def lines_confirm(snapshot, context: NavigationContext) -> ActionResult:
        if snapshot.selected_id is not None:
            direction_nav.line = snapshot.selected_id
        return ActionResult.accepted_with()

    return stations_confirm, lines_confirm


def _build_list_cross_commands(direction_nav):
    def list_line_command(snapshot, context: NavigationContext) -> ActionResult:
        direction_nav.line = None
        return ActionResult.accepted_with()

    def list_station_command(snapshot, context: NavigationContext) -> ActionResult:
        direction_nav.station = None
        return ActionResult.accepted_with()

    return list_line_command, list_station_command


def _build_quit_actions(direction_nav):
    from apps.access8graph.navigation.model import PresentationEffects

    def mode_quit(snapshot, context: NavigationContext) -> ActionResult:
        return ActionResult.accepted_with(
            PresentationEffects(
                close_messages=("功能選單關閉",),
            )
        )

    def stations_quit(snapshot, context: NavigationContext) -> ActionResult:
        direction_nav.line = None
        direction_nav.station = None
        return ActionResult.accepted_with(
            PresentationEffects(
                close_messages=("車站瀏覽選單關閉",),
            )
        )

    def lines_quit(snapshot, context: NavigationContext) -> ActionResult:
        direction_nav.line = None
        direction_nav.station = None
        return ActionResult.accepted_with(
            PresentationEffects(
                close_messages=("車站瀏覽選單關閉",),
            )
        )

    return mode_quit, stations_quit, lines_quit


def _build_run_common_actions(direction_nav, undirection_nav):
    def run_mode(snapshot, context: NavigationContext) -> ActionResult:
        return ActionResult.accepted_with()

    def run_browser(snapshot, context: NavigationContext) -> ActionResult:
        return ActionResult.accepted_with(
            PresentationEffects(open_messages=("車站瀏覽選單開啟",))
        )

    return run_mode, run_browser


def _build_undirection_cross_commands(undirection_nav):
    def list_line_command(snapshot, context: NavigationContext) -> ActionResult:
        undirection_nav.line = None
        return ActionResult.accepted_with()

    def list_station_command(snapshot, context: NavigationContext) -> ActionResult:
        undirection_nav.station = None
        return ActionResult.accepted_with()

    return list_line_command, list_station_command


def build_actions(direction_nav=None, undirection_nav=None) -> dict[ActionId, callable]:
    actions: dict[ActionId, callable] = {}

    if direction_nav is not None:
        sel_dir, sel_undir, sel_plan = _build_mode_select_actions(
            direction_nav, undirection_nav
        )
        actions[A_SELECT_DIRECTION] = sel_dir
        actions[A_SELECT_UNDIRECTED] = sel_undir
        actions[A_SELECT_PLAN] = sel_plan

        sc, lc = _build_stations_lines_confirm(direction_nav)
        actions[A_STATIONS_CONFIRM] = sc
        actions[A_LINES_CONFIRM] = lc

        lcl, lcs = _build_list_cross_commands(direction_nav)
        actions[A_LIST_LINE_COMMAND] = lcl
        actions[A_LIST_STATION_COMMAND] = lcs

        mq, sq, lq = _build_quit_actions(direction_nav)
        actions[A_MODE_QUIT] = mq
        actions[A_STATIONS_QUIT] = sq
        actions[A_LINES_QUIT] = lq

    if direction_nav is not None and undirection_nav is not None:
        rm, rb = _build_run_common_actions(direction_nav, undirection_nav)
        actions[A_RUN_MODE] = rm
        actions[A_RUN_BROWSER] = rb

    if undirection_nav is not None:
        ulcl, ulcs = _build_undirection_cross_commands(undirection_nav)
        actions[A_LIST_LINE_COMMAND] = ulcl
        actions[A_LIST_STATION_COMMAND] = ulcs

    return actions
