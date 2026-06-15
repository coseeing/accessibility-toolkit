from apps.access8graph.flow import MrtFlow


class FakeOutput:
    def __init__(self) -> None:
        self.calls = []

    def cancel_speech(self) -> None:
        self.calls.append(("cancel", None))

    def speak(self, items) -> None:
        self.calls.append(("speak", tuple(items)))

    def beep_failure(self) -> None:
        self.calls.append(("beep", None))


class FakeDirectionNavigator:
    def __init__(self) -> None:
        self.line = None
        self.station = None
        self.source = None
        self.destination = None
        self.current = None
        self.run = False
        self.lines_display = [
            {"id": "blue", "label": "板南線"},
            {"id": "red", "label": "淡水信義線"},
        ]
        self.stations_display = [
            {"id": "taipei", "label": "台北車站"},
            {"id": "ximen", "label": "西門"},
        ]
        self.end_points = [{"id": "nangang", "label": "南港展覽館"}]
        self.transfer_display = []
        self.current_display = {"id": "taipei", "label": "台北車站"}
        self.forward = []
        self.reverse = []


class FakeUndirectionNavigator:
    def __init__(self) -> None:
        self.line = None
        self.station = None
        self.current = None
        self.sub_line = None
        self.lines_display = [{"id": "blue", "label": "板南線"}]
        self.stations_display = [{"id": "taipei", "label": "台北車站"}]
        self.sub_lines_display = [{"id": ("taipei", "ximen"), "label": "台北車站往西門"}]
        self.transfer_display = []
        self.current_display = {"id": "taipei", "label": "台北車站"}
        self.previous = None
        self.next = None


def test_flow_startup_speaks_mode_menu() -> None:
    output = FakeOutput()

    MrtFlow(
        navigator={
            "direction": FakeDirectionNavigator(),
            "undirection": FakeUndirectionNavigator(),
        },
        output=output,
    )

    assert output.calls[0] == ("cancel", None)
    assert output.calls[1][0] == "speak"
    assert "功能選單開啟" in output.calls[1][1]
    assert "方向探索" in output.calls[1][1]


def test_flow_down_moves_mode_menu_selection() -> None:
    output = FakeOutput()
    flow = MrtFlow(
        navigator={
            "direction": FakeDirectionNavigator(),
            "undirection": FakeUndirectionNavigator(),
        },
        output=output,
    )
    output.calls.clear()

    assert flow.enter({"key": "down", "repeat": 0, "pressing": 0}) is True

    assert output.calls[0] == ("cancel", None)
    assert output.calls[1][0] == "speak"
    assert "線性探索" in output.calls[1][1]


def test_flow_unsupported_command_beeps_and_returns_false() -> None:
    output = FakeOutput()
    flow = MrtFlow(
        navigator={
            "direction": FakeDirectionNavigator(),
            "undirection": FakeUndirectionNavigator(),
        },
        output=output,
    )
    output.calls.clear()

    assert flow.enter({"key": "unknown", "repeat": 0, "pressing": 0}) is False

    assert ("beep", None) in output.calls
