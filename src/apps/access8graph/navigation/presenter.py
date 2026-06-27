from __future__ import annotations

from typing import Protocol

from apps.access8graph.navigation.model import TransitionOutcome, TransitionResult


class OutputPort(Protocol):
    def speak(self, items: tuple[object, ...]) -> None: ...
    def cancel(self) -> None: ...
    def beep(self) -> None: ...


class FlowPresenter:
    def __init__(self, output: OutputPort):
        self._output = output

    def present(self, result: TransitionResult) -> None:
        if result.outcome == TransitionOutcome.UNHANDLED:
            return

        if result.outcome == TransitionOutcome.REJECTED:
            self._present_rejected(result)
        else:
            self._present_transitioned(result)

    def _present_rejected(self, result: TransitionResult) -> None:
        effects = result.effects
        self._output.beep()
        items = tuple(item for item in effects.view_items if item)
        if items:
            self._output.speak(items)

    def _present_transitioned(self, result: TransitionResult) -> None:
        effects = result.effects
        items = tuple(
            item
            for item in (
                effects.close_messages
                + effects.open_messages
                + effects.hints
                + effects.view_items
            )
            if item
        )
        if items:
            self._output.cancel()
            self._output.speak(items)
