from pathlib import Path
from unittest.mock import Mock
import xml.etree.ElementTree as ET

from apps.access8graph.graphml import model


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "access8graph" / "test.graphml"


def init_graph():
    # testing data prepare
    with open(FIXTURE, "r", encoding="utf8") as f:
        content = f.read()
    parser = ET.XMLParser()
    tree = ET.fromstring(content.encode('utf-8'), parser=parser)
    for item in tree.iter():
        _, _, postfix = item.tag.partition('}')
        item.tag = postfix
    tree = tree.findall("graph")[0]
    return tree


def test_graphf(monkeypatch):
    tree = init_graph()

    # mock functions
    nodef = Mock(return_value=1)
    monkeypatch.setattr(model, "nodef", nodef)
    fake_source_id = 0
    fake_target_id = 10

    def mock_edgef(item):
        nonlocal fake_source_id, fake_target_id
        fake_source_id += 1
        fake_target_id += 1
        return [
            {
                'source': fake_source_id,
                'target': fake_target_id,
                'line_style': {
                    'color': '',
                    'type': ''
                }
            }
        ]
    edgef = Mock(side_effect=mock_edgef)
    monkeypatch.setattr(model, "edgef", edgef)

    # UT
    data = model.graphf(tree)
    assert nodef.call_count == 28
    assert edgef.call_count == 10
    assert data['nodes'] == [1] * 28
    assert len(data['edges']) == 10


def test_nodef():
    # testing data prepare
    tree = init_graph()
    # test parsing ProxyAutoBoundsNode
    proxy_auto_bounds_node = tree.findall("node")[0]
    node_class = model.nodef(proxy_auto_bounds_node, parent=None)
    proxy_auto_bounds_node_info = {
        'id': 'n0',
        'label': {
            'open': [{'text': '松江南京', 'modelName': 'internal'}],
            'close': [{'text': 'Folder 1', 'modelName': 'internal'}]
        },
        'shape': 'roundrectangle', 'state': 'open',
        'parent': None,
        'geometry': {
            'height': '82.892578125', 'width': '84.0', 'x': '800.0', 'y': '301.107421875'
        },
        'fill': {'transparent': 'false', 'color': '#F5F5F5'},
        'border': {'type': 'dashed', 'width': '1.0', 'color': '#000000'}
    }
    assert node_class == proxy_auto_bounds_node_info
    # test parsing ShapeNode
    shape_node = tree.findall("node")[0].findall("graph")[0].findall("node")[0]
    node_class = model.nodef(shape_node, parent=None)
    shape_node_info = {
        'id': 'n0::n0',
        'label': {
            'open': [{'text': 'G\n15', 'modelName': 'custom'}], 'close': []
        },
        'shape': 'roundrectangle',
        'state': 'open', 'parent': None,
        'geometry': {
            'height': '30.0', 'width': '24.0', 'x': '815.69776', 'y': '336.6201171875'
        },
        'fill': {
            'transparent': 'false', 'color': '#FFFFFF'
        },
        'border': {
            'type': 'line', 'width': '4.0', 'color': '#339966'
        }
    }
    assert node_class == shape_node_info


def test_Node():
    # testing data prepare
    tree = init_graph()
    # test parsing ShapeNode
    shape_node = tree.findall("node")[0].findall("graph")[0].findall("node")[0]
    node_class = model.nodef(shape_node, parent=None)
    node_instance = model.Node(
        id=node_class["id"], label=node_class["label"], shape=node_class["shape"],
        state=node_class["state"], geometry=node_class["geometry"], fill=node_class["fill"],
        border=node_class["border"]
    )
    shape_node_info = {
        'id': 'n0::n0',
        'label': {
            'open': [{'text': 'G\n15', 'modelName': 'custom'}], 'close': []
        },
        'shape': 'roundrectangle',
        'state': 'open', 'parent': None,
        'geometry': {
            'height': '30.0', 'width': '24.0', 'x': '815.69776', 'y': '336.6201171875'
        },
        'fill': {
            'transparent': 'false', 'color': '#FFFFFF'
        },
        'border': {
            'type': 'line', 'width': '4.0', 'color': '#339966'
        }
    }
    assert node_instance.label[0].text == 'G\n15'
    assert node_class == shape_node_info


def test_extract_geo_and_color():
    # testing data prepare
    tree = init_graph()
    # test parsing ShapeNode
    shape_node = tree.findall("node")[1].findall("graph")[0].findall("node")[0]
    item = shape_node.findall("data/ShapeNode")[0]
    node_attrib = model.extract_geo_and_color(item)
    attrib_info = {
        'geometry': {
            'height': '30.0', 'width': '24.0', 'x': '1015.69776', 'y': '336.6201171875'
        },
        'fill': {
            'transparent': 'false', 'color': '#FFFFFF'
        },
        'border': {
            'type': 'line', 'width': '4.0', 'color': '#339966'
        }
    }
    assert node_attrib == attrib_info


def test_edgef():
    # testing data prepare
    tree = init_graph()
    # test parsing PolyLineEdge
    poly_line_edge = tree.findall("edge")[0]
    line_class = model.edgef(poly_line_edge)
    poly_line_edge_info = [
        {
            'id': 'e0', 'label': [], 'source': 'n0::n0',
            'target': 'n1::n0',
            'line_style': {
                'color': '#339966', 'type': 'line', 'width': '4.0'
            }
        },
        {
            'id': 'e0', 'label': [], 'source': 'n1::n0',
            'target': 'n0::n0',
            'line_style': {
                'color': '#339966', 'type': 'line', 'width': '4.0'
            }
        }
    ]
    assert line_class == poly_line_edge_info


def test_Edge():
    # testing data prepare
    tree = init_graph()
    # test parsing PolyLineEdge
    poly_line_edge = tree.findall("edge")[0]
    line_class = model.edgef(poly_line_edge)[0]
    edge_id = f'{line_class["id"]}_{line_class["source"]}_{line_class["target"]}'
    edge_instance = model.Edge(id=edge_id, label=line_class["label"], line_style=line_class["line_style"])
    assert edge_instance.id == edge_id
    assert edge_instance.line_style == {
        'color': '#339966',
        'type': 'line',
        'width': '4.0'
    }


def test_Graph():
    data = model.Graph(path=str(FIXTURE), ET=ET)
    assert len(data.node_list) == 29
    assert len(data.edge_list) == 20
    assert data.node_max == 29
    assert data.edge_max == 20


def test_Path():
    path_weight = {
        'n1::n0': {('n0::n0', 1), ('n1::n1', 5), ('n3::n0', 1)},
        'n1::n1': {('n6::n0', 1), ('n1::n0', 5), ('n2::n0', 1)},
        'n0::n0': {('n1::n0', 1)},
        'n3::n0': {('n4::n0', 1), ('n1::n0', 1)},
        'n2::n0': {('n1::n1', 1)},
        'n6::n0': {('n1::n1', 1), ('n7::n0', 1)},
        'n4::n0': {('n3::n0', 1), ('n5::n0', 1)},
        'n5::n0': {('n4::n0', 1)},
        'n7::n0': {('n6::n0', 1)}
    }
    path = model.Path(path_weight)
    assert path.get_optimized_path('n1::n0', 'n4::n0') == (2, ['n1::n0', 'n3::n0', 'n4::n0'])

