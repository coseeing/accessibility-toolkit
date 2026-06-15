from pathlib import Path

from apps.access8graph.flow import MrtFlow
from apps.access8graph.graphml import (
    Graph,
    MrtDirectionNavigator,
    MrtModel,
    MrtUndirectionNavigator,
)


FIXTURE = Path("Access8Graph/tests/test.graphml")


class FakeOutput:
    def __init__(self) -> None:
        self.calls = []

    def cancel_speech(self) -> None:
        self.calls.append(("cancel", None))

    def speak(self, items) -> None:
        self.calls.append(("speak", tuple(items)))

    def beep_failure(self) -> None:
        self.calls.append(("beep", None))


def test_access8graph_mrt_flow_starts_from_fixture_and_accepts_menu_navigation() -> None:
    graph = Graph(path=str(FIXTURE))
    model = MrtModel(graph)
    output = FakeOutput()

    flow = MrtFlow(
        navigator={
            "direction": MrtDirectionNavigator(model),
            "undirection": MrtUndirectionNavigator(model),
        },
        output=output,
    )

    assert output.calls[0] == ("cancel", None)
    assert output.calls[1][0] == "speak"
    assert "方向探索" in output.calls[1][1]

    output.calls.clear()

    assert flow.enter({"key": "down", "repeat": 0, "pressing": 0}) is True

    assert output.calls[0] == ("cancel", None)
    assert output.calls[1][0] == "speak"
    assert "線性探索" in output.calls[1][1]
