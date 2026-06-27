from __future__ import annotations

from typing import TYPE_CHECKING

from apps.access8graph.navigation.model import (
    NavigationCommand,
    NavigationContext,
    NavigationStateId,
    TransitionOutcome,
    TransitionResult,
)

if TYPE_CHECKING:
    from apps.access8graph.navigation.engine import TransitionEngine
    from apps.access8graph.navigation.presenter import FlowPresenter


_COMMAND_MAP: dict[str, NavigationCommand] = {
    "up": NavigationCommand.UP,
    "down": NavigationCommand.DOWN,
    "left": NavigationCommand.LEFT,
    "right": NavigationCommand.RIGHT,
    "enter": NavigationCommand.CONFIRM,
    "home": NavigationCommand.HOME,
    "end": NavigationCommand.END,
    "d": NavigationCommand.SELECT_DIRECTION,
    "u": NavigationCommand.SELECT_UNDIRECTED,
    "p": NavigationCommand.SELECT_PLAN,
    "q": NavigationCommand.QUIT,
    "h": NavigationCommand.OPEN_HELP,
    "m": NavigationCommand.OPEN_MODE,
    "v": NavigationCommand.OPEN_BROWSER,
    "s": NavigationCommand.SELECT_STATION,
    "l": NavigationCommand.SELECT_LINE,
    "e": NavigationCommand.SELECT_ENDPOINT,
}


class TransitionNavigationFlow:
    def __init__(self, engine: TransitionEngine, presenter: FlowPresenter):
        self._engine = engine
        self._presenter = presenter

    @property
    def engine(self) -> TransitionEngine:
        return self._engine

    @property
    def context(self) -> NavigationContext:
        return self._engine.context

    def enter(self, command: str | NavigationCommand) -> bool:
        if isinstance(command, NavigationCommand):
            nav_command = command
        elif isinstance(command, str):
            nav_command = _COMMAND_MAP.get(command)
            if nav_command is None:
                nav_command = NavigationCommand.QUIT
        else:
            return False

        result = self._engine.dispatch(nav_command)
        self._presenter.present(result)

        return result.outcome != TransitionOutcome.REJECTED

    @classmethod
    def build(
        cls,
        *,
        engine: TransitionEngine,
        presenter: FlowPresenter,
    ) -> TransitionNavigationFlow:
        return cls(engine=engine, presenter=presenter)
