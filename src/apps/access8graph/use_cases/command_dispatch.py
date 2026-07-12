from typing import Protocol

from apps.access8graph.navigation.model import NavigationCommand, TransitionResult
from accessibility_toolkit.input import AppKeyEventResult


class NavigationFlow(Protocol):
    def enter(self, command: NavigationCommand) -> TransitionResult: ...


class Access8GraphCommandDispatcher:
    def __init__(self, *, navigation, translator=None) -> None:
        self._translator = translator
        self._navigation = navigation

    def handle_key_event(self, event) -> AppKeyEventResult:
        if self._translator is None:
            return AppKeyEventResult.UNHANDLED
        command = self._translator.translate(event)
        if command is None:
            return AppKeyEventResult.HANDLED_STOP
        return self.dispatch(command)

    def dispatch(self, command: NavigationCommand) -> AppKeyEventResult:
        flow = self._navigation.current_flow
        if flow is None:
            return AppKeyEventResult.UNHANDLED
        flow.enter(command)
        return AppKeyEventResult.HANDLED_STOP
