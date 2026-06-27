from dataclasses import FrozenInstanceError

import pytest

from apps.access8graph.navigation.model import NavigationContext, NavigationStateId
from apps.access8graph.navigation.snapshot import (
    NavigationSnapshot,
    NavigationSnapshotFactory,
)


def test_navigation_snapshot_is_immutable():
    snapshot = NavigationSnapshot(
        state=NavigationStateId.MODE,
        return_state=None,
        selected_id="direction",
        option_count=3,
        selected_mode=None,
        has_line=False,
        has_station=False,
        has_source=False,
        has_destination=False,
        neighbor_count=0,
        transfer_count=0,
        run_active=False,
    )

    with pytest.raises(FrozenInstanceError):
        snapshot.option_count = 1


def test_factory_creates_valid_snapshot():
    context = NavigationContext(
        current_state=NavigationStateId.STATIONS,
        return_state=NavigationStateId.MODE,
        selected_mode="direction",
    )

    snapshot = NavigationSnapshotFactory.create(
        context,
        selected_id="station_42",
        option_count=5,
        has_line=True,
        has_station=True,
        has_source=True,
        has_destination=False,
        neighbor_count=2,
        transfer_count=1,
        run_active=False,
    )

    assert snapshot.state == NavigationStateId.STATIONS
    assert snapshot.return_state == NavigationStateId.MODE
    assert snapshot.selected_id == "station_42"
    assert snapshot.option_count == 5
    assert snapshot.selected_mode == "direction"
    assert snapshot.has_line is True
    assert snapshot.has_station is True
    assert snapshot.has_source is True
    assert snapshot.has_destination is False
    assert snapshot.neighbor_count == 2
    assert snapshot.transfer_count == 1
    assert snapshot.run_active is False
