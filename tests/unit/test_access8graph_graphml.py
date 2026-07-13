from pathlib import Path

from apps.access8graph.graphml import (
    Graph,
    MrtDirectionNavigator,
    MrtModel,
    MrtUndirectionNavigator,
)


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "access8graph" / "test.graphml"


class _ReverseIterSet(set):
    def __iter__(self):
        return iter(sorted(set.copy(self), reverse=True))


class _UnorderedSubLineModel:
    def get_node_from_station_id_line_id(self, station_id, line_id):
        return _ReverseIterSet({"node-b", "node-a"})

    def get_sub_line_from_node_id(self, node_id):
        assert node_id == "node-a"
        return _ReverseIterSet(
            {
                ("node-a", "node-z"),
                ("node-z", "node-a"),
            }
        )

    def get_node_info_using_node_id(self, node_id):
        names = {"node-a": "松江南京", "node-z": "松山"}
        return ("", names[node_id], "松山新店線")


def test_access8graph_graphml_core_imports_without_nvda_modules() -> None:
    assert Graph is not None
    assert MrtModel is not None
    assert MrtDirectionNavigator is not None
    assert MrtUndirectionNavigator is not None


def test_access8graph_graphml_fixture_builds_mrt_model() -> None:
    graph = Graph(path=str(FIXTURE))
    model = MrtModel(graph)

    assert model.get_all_stations()
    assert model.get_all_lines()


def test_access8graph_navigators_expose_station_and_line_displays() -> None:
    graph = Graph(path=str(FIXTURE))
    model = MrtModel(graph)

    direction = MrtDirectionNavigator(model)
    undirection = MrtUndirectionNavigator(model)

    assert direction.stations_display
    assert direction.lines_display
    assert undirection.stations_display
    assert undirection.lines_display


def test_sub_line_display_has_deterministic_user_visible_order() -> None:
    navigator = MrtUndirectionNavigator(_UnorderedSubLineModel())
    navigator.station = "station"
    navigator.line = 2

    assert navigator.sub_lines_display == [
        {
            "id": ("node-z", "node-a"),
            "label": "松山往松江南京",
        },
        {
            "id": ("node-a", "node-z"),
            "label": "松江南京往松山",
        },
    ]
