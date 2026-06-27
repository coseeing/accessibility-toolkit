from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from apps.access8graph.navigation.model import NavigationStateId

if TYPE_CHECKING:
    from apps.access8graph.navigation.model import NavigationContext


@dataclass(frozen=True, slots=True)
class NavigationSnapshot:
    state: NavigationStateId
    return_state: NavigationStateId | None
    selected_id: str | None
    option_count: int
    selected_mode: str | None
    has_line: bool
    has_station: bool
    has_source: bool
    has_destination: bool
    neighbor_count: int
    transfer_count: int
    run_active: bool


class NavigationSnapshotFactory:
    @staticmethod
    def create(
        context: "NavigationContext",
        *,
        selected_id: str | None = None,
        option_count: int = 0,
        has_line: bool = False,
        has_station: bool = False,
        has_source: bool = False,
        has_destination: bool = False,
        neighbor_count: int = 0,
        transfer_count: int = 0,
        run_active: bool = False,
    ) -> NavigationSnapshot:
        return NavigationSnapshot(
            state=context.current_state,
            return_state=context.return_state,
            selected_id=selected_id,
            option_count=option_count,
            selected_mode=context.selected_mode,
            has_line=has_line,
            has_station=has_station,
            has_source=has_source,
            has_destination=has_destination,
            neighbor_count=neighbor_count,
            transfer_count=transfer_count,
            run_active=run_active,
        )
