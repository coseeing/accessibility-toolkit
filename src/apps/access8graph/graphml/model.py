import heapq
import itertools
import json
import xml.etree.ElementTree as _ET


def graphf(tree, parent=None):
	nodes = []
	edges = {}

	for item in tree.iterfind("node"):
		nodes.append(nodef(item, parent=parent))

	for item in tree.iterfind("edge"):
		for edge in edgef(item):
			try:
				edges[(edge['source'], edge['target'], edge['line_style']['color'], edge['line_style']['type'])] = edge
			except:
				print("line id:" + json.dumps(edge['id']))
				print("line type:" + json.dumps(edge['line_style']))
				print("source:" + edge['source'])
				print("target:" + edge['target'])

	for item in tree.iterfind("node"):
		parent = item.attrib['id']
		if len(item.findall("graph")) == 1:
			subdata = graphf(item.findall("graph")[0], parent=parent)
			nodes.extend(subdata['nodes'])
	data = {
		"nodes": nodes,
		"edges": edges,
	}
	return data


def extract_geo_and_color(item):
	geometry_item = item.findall("Geometry")[0]
	geometry = {
		'height': geometry_item.attrib["height"],
		'width': geometry_item.attrib["width"],
		'x': geometry_item.attrib["x"],
		'y': geometry_item.attrib["y"],
	}
	fill_item = item.findall("Fill")[0]
	fill = {
		'transparent': fill_item.attrib["transparent"],
	}
	if 'color' in fill_item.attrib:
		fill['color'] = fill_item.attrib['color']
	if 'hasColor' in fill_item.attrib:
		fill['hasColor'] = fill_item.attrib['hasColor']
	border_item = item.findall("BorderStyle")[0]
	border = {
		'type': border_item.attrib["type"],
		'width': border_item.attrib["width"],
	}
	if 'color' in border_item.attrib:
		border['color'] = border_item.attrib['color']
	if 'hasColor' in border_item.attrib:
		border['hasColor'] = border_item.attrib['hasColor']
	return {
		'geometry': geometry,
		'fill': fill,
		'border': border,
	}


def nodef(tree, parent=None):
	pk = tree.attrib['id']
	label = {
		'open': [],
		'close': []
	}
	state = 'open'
	shape = ""
	node_attrib = {}

	items = tree.findall("data/ShapeNode")
	if len(items) == 1:
		item = items[0]
		shape = item.findall("Shape")[0].attrib["type"]
		node_attrib = extract_geo_and_color(item)
		for sub_item in item.findall("NodeLabel"):
			label['open'].append({
				'text': sub_item.text,
				'modelName': sub_item.attrib['modelName']
			})

	items = tree.findall("data/GenericNode")
	if len(items) == 1:
		item = items[0]
		shape = item.attrib['configuration']
		node_attrib = extract_geo_and_color(item)
		for sub_item in item.findall("NodeLabel"):
			label['open'].append({
				'text': sub_item.text,
				'modelName': sub_item.attrib['modelName']
			})

	items = tree.findall("data/ProxyAutoBoundsNode")
	if len(items) == 1:
		state, label, shape, node_attrib = extract_group_node(items[0], label)
	return {
		"id": pk, "label": label, "shape": shape, "state": state,
		"parent": parent, 'geometry': node_attrib['geometry'],
		'fill': node_attrib['fill'], 'border': node_attrib['border']
	}


# Because yEd has some issue, we need to deal with this special case.
def extract_group_node(item, label):
	if len(item.findall("Realizers/GroupNode")) == 1:
		item = item.findall("Realizers/ProxyAutoBoundsNode")[0]
		state, label, shape, node_attrib = extract_group_node(item, label)
	else:
		state = "open" if item.findall("Realizers")[0].attrib["active"] == "0" else "close"
		for gn in item.findall("Realizers/GroupNode"):
			closed = gn.findall("State")[0].attrib["closed"]
			label_key = 'open' if closed == "false" else 'close'
			if closed == "false":
				shape = gn.findall("Shape")[0].attrib["type"]
				node_attrib = extract_geo_and_color(gn)
			for sub_item in gn.findall("NodeLabel"):
				label[label_key].append({
					'text': sub_item.text,
					'modelName': sub_item.attrib['modelName']
				})
	return state, label, shape, node_attrib


def edgef(tree):
	pk = tree.attrib['id']
	label = []
	source = tree.attrib['source']
	target = tree.attrib['target']
	line_style = {}
	arrows_direct = 'bi'  # source/target/bi

	for item in itertools.chain(tree.iterfind("data/PolyLineEdge"), tree.iterfind("data/ArcEdge"), tree.iterfind("data/SplineEdge")):
		line_style_item = item.findall("LineStyle")[0]
		line_style = {
			'color': line_style_item.attrib['color'],
			'type': line_style_item.attrib['type'],
			'width': line_style_item.attrib['width'],
		}
		for sub_item in item.findall("EdgeLabel"):
			label.append({
				'text': sub_item.text,
				'modelName': sub_item.attrib['modelName']
			})
		arrows = item.findall("Arrows")[0]
		if arrows.attrib['source'] == 'none' and arrows.attrib['target'] != 'none':
			arrows_direct = 'target'
		elif arrows.attrib['source'] != 'none' and arrows.attrib['target'] == 'none':
			arrows_direct = 'source'

	if arrows_direct == 'bi':
		return [
			{"id": pk, "label": label, "source": source, "target": target, 'line_style': line_style},
			{"id": pk, "label": label, "source": target, "target": source, 'line_style': line_style},
		]
	elif arrows_direct == 'source':
		return [{"id": pk, "label": label, "source": target, "target": source, 'line_style': line_style}]
	elif arrows_direct == 'target':
		return [{"id": pk, "label": label, "source": source, "target": target, 'line_style': line_style}]


class Label:
	def __init__(self, label_info):
		self._text = label_info['text']
		self._modelName = label_info['modelName']

	@property
	def text(self):
		return self._text

	@property
	def modelName(self):
		return self._modelName


class Node:
	def __init__(self, id, label, shape, state, geometry=None, fill=None, border=None):
		self.id = str(id)
		self.layer = len(self.id.split("::"))
		self.state = state
		self._label = {}
		for key, values in label.items():
			self._label[key] = []
			for val in values:
				self._label[key].append(Label(val))
		self.shape = shape
		self.in_edges = []
		self.out_edges = []
		self._parent = None
		self.children = []
		self.geometry = geometry
		self.fill = fill
		self.border = border

	# def __repr__(self):
		# return super().__repr__() + self.id

	@property
	def label(self):
		return self._label[self.state]

	@property
	def parent(self):
		return self._parent

	@parent.setter
	def parent(self, node):
		if self._parent:
			self._parent.children.remove(self)
		if node:
			node.children.append(self)
		self._parent = node

	@property
	def siblings(self):
		return self.parent.children if self.parent else [self]

	@property
	def next_sibling(self):
		index = (self.siblings.index(self) + 1)
		if index < len(self.siblings):
			return self.siblings[index]
		else:
			return None

	@property
	def previous_sibling(self):
		index = (self.siblings.index(self) - 1)
		if index >= 0:
			return self.siblings[index]
		else:
			return None

	def add_children(self, node):
		node.parent = self
		self.children.append(node)

	def remove_children(self, node):
		node.parent = None
		self.children.remove(node)

	def add_in_edges(self, edge):
		edge.set_target(self)

	def remove_in_edges(self, edge):
		edge.set_target(None)

	def add_out_edges(self, edge):
		edge.set_source(self)

	def remove_out_edges(self, edge):
		edge.set_source(None)


class Edge:
	def __init__(self, id, label, line_style):
		self.id = id
		self.label = []
		for lab in label:
			self.label.append(Label(lab))
		self.line_style = line_style
		self.source = None
		self.target = None

	def set_source(self, node):
		if self.source:
			self.source.out_edges.remove(self)
		self.source = node
		if self.source:
			self.source.out_edges.append(self)

	def set_target(self, node):
		if self.target:
			self.target.in_edges.remove(self)
		self.target = node
		if self.target:
			self.target.in_edges.append(self)


class Graph:
	def __init__(self, path=None, ET=_ET):
		self.node_list = []
		self.edge_list = []
		self.node_max = 0
		self.edge_max = 0
		self.node_map = {}
		self.edge_map = {}
		if path:
			self.load(path, ET)

	def load(self, path, ET):
		self.node_list = []
		self.edge_list = []
		self.node_max = 0
		self.edge_max = 0
		self.node_map = {}
		self.edge_map = {}

		with open(path, "r", encoding="utf8") as f:
			content = f.read()
		parser = ET.XMLParser()
		try:
			tree = ET.fromstring(content.encode('utf-8'), parser=parser)
		except Exception as e:
			raise ValueError(f"Failed to parse GraphML file: {e}") from e

		for item in tree.iter():
			_, _, postfix = item.tag.partition('}')
			item.tag = postfix

		tree = tree.findall("graph")[0]
		data = graphf(tree)

		root_instance = Node(
			id="root", label={'open': [{'text': "root", 'modelName': 'custom'}]},
			shape="root", state="open"
		)
		self.node_list.append(root_instance)
		self.node_map[root_instance.id] = root_instance
		self.node_max += 1
		for node in data["nodes"]:
			node_instance = Node(
				id=node["id"], label=node["label"], shape=node["shape"],
				state=node["state"], geometry=node["geometry"], fill=node["fill"],
				border=node["border"]
			)
			self.node_list.append(node_instance)
			self.node_map[node_instance.id] = node_instance
			self.node_max += 1

		for node in data["nodes"]:
			node_instance = self.node_map[node["id"]]
			if node["parent"]:
				node_instance.parent = self.node_map[node["parent"]]
			else:
				node_instance.parent = root_instance

		for node in data["nodes"]:
			node_instance = self.node_map[node["id"]]

		for edge in data["edges"].values():
			edge_id = f'{edge["id"]}_{edge["source"]}_{edge["target"]}'
			edge_instance = Edge(id=edge_id, label=edge["label"], line_style=edge["line_style"])
			self.edge_list.append(edge_instance)
			self.edge_map[edge_id] = edge_instance
			self.edge_max += 1

		for edge in data["edges"].values():
			edge_id = f'{edge["id"]}_{edge["source"]}_{edge["target"]}'
			edge_instance = self.edge_map[edge_id]
			edge_instance.set_source(self.node_map[edge["source"]])
			edge_instance.set_target(self.node_map[edge["target"]])

	def add_node(self, label):
		pk = "n{}a".format(self.node_max)
		node_instance = Node(id=pk, label=label, shape="rectangle", state="open")
		self.node_list.append(node_instance)
		self.node_map[pk] = node_instance
		self.node_max += 1

	def add_edge(self, source, label, target):
		pk = "e{}a".format(self.edge_max)
		edge_instance = Edge(id=pk, label=label)
		self.edge_list.append(edge_instance)
		self.edge_map[pk] = edge_instance
		self.edge_max += 1
		edge_instance.set_source(self.node_map[source])
		edge_instance.set_target(self.node_map[target])


class Path:
	def __init__(self, path_weight):
		self.path_weight = path_weight

	def get_optimized_path(self, start, end):
		# Use dijkstra algorithm, source: chatGPT
		# Create a dictionary to keep track of the shortest distance to each node
		dist = {node: float('inf') for node in self.path_weight}
		# Set the starting node's distance to 0
		dist[start] = 0
		# Create a dictionary to keep track of the previous node in the shortest path
		prev = {node: None for node in self.path_weight}
		# Create a priority queue to store the nodes and their distances
		pq = [(0, start)]
		while pq:
			# Pop the node with the smallest distance from the priority queue
			(distance, node) = heapq.heappop(pq)
			# Check if this is the end node
			if node == end:
				# Build the shortest path by traversing the prev dictionary
				path = []
				while node is not None:
					path.append(node)
					node = prev[node]
				# Reverse the path to get it in the correct order
				path.reverse()
				return dist[end], path
			# Check if we've already visited this node
			if distance > dist[node]:
				continue
			# Loop through the neighboring nodes and update their distances
			for neighbor, weight in self.path_weight[node]:
				new_dist = dist[node] + weight
				if new_dist < dist[neighbor]:
					dist[neighbor] = new_dist
					# Update the previous node for the neighbor
					prev[neighbor] = node
					# Add the neighbor to the priority queue
					heapq.heappush(pq, (new_dist, neighbor))
		# If we get here, we were unable to find a path
		return None, None
