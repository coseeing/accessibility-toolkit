from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.access8graph.navigation.snapshot import NavigationSnapshot


class NavigationCommand(StrEnum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    CONFIRM = "confirm"
    HOME = "home"
    END = "end"
    SELECT_DIRECTION = "select_direction"
    SELECT_UNDIRECTED = "select_undirected"
    SELECT_PLAN = "select_plan"
    QUIT = "quit"
    OPEN_HELP = "open_help"
    OPEN_MODE = "open_mode"
    OPEN_BROWSER = "open_browser"
    SELECT_STATION = "select_station"
    SELECT_LINE = "select_line"
    SELECT_ENDPOINT = "select_endpoint"
    AUTO = "auto"


class NavigationStateId(StrEnum):
    MODE = "mode"
    STATIONS = "stations"
    LINES = "lines"
    DIRECTION_END_POINT = "direction_end_point"
    DIRECTION_RUN = "direction_run"
    UNDIRECTION_RUN = "undirection_run"
    PLAN_RUN = "plan_run"
    DIRECTION_TRANSFER = "direction_transfer"
    UNDIRECTION_TRANSFER = "undirection_transfer"
    EXPLORE_NEIGHBOR = "explore_neighbor"
    EXPLORE_SUB_LINE = "explore_sub_line"
    DIRECTION_STATIONS = "direction_stations"
    DIRECTION_LINES = "direction_lines"
    SOURCE_STATIONS = "source_stations"
    SOURCE_LINES = "source_lines"
    DESTINATION_STATIONS = "destination_stations"
    DESTINATION_LINES = "destination_lines"
    UNDIRECTION_STATIONS = "undirection_stations"
    UNDIRECTION_LINES = "undirection_lines"
    UNDIRECTION_SUB_LINES = "undirection_sub_lines"
    HELP = "help"


@dataclass(frozen=True, slots=True)
class ActionId:
    value: str


@dataclass(frozen=True, slots=True)
class GuardId:
    value: str


Guard = Callable[["NavigationSnapshot"], bool]


@dataclass(frozen=True, slots=True)
class TransitionRule:
    source: NavigationStateId
    command: NavigationCommand
    target: NavigationStateId
    action_id: ActionId
    guard_id: GuardId | None = None


class TransitionOutcome(StrEnum):
    TRANSITIONED = "transitioned"
    HANDLED = "handled"
    REJECTED = "rejected"
    UNHANDLED = "unhandled"


@dataclass(frozen=True, slots=True)
class PresentationEffects:
    close_messages: tuple[object, ...] = ()
    open_messages: tuple[object, ...] = ()
    hints: tuple[object, ...] = ()
    view_items: tuple[object, ...] = ()


@dataclass(frozen=True, slots=True)
class ActionResult:
    accepted: bool
    effects: PresentationEffects = field(default_factory=PresentationEffects)

    @classmethod
    def accepted_with(
        cls, effects: PresentationEffects | None = None
    ) -> "ActionResult":
        return cls(accepted=True, effects=effects or PresentationEffects())

    @classmethod
    def rejected(cls) -> "ActionResult":
        return cls(accepted=False)


@dataclass(frozen=True, slots=True)
class TransitionResult:
    outcome: TransitionOutcome
    source: NavigationStateId
    target: NavigationStateId
    effects: PresentationEffects
    auto_steps: tuple[
        tuple[NavigationStateId, ActionId, NavigationStateId], ...
    ] = ()

    @classmethod
    def transitioned(
        cls,
        *,
        source: NavigationStateId,
        target: NavigationStateId,
        effects: PresentationEffects,
        auto_steps: tuple[
            tuple[NavigationStateId, ActionId, NavigationStateId], ...
        ] = (),
    ) -> "TransitionResult":
        return cls(
            TransitionOutcome.TRANSITIONED,
            source,
            target,
            effects,
            auto_steps,
        )

    @classmethod
    def handled(
        cls,
        *,
        source: NavigationStateId,
        effects: PresentationEffects,
    ) -> "TransitionResult":
        return cls(TransitionOutcome.HANDLED, source, source, effects)

    @classmethod
    def rejected(
        cls,
        *,
        source: NavigationStateId,
        effects: PresentationEffects | None = None,
    ) -> "TransitionResult":
        return cls(
            TransitionOutcome.REJECTED,
            source,
            source,
            effects or PresentationEffects(),
        )


@dataclass(slots=True)
class NavigationContext:
    current_state: NavigationStateId
    return_state: NavigationStateId | None = None
    view_model: Any = None
    selected_mode: str | None = None
    pending_effects: PresentationEffects = field(default_factory=PresentationEffects)
    hint_pending: bool = True
