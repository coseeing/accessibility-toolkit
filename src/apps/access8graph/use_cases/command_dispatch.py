from typing import Protocol

from apps.access8graph.navigation.model import NavigationCommand, TransitionResult
from accessibility_toolkit.input import AppKeyEventResult


class NavigationFlow(Protocol):
    def enter(self, command: NavigationCommand) -> TransitionResult: ...


class Access8GraphCommandDispatcher:
    def __init__(self, *, translator, navigation) -> None:
        self._translator = translator
        self._navigation = navigation

    def handle_key_event(self, event) -> AppKeyEventResult:
        command = self._translator.translate(event)
        if command is None:
            return AppKeyEventResult.HANDLED_STOP
        flow = self._navigation.current_flow
        if flow is None:
            return AppKeyEventResult.UNHANDLED
        flow.enter(command)
        return AppKeyEventResult.HANDLED_STOP
