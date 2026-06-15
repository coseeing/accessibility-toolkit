from collections import defaultdict, deque
from apps.access8graph.graphml.model import Path

LEGEND = ['圖例', 'legend', 'Legend']


class MrtModel(Path):
	def __init__(self, data):
		self.data = data
		self.cross_line_path_weight = defaultdict(set)
		self.all_path_in_same_line = defaultdict(set)
		self.all_path_in_cross_line = defaultdict(set)
		self.end_id_for_nodes = defaultdict(set)
		self.feature_to_line_id = {}
		self.line_id_to_name = {}
		self.line_id_mapping_nodes = defaultdict(set)
		self.node_id_mapping_lines = defaultdict(set)
		self.station_id_mapping_nodes = defaultdict(set)
		self.station_id_mapping_lines = defaultdict(set)
		self.line_id_mapping_stations = defaultdict(set)

		self.init()
		super(MrtModel, self).__init__(self.cross_line_path_weight)

	def init(self):
		# try:
			self.init_legend()
			self.init_weight()
			self.init_mapping()
			return True
		# except Exception as e:
			# return False

	def init_legend(self):
		line_id = 1
		for node in self.data.node_list:
			if len(node.label) > 0 and node.label[0].text in LEGEND:
				for cnode in node.children:
					if len(cnode.children) == 1:
						self.feature_to_line_id[cnode.children[0].fill.get('color')] = line_id
						self.line_id_to_name[line_id] = cnode.label[0].text
						line_id += 1
					else:
						for sub_cnode in cnode.children:
							if sub_cnode.in_edges:
								self.feature_to_line_id[sub_cnode.in_edges[0].line_style.get('color')] = line_id
								self.line_id_to_name[line_id] = cnode.label[0].text
								line_id += 1
								break

	def init_mapping(self):
		for node in self.data.node_list:
			if (len(node.label) > 0 and (node.label[0].text == 'root' or node.label[0].text in LEGEND)) or \
				node.layer >= 3:
				continue
			if node.layer == 1:
				for cnode in node.children:
					for edge in cnode.in_edges:
						source_node = self.data.node_map[edge.source.id]
						target_node = self.data.node_map[edge.target.id]
						if 'color' in source_node.border and 'color' in target_node.border and \
							source_node.border['color'] == target_node.border['color']:
							self.all_path_in_same_line[edge.source.id].add(edge.target.id)
							self.line_id_mapping_nodes[
								self._get_feature_to_line_id(source_node.border['color'])
							].add(source_node.id)
							self.line_id_mapping_nodes[
								self._get_feature_to_line_id(target_node.border['color'])
							].add(target_node.id)
							self.node_id_mapping_lines[
								source_node.id
							].add(self._get_feature_to_line_id(source_node.border['color']))
							self.node_id_mapping_lines[
								target_node.id
							].add(self._get_feature_to_line_id(target_node.border['color']))
						else:
							self.all_path_in_cross_line[edge.source.id].add(edge.target.id)
					for edge in cnode.out_edges:
						source_node = self.data.node_map[edge.source.id]
						target_node = self.data.node_map[edge.target.id]
						if 'color' in source_node.border and 'color' in target_node.border and \
							source_node.border['color'] == target_node.border['color']:
							self.all_path_in_same_line[edge.source.id].add(edge.target.id)
							self.line_id_mapping_nodes[
								self._get_feature_to_line_id(source_node.border['color'])
							].add(source_node.id)
							self.line_id_mapping_nodes[
								self._get_feature_to_line_id(target_node.border['color'])
							].add(target_node.id)
							self.node_id_mapping_lines[
								source_node.id
							].add(self._get_feature_to_line_id(source_node.border['color']))
							self.node_id_mapping_lines[
								target_node.id
							].add(self._get_feature_to_line_id(target_node.border['color']))
						else:
							self.all_path_in_cross_line[edge.source.id].add(edge.target.id)

					self.station_id_mapping_nodes[node.id].add(cnode.id)
					for line in self.node_id_mapping_lines[cnode.id]:
						self.station_id_mapping_lines[node.id].add(line)
						self.line_id_mapping_stations[line].add(node.id)

		def dfs(start, previous, graph, visited):
			visited.add(start)
			end_points = set()

			# Check if the current node has no outgoing edges
			if previous in graph[start] and len(graph[start]) == 1:
				end_points.add(start)

			for neighbor in graph[start]:
				if neighbor not in visited:
					end_points |= dfs(neighbor, start, graph, visited)

			visited.remove(start)
			return end_points

		def _find_end_points(graph):
			result = defaultdict(set)
			for node in graph:
				visited = set()
				end_points = dfs(node, None, graph, visited)
				result[node] = end_points
			return result
		self.end_id_for_nodes = _find_end_points(self.all_path_in_same_line)

	def init_weight(self):
		for node in self.data.node_list:
			if (len(node.label) > 0 and (node.label[0].text == 'root' or node.label[0].text in LEGEND)) or \
				node.layer >= 3:
				continue
			if 'color' in node.border and node.layer == 2:
				for edge in node.in_edges:
					self.cross_line_path_weight[edge.source.id].add(
						(edge.target.id, 1 if edge.line_style['type'] == 'line' else 6)
					)
				for edge in node.out_edges:
					self.cross_line_path_weight[edge.source.id].add(
						(edge.target.id, 1 if edge.line_style['type'] == 'line' else 6)
					)
			# Move in transfer station
			if node.children and node.layer == 1:
				# Check with the right type children node
				if 'color' not in node.children[0].border:
					continue
				length_c = len(node.children)
				for i in range(length_c):
					for j in range(i + 1, length_c):
						self.cross_line_path_weight[node.children[i].id].add((node.children[j].id, 5))
						self.cross_line_path_weight[node.children[j].id].add((node.children[i].id, 5))

	def _get_feature_to_line_id(self, feature):
		return self.feature_to_line_id.get(feature, feature)

	def get_line_name_using_line_id(self, id):
		return self.line_id_to_name.get(int(id))

	def get_node_info_using_node_id(self, node_id):
		node = self.data.node_map.get(node_id)
		if not node:
			return ('', '', '')
		if node.layer == 1:
			return ('', node.label[0].text, '')
		else:
			return (
				node.label[0].text, node.parent.label[0].text,
				"/".join([self.get_line_name_using_line_id(item) for item in self.node_id_mapping_lines[node_id]])
			)

	def get_node_from_station_id_line_id(self, station_id, line_id):
		return self.station_id_mapping_nodes[station_id] & self.line_id_mapping_nodes[line_id]

	def get_all_stations(self):
		return list(self.station_id_mapping_nodes.keys())

	def get_all_lines(self):
		return list(self.line_id_mapping_nodes.keys())

	def get_node_from_line_id(self, line_id):
		return list(self.line_id_mapping_nodes.get(int(line_id), []))

	def _get_sub_line_in_same_line(self, sub_line, curr_node_id, break_nodes, visited):
		while self.all_path_in_same_line.get(curr_node_id) and curr_node_id not in break_nodes:
			visited.add(curr_node_id)
			all_visited = True
			for neighbor in self.all_path_in_same_line[curr_node_id]:
				if neighbor not in visited:
					sub_line.append(neighbor)
					curr_node_id = neighbor
					all_visited = False
					break
			if all_visited:
				break
		return sub_line

	def get_sub_line_from_line_id(self, line_id):
		end_nodes = []
		meeting_nodes = []
		sub_lines = []
		all_target_node_counter = defaultdict(set)
		for node_id in list(self.line_id_mapping_nodes.get(int(line_id), [])):
			for target_node_id in self.all_path_in_same_line[node_id]:
				all_target_node_counter[target_node_id].add(node_id)
		for node_id in list(self.line_id_mapping_nodes.get(int(line_id), [])):
			if len(self.all_path_in_same_line[node_id]) == 1 or \
				len(self.all_path_in_same_line[node_id]) < len(all_target_node_counter[node_id]):
				end_nodes.append(node_id)
			elif len(self.all_path_in_same_line[node_id]) > 2 or \
				len(self.all_path_in_same_line[node_id]) > len(all_target_node_counter[node_id]) or \
				set(self.all_path_in_same_line[node_id]) != all_target_node_counter[node_id]:
				meeting_nodes.append(node_id)
		print(end_nodes + meeting_nodes)
		for node_id in end_nodes + meeting_nodes:
			for neighbor_node_id in self.all_path_in_same_line[node_id]:
				visited = set([node_id])
				sub_line = [node_id, neighbor_node_id]
				sub_line = self._get_sub_line_in_same_line(sub_line, neighbor_node_id, meeting_nodes + end_nodes, visited)
				sub_line = tuple(sub_line)
				sub_lines.append(sub_line)
		return set(sub_lines)

	def get_sub_line_from_node_id(self, node_id):
		result = set([])
		for line in self.get_line_from_node_id(node_id):
			for sub_line in self.get_sub_line_from_line_id(line):
				if node_id in sub_line:
					result.add(sub_line)
		return result

	def get_node_from_station_id(self, station_id):
		return list(self.station_id_mapping_nodes.get(station_id, []))

	def get_station_from_line_id(self, line_id):
		return list(self.line_id_mapping_stations.get(line_id, []))

	def get_line_from_station_id(self, station_id):
		return list(self.station_id_mapping_lines.get(station_id, []))

	def get_line_from_node_id(self, node_id):
		return list(self.node_id_mapping_lines.get(node_id, []))

	def _from_start_to_current_visited_set(self, start_location, current_location):
		visited = set()
		start_moving_stack = deque([start_location])
		find_current_location = False
		while start_moving_stack:
			stack_len = len(start_moving_stack)
			for _ in range(stack_len):
				location = start_moving_stack.popleft()
				if location == current_location:
					find_current_location = True
					continue
				visited.add(location)
				for neighbor in self.all_path_in_same_line[location]:
					if neighbor not in visited:
						start_moving_stack.append(neighbor)
		return find_current_location, visited

	def find_directional_end_points(self, start_location, current_location):
		find_current_location, visited = self._from_start_to_current_visited_set(start_location, current_location)
		directional_end_points = set()
		if not find_current_location:
			return directional_end_points

		stack = deque([current_location])
		while stack:
			location = stack.popleft()
			if location not in visited:
				visited.add(location)

				# Check if the current location has no outgoing edges
				if len(self.all_path_in_same_line[location]) == 1 and \
					list(self.all_path_in_same_line[location])[0] in visited:
					directional_end_points.add(location)

				for neighbor in self.all_path_in_same_line[location]:
					if neighbor not in visited:
						stack.append(neighbor)

		return directional_end_points

	def find_directional_next_node(self, start_location, current_location):
		find_current_location, visited = self._from_start_to_current_visited_set(start_location, current_location)
		directional_end_points = set()
		if not find_current_location:
			return directional_end_points

		for neighbor in self.all_path_in_same_line[current_location]:
			if neighbor not in visited:
				directional_end_points.add(neighbor)
		return directional_end_points

	def find_next_node(self, node_id):
		node = self.data.node_map.get(node_id)
		if not node:
			return []
		id_list = []
		if node.children and node.layer == 1:
			for cnode in node.children:
				for node_set in self.cross_line_path_weight[cnode.id]:
					if node_set[1] == 1:
						id_list.append(node_set[0])
		else:
			id_list.extend(self.all_path_in_same_line[node.id])
		return id_list

	def find_end_points(self, node_id):
		node = self.data.node_map.get(node_id)
		if not node:
			return set([])
		id_list = []
		if node.children and node.layer == 1:
			for cnode in node.children:
				id_list.extend(self.end_id_for_nodes[cnode.id])
		else:
			id_list.extend(self.end_id_for_nodes[node.id])
		return set(id_list)

	def find_cross_points(self, node_id):
		return list(self.all_path_in_cross_line.get(node_id, []))

	def get_another_child_node(self, node_id):
		node = self.data.node_map.get(node_id)
		if not node:
			return []
		if node.parent.label[0].text == 'root':
			return []
		id_list = []
		for cnode in node.parent.children:
			if cnode.id != node_id:
				id_list.append(cnode.id)
		return id_list
