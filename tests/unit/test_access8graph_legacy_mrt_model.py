from pathlib import Path
import xml.etree.ElementTree as ET

from apps.access8graph.graphml import model, mrt_model as mrtModel


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "access8graph" / "test.graphml"


def init_model():
    # testing data prepare
    mrt_model = mrtModel.MrtModel(model.Graph(path=str(FIXTURE), ET=ET))
    return mrt_model


def init_model2():
    # testing data prepare
    mrt_model = mrtModel.MrtModel(model.Graph(path=str(FIXTURE), ET=ET))
    return mrt_model


def test_get_all_stations():
    model = init_model()
    assert model.get_all_stations() == ['n0', 'n1', 'n2', 'n3', 'n4', 'n5', 'n6', 'n7']


def test_get_all_lines():
    model = init_model()
    assert model.get_all_lines() == [2, 1]


def test_get_node_from_line_id():
    model = init_model()
    assert set(model.get_node_from_line_id(2)) == set(['n1::n0', 'n4::n0', 'n5::n0', 'n3::n0', 'n0::n0'])


def test_get_line_name_using_line_id():
    model = init_model()
    assert model.get_line_name_using_line_id(2) == '松山新店線'


def test_get_node_info_using_node_id():
    model = init_model()
    assert model.get_node_info_using_node_id('n1') == ('', '南京復興', '')
    assert model.get_node_info_using_node_id('n1::n0') == ('G\n16', '南京復興', '松山新店線')
    assert model.get_node_info_using_node_id('nn') == ('', '', '')


def test_get_node_from_station_id():
    model = init_model()
    assert set(model.get_node_from_station_id('n1')) == set(['n1::n0', 'n1::n1'])


def test_get_line_from_node_id():
    model = init_model()
    assert set(model.get_line_from_node_id('n1::n0')) == set([2])


def test_find_directional_end_points():
    model = init_model()
    assert set(model.find_directional_end_points('n2::n0', 'n6::n0')) == set(['n7::n0'])
    assert set(model.find_directional_end_points('n2::n1', 'n6::n0')) == set()


def test_find_directional_next_node():
    model = init_model()
    assert set(model.find_directional_next_node('n1::n0', 'n3::n0')) == set(['n4::n0'])
    assert set(model.find_directional_next_node('n2::n1', 'n6::n0')) == set()


def test_find_next_node():
    model = init_model()
    assert set(model.find_next_node('n1::n0')) == set(['n0::n0', 'n3::n0'])
    assert set(model.find_next_node('n1')) == set(['n3::n0', 'n2::n0', 'n6::n0', 'n0::n0'])
    assert set(model.find_next_node('n1::nn')) == set()


def test_find_end_points():
    model = init_model()
    assert set(model.find_end_points('n6::n0')) == set(['n7::n0', 'n2::n0'])
    assert set(model.find_end_points('n1')) == set(['n5::n0', 'n2::n0', 'n7::n0', 'n0::n0'])
    assert set(model.find_end_points('n6::nn')) == set()


def test_get_another_child_node():
    model = init_model()
    assert set(model.get_another_child_node('n6')) == set([])
    assert set(model.get_another_child_node('n1::n0')) == set(['n1::n1'])
    assert set(model.get_another_child_node('n6::nn')) == set([])


def test_get_all_sub_line_from_line_id():
    model = init_model2()
    result = {
        ('n2::n0', 'n1::n1', 'n6::n0', 'n7::n0'),
        ('n7::n0', 'n6::n0', 'n1::n1', 'n2::n0'),
    }
    function_result = model.get_sub_line_from_line_id(1)
    assert function_result == result
