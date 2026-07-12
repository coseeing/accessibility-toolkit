from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from accessibility_toolkit.input.events import CapturedKeyEvent, KeyEvent
from accessibility_toolkit.input.hid import HID
from accessibility_toolkit.input.results import AppKeyEventResult


class Modifier(StrEnum):
    CONTROL = "control"
    SHIFT = "shift"
    ALT = "alt"
    META = "meta"


class KeyTrigger(StrEnum):
    KEY_DOWN = "key_down"
    KEY_UP = "key_up"
    LONG_PRESS = "long_press"


KeyHandler = Callable[[KeyEvent], AppKeyEventResult]
KeyEventInput = KeyEvent | CapturedKeyEvent
FallbackHandler = Callable[[KeyEventInput], AppKeyEventResult]


@dataclass(frozen=True, slots=True)
class KeyChord:
    usage: int
    modifiers: frozenset[Modifier] = frozenset()


@dataclass(frozen=True, slots=True)
class KeyBinding:
    chord: KeyChord
    trigger: KeyTrigger
    handler: KeyHandler
    duration_seconds: float | None = None

    def __post_init__(self) -> None:
        if self.trigger is KeyTrigger.LONG_PRESS:
            if self.duration_seconds is None or self.duration_seconds <= 0:
                raise ValueError("Long-press bindings require a positive duration_seconds")
        elif self.duration_seconds is not None:
            raise ValueError("Only long-press bindings accept duration_seconds")


class ScheduledCall(Protocol):
    def cancel(self) -> None: ...


class DelayedScheduler(Protocol):
    def schedule(
        self, delay_seconds: float, callback: Callable[[], None]
    ) -> ScheduledCall: ...


@dataclass(slots=True)
class _PendingLongPress:
    chord: KeyChord
    event: KeyEvent
    timer: ScheduledCall
    key_down_binding: KeyBinding | None
    long_press_binding: KeyBinding
    fired: bool = False


_MODIFIER_BY_USAGE = {
    HID.LEFT_CONTROL: Modifier.CONTROL,
    HID.RIGHT_CONTROL: Modifier.CONTROL,
    HID.LEFT_SHIFT: Modifier.SHIFT,
    HID.RIGHT_SHIFT: Modifier.SHIFT,
    HID.LEFT_ALT: Modifier.ALT,
    HID.RIGHT_ALT: Modifier.ALT,
    HID.LEFT_META: Modifier.META,
    HID.RIGHT_META: Modifier.META,
}


class KeyEventRouter:
    def __init__(
        self,
        *,
        bindings: tuple[KeyBinding, ...],
        fallback: FallbackHandler | None = None,
        delayed_scheduler: DelayedScheduler | None = None,
    ) -> None:
        self._bindings = self._index_bindings(bindings)
        self._fallback = fallback
        self._delayed_scheduler = delayed_scheduler
        self._pressed_modifier_usages: set[int] = set()
        self._pending_long_presses: dict[int, _PendingLongPress] = {}
        if any(binding.trigger is KeyTrigger.LONG_PRESS for binding in bindings):
            if delayed_scheduler is None:
                raise ValueError("Long-press bindings require a delayed_scheduler")

    def handle(self, event: KeyEventInput) -> AppKeyEventResult:
        original_event = event
        event = event.key_event if isinstance(event, CapturedKeyEvent) else event
        if event.usage_page != HID.KEYBOARD_PAGE:
            return self._handle_fallback(original_event)

        modifier = _MODIFIER_BY_USAGE.get(event.usage)
        if modifier is not None:
            self._update_modifier_state(event)
            if not event.pressed and modifier not in self._active_modifiers():
                self._cancel_long_presses_requiring(modifier)
            return self._handle_fallback(original_event)

        if event.pressed:
            return self._handle_key_down(event, original_event)
        return self._handle_key_up(event, original_event)

    def reset(self) -> None:
        for pending in self._pending_long_presses.values():
            pending.timer.cancel()
        self._pending_long_presses.clear()
        self._pressed_modifier_usages.clear()

    def _handle_key_down(
        self, event: KeyEvent, original_event: KeyEventInput
    ) -> AppKeyEventResult:
        chord = KeyChord(event.usage, self._active_modifiers())
        long_press_binding = self._bindings.get((chord, KeyTrigger.LONG_PRESS))
        key_down_binding = self._bindings.get((chord, KeyTrigger.KEY_DOWN))
        if long_press_binding is not None:
            if event.usage not in self._pending_long_presses:
                self._schedule_long_press(
                    chord, event, key_down_binding, long_press_binding
                )
            return AppKeyEventResult.HANDLED_STOP
        if key_down_binding is not None:
            return key_down_binding.handler(event)
        return self._handle_fallback(original_event)

    def _handle_key_up(
        self, event: KeyEvent, original_event: KeyEventInput
    ) -> AppKeyEventResult:
        pending = self._pending_long_presses.pop(event.usage, None)
        delayed_result: AppKeyEventResult | None = None
        if pending is not None:
            pending.timer.cancel()
            if not pending.fired and pending.key_down_binding is not None:
                delayed_result = pending.key_down_binding.handler(pending.event)

        chord = KeyChord(event.usage, self._active_modifiers())
        key_up_binding = self._bindings.get((chord, KeyTrigger.KEY_UP))
        if key_up_binding is not None:
            return key_up_binding.handler(event)
        if delayed_result is not None:
            return delayed_result
        return self._handle_fallback(original_event)

    def _schedule_long_press(
        self,
        chord: KeyChord,
        event: KeyEvent,
        key_down_binding: KeyBinding | None,
        long_press_binding: KeyBinding,
    ) -> None:
        assert self._delayed_scheduler is not None

        def fire() -> None:
            pending = self._pending_long_presses.get(event.usage)
            if pending is None or pending.chord != chord:
                return
            pending.fired = True
            long_press_binding.handler(event)

        timer = self._delayed_scheduler.schedule(
            long_press_binding.duration_seconds, fire
        )
        self._pending_long_presses[event.usage] = _PendingLongPress(
            chord=chord,
            event=event,
            timer=timer,
            key_down_binding=key_down_binding,
            long_press_binding=long_press_binding,
        )

    def _update_modifier_state(self, event: KeyEvent) -> None:
        if event.pressed:
            self._pressed_modifier_usages.add(event.usage)
        else:
            self._pressed_modifier_usages.discard(event.usage)

    def _active_modifiers(self) -> frozenset[Modifier]:
        return frozenset(
            _MODIFIER_BY_USAGE[usage] for usage in self._pressed_modifier_usages
        )

    def _cancel_long_presses_requiring(self, modifier: Modifier) -> None:
        for usage, pending in tuple(self._pending_long_presses.items()):
            if modifier in pending.chord.modifiers:
                pending.timer.cancel()
                del self._pending_long_presses[usage]

    def _handle_fallback(self, event: KeyEventInput) -> AppKeyEventResult:
        if self._fallback is None:
            return AppKeyEventResult.UNHANDLED
        return self._fallback(event)

    @staticmethod
    def _index_bindings(
        bindings: tuple[KeyBinding, ...],
    ) -> dict[tuple[KeyChord, KeyTrigger], KeyBinding]:
        indexed: dict[tuple[KeyChord, KeyTrigger], KeyBinding] = {}
        for binding in bindings:
            key = (binding.chord, binding.trigger)
            if key in indexed:
                raise ValueError(f"Duplicate key binding: {binding.chord!r} {binding.trigger}")
            indexed[key] = binding
        return indexed
