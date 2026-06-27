from __future__ import annotations

from apps.access8graph.navigation.model import (
    NavigationCommand,
    NavigationContext,
    NavigationStateId,
    TransitionResult,
)
from apps.access8graph.navigation.engine import TransitionEngine
from apps.access8graph.navigation.presenter import FlowPresenter


class TransitionNavigationFlow:
    def __init__(self, *, engine: TransitionEngine, presenter: FlowPresenter):
        self._engine = engine
        self._presenter = presenter

    @property
    def context(self) -> NavigationContext:
        return self._engine.context

    def enter(self, command: NavigationCommand) -> TransitionResult:
        result = self._engine.dispatch(command)
        self._presenter.present(result)
        return result
