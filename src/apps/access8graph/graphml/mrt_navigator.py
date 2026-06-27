try:
    _
except NameError:
    _ = lambda message: message


class MrtNavigator:
	def __init__(self, model):
		self.model = model

		self.current = None
		self.line = None
		self.station = None

	def reset(self):
		self.current = None
		self.line = None
		self.station = None

	def node_info_display(self, id_):
		node_info = self.model.get_node_info_using_node_id(id_)
		return {
			"number": node_info[0].replace("\n", "").replace("\r", ""),
			"name": node_info[1].replace("\n", "").replace("\r", ""),
			"line": node_info[2].replace("\n", "").replace("\r", ""),
		}

	@property
	def stations_display(self):
		display = []
		if self.line:
			datas = [{"id": id_, "node_info": self.node_info_display(id_)} for id_ in self.model.get_station_from_line_id(self.line)]
			datas = sorted(datas, key=lambda x: x['node_info']["name"])
			for item in datas:
				display.append({
					"id": item["id"],
					"label": item["node_info"]["name"],
				})
		else:
			datas = [{"id": id_, "node_info": self.node_info_display(id_)} for id_ in self.model.get_all_stations()]
			datas = sorted(datas, key=lambda x: x['node_info']["name"])
			for item in datas:
				display.append({
					"id": item["id"],
					"label": item["node_info"]["name"],
				})
		return display

	@property
	def lines_display(self):
		display = []
		if self.station:
			for id_ in self.model.get_line_from_station_id(self.station):
				name = self.model.get_line_name_using_line_id(id_)
				display.append({
					"id": id_,
					"label": name,
				})
		else:
			for id_ in self.model.get_all_lines():
				name = self.model.get_line_name_using_line_id(id_)
				display.append({
					"id": id_,
					"label": name,
				})
		return display

	@property
	def sub_lines_display(self):
		display = []
		if self.line and self.station:
			node_ids = sorted(self.model.get_node_from_station_id_line_id(self.station, self.line))
			if not node_ids:
				return display
			result = node_ids[0]
			datas = [{"id": sub_line, "node_info": (self.node_info_display(sub_line[0]), self.node_info_display(sub_line[-1]))} for sub_line in self.model.get_sub_line_from_node_id(result)]
			datas = sorted(
				datas,
				key=lambda item: (
					item["node_info"][0]["name"],
					item["node_info"][1]["name"],
					item["id"],
				),
			)
			for item in datas:
				display.append({
					"id": item["id"],
				"label": _(f'{item["node_info"][0]["name"]}往{item["node_info"][1]["name"]}'),
				})
		else:
			raise ValueError("station or line is None")
		return display

	@property
	def end_points(self):
		display = []
		datas = [{"id": id_, "node_info": self.node_info_display(id_)} for id_ in self.model.find_end_points(self.current)]
		datas = sorted(datas, key=lambda x: x['node_info']["name"])
		for item in datas:
			display.append({
				"id": item["id"],
				"label": item["node_info"]["name"],
			})
		return display

	@property
	def current_display(self):
		display = None
		id_ = self.current
		if id_:
			node_info = self.node_info_display(id_)
			display = {
				"id": id_,
				"label": node_info["name"],
			}
		return display


class MrtDirectionNavigator(MrtNavigator):
	def __init__(self, model):
		super().__init__(model)
		self.source = None
		self.destination = None

	def reset(self):
		super.reset()
		self.source = None
		self.destination = None

	@property
	def run(self):
		return self.source and self.destination and self.current

	@property
	def transfer_same_end_point(self):
		if self.source == self.current or not self.next:
			return set()

		end = set()

		compare_node = self.next
		if not compare_node:
			for item in self.model.find_end_points(self.current):
				end.add((self.current, item))
			current = end

			compare = set()
		else:
			for item in self.model.find_directional_end_points(self.source, self.current):
				end.add((self.current, item))
			current = end

			end_compare = set()
			for item in self.model.find_directional_end_points(self.source, compare_node):
				end_compare.add((self.current, item))
			compare = end_compare

		return current - compare

	@property
	def transfer_another_end_point(self):
		result = set()
		for item in self.model.get_another_child_node(self.current):
			for i in self.model.find_end_points(item):
				result.add((item, i))
		return result

	@property
	def transfer_same_cross_point(self):
		result = set()
		for cross in self.model.find_cross_points(self.current):
			for end in self.model.find_end_points(cross):
				result.add((cross, end))
		return result

	@property
	def transfer_another_cross_point(self):
		result = set()
		for item in self.model.get_another_child_node(self.current):
			for cross in self.model.find_cross_points(item):
				for end in self.model.find_end_points(cross):
					result.add((cross, end))
		return result

	@property
	def transfer_display(self):
		display = []

		datas = [{"id": (source, destination), "node_info": self.node_info_display(destination)} for source, destination in self.transfer_same_end_point]
		datas = sorted(datas, key=lambda x: x['node_info']["name"])
		for item in datas:
			display.append({
				"id": item["id"],
				"label": _(f'{item["node_info"]["line"]}往{item["node_info"]["name"]}'),
				"attribute": _(f'同線站內轉乘'),
			})

		datas = [{"id": (source, destination), "node_info": self.node_info_display(destination)} for source, destination in self.transfer_another_end_point]
		datas = sorted(datas, key=lambda x: x['node_info']["name"])
		for item in datas:
			display.append({
				"id": item["id"],
				"label": _(f'{item["node_info"]["line"]}往{item["node_info"]["name"]}'),
				"attribute": _(f'換線站內轉乘'),
			})

		datas = [{"id": (source, destination), "node_info": self.node_info_display(destination)} for source, destination in self.transfer_same_cross_point | self.transfer_another_cross_point]
		datas = sorted(datas, key=lambda x: x['node_info']["name"])
		for item in datas:
			display.append({
				"id": item["id"],
				"label": _(f'{item["node_info"]["line"]}往{item["node_info"]["name"]}'),
				"attribute": _(f'站外轉乘'),
			})

		return display

	@property
	def destination_display(self):
		display = None
		id_ = self.destination
		if id_:
			node_info = self.node_info_display(id_)
			display = {
				"id": id_,
				"label": node_info,
			}
		return display

	@property
	def next(self):
		optimized_path = self.model.get_optimized_path(self.source, self.destination)[1]

		index = optimized_path.index(self.current) + 1
		if index >= len(optimized_path):
			result = None
		else:
			result = optimized_path[index]

		return result

	@property
	def previous(self):
		optimized_path = self.model.get_optimized_path(self.source, self.destination)[1]

		index = optimized_path.index(self.current) - 1
		if index < 0:
			result = None
		else:
			result = optimized_path[index]

		return result

	@property
	def forward(self):
		optimized_path = self.model.get_optimized_path(self.source, self.destination)[1]

		index = optimized_path.index(self.current) + 1
		if index >= len(optimized_path):
			result = []
		else:
			result = [optimized_path[index]]

		return result

	@property
	def reverse(self):
		nexts = self.model.find_directional_next_node(self.destination, self.current)
		result = list(nexts)
		return result

	@property
	def forward_display(self):
		display = []
		for item in self.forward:
			node_info = self.node_info_display(item)
			display.append({
				"id": item,
				"label": node_info["name"],
			})
		return display

	@property
	def reverse_display(self):
		display = []
		for item in self.reverse:
			node_info = self.node_info_display(item)
			display.append({
				"id": item,
				"label": node_info["name"],
			})
		return display


class MrtUndirectionNavigator(MrtNavigator):
	def __init__(self, model):
		super().__init__(model)
		self.sub_line = None

	def reset(self):
		super.reset()
		self.sub_line = None

	@property
	def mode(self):
		result = "center"
		index = self.sub_line.index(self.current)
		if index == 0:
			result = "left"
		elif index == len(self.sub_line) - 1:
			result = "right"
		return result

	@property
	def transfer_same_end_sub_line(self):
		transfer = []
		current = self.current
		current_sub_line = self.sub_line
		sub_lines = []

		for sub_line in self.model.get_sub_line_from_node_id(current):
			sub_lines.append({"sub_line": sub_line, "current": current})

		for item in sub_lines:
			if current_sub_line == item["sub_line"] or current_sub_line == item["sub_line"][::-1]:
				continue
			if self.mode == "left" and current == item["sub_line"][-1]:
				transfer.append(item)
			elif self.mode == "right" and current == item["sub_line"][0]:
				transfer.append(item)
		return transfer

	@property
	def transfer_another_end_sub_line(self):
		transfer = []
		current = self.current
		current_sub_line = self.sub_line
		sub_lines = []

		for node in self.model.get_another_child_node(current):
			for sub_line in self.model.get_sub_line_from_node_id(node):
				sub_lines.append({"sub_line": sub_line, "current": node})

		for item in sub_lines:
			if current_sub_line == item["sub_line"] or current_sub_line == item["sub_line"][::-1]:
				continue
			transfer.append(item)

		return transfer

	@property
	def transfer_same_cross_sub_line(self):
		transfer = []
		current = self.current
		current_sub_line = self.sub_line
		sub_lines = []

		for node in self.model.find_cross_points(current):
			for sub_line in self.model.get_sub_line_from_node_id(node):
				sub_lines.append({"sub_line": sub_line, "current": node})

		for item in sub_lines:
			if current_sub_line == item["sub_line"] or current_sub_line == item["sub_line"][::-1]:
				continue
			transfer.append(item)

		return transfer

	@property
	def transfer_another_cross_sub_line(self):
		transfer = []
		current = self.current
		current_sub_line = self.sub_line
		sub_lines = []

		for item in self.model.get_another_child_node(current):
			for node in self.model.find_cross_points(item):
				for sub_line in self.model.get_sub_line_from_node_id(node):
					sub_lines.append({"sub_line": sub_line, "current": node})

		for item in sub_lines:
			if current_sub_line == item["sub_line"] or current_sub_line == item["sub_line"][::-1]:
				continue
			transfer.append(item)

		return transfer

	@property
	def transfer_display(self):
		display = []

		try:
			datas = [{"id": item, "node_info": (self.node_info_display(item["sub_line"][0]), self.node_info_display(item["sub_line"][-1]))} for item in self.transfer_same_end_sub_line]
		except BaseException as e:
			print(e)
			datas = []
		for item in datas:
			display.append({
				"id": item["id"],
				"label": _(f'{item["node_info"][0]["name"]}往{item["node_info"][1]["name"]}'),
				"attribute": _(f'同線站內轉乘'),
			})

		try:
			datas = [{"id": item, "node_info": (self.node_info_display(item["sub_line"][0]), self.node_info_display(item["sub_line"][-1]))} for item in self.transfer_another_end_sub_line]
		except BaseException as e:
			print(e)
			datas = []
		for item in datas:
			display.append({
				"id": item["id"],
				"label": _(f'{item["node_info"][0]["name"]}往{item["node_info"][1]["name"]}'),
				"attribute": _(f'換線站內轉乘'),
			})

		try:
			datas = [{"id": item, "node_info": (self.node_info_display(item["sub_line"][0]), self.node_info_display(item["sub_line"][-1]))} for item in self.transfer_same_cross_sub_line + self.transfer_another_cross_sub_line]
		except BaseException as e:
			print(e)
			datas = []

		for item in datas:
			display.append({
				"id": item["id"],
				"label": _(f'{item["node_info"][0]["name"]}往{item["node_info"][1]["name"]}'),
				"attribute": _(f'站外轉乘'),
			})

		return display

	@property
	def next(self):
		path = self.sub_line

		index = path.index(self.current) + 1
		if index >= len(path):
			result = None
		else:
			result = path[index]

		return result

	@property
	def previous(self):
		path = self.sub_line

		index = path.index(self.current) - 1
		if index < 0:
			result = None
		else:
			result = path[index]

		return result

	@property
	def line_name_display(self):
		display = None
		id_ = self.current
		if id_:
			node_info = self.node_info_display(id_)
			display = {
				"id": id_,
				"label": node_info["line"],
			}
		return display

	@property
	def left_point_name_display(self):
		display = None
		id_ = self.sub_line[0]
		if id_:
			node_info = self.node_info_display(id_)
			display = {
				"id": id_,
				"label": node_info["name"],
			}
		return display

	@property
	def right_point_name_display(self):
		display = None
		id_ = self.sub_line[-1]
		if id_:
			node_info = self.node_info_display(id_)
			display = {
				"id": id_,
				"label": node_info["name"],
			}
		return display
