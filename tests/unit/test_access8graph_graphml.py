from pathlib import Path

from apps.access8graph.graphml import (
    Graph,
    MrtDirectionNavigator,
    MrtModel,
    MrtUndirectionNavigator,
)


FIXTURE = Path("Access8Graph/tests/test.graphml")


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
