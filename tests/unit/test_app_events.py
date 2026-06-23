from apps.access8graph.events import GraphNavigationChanged
from apps.key_echo.events import EchoStateChanged
from apps.nvda_remote.events import (
    RemoteConnectionChanged,
    RemoteControlChanged,
    RemoteMessageReceived,
    RemoteTransportDisconnected,
)


def test_key_echo_events_use_value_equality() -> None:
    assert EchoStateChanged(True) == EchoStateChanged(True)


def test_access8graph_events_use_value_equality() -> None:
    assert GraphNavigationChanged(False) == GraphNavigationChanged(False)


def test_nvda_remote_events_use_value_equality() -> None:
    assert RemoteConnectionChanged("connected") == RemoteConnectionChanged("connected")
    assert RemoteControlChanged("controlling") == RemoteControlChanged("controlling")
    assert RemoteTransportDisconnected() == RemoteTransportDisconnected(reason=None)
    assert RemoteTransportDisconnected("closed") == RemoteTransportDisconnected("closed")
    assert RemoteMessageReceived("motd", {"message": "hi"}) == RemoteMessageReceived(
        "motd", {"message": "hi"}
    )
