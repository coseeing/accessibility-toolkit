try:
    _
except NameError:
    _ = lambda message: message


class MrtFlow:
    def __init__(self, navigator, output):
        self.pass_key = [f"numpad{i}" for i in range(1, 10)]
        self.navigator = navigator
        self.output = output
        self.message = []
        self.states = {
            "mode": ModeState(self),
            "stations": StationsState(self),
            "lines": LinesState(self),
            "direction_end_point": DirectionEndPointState(self),
            "direction_run": DirectionRunState(self),
            "undirection_run": UndirectionRunState(self),
            "plan_run": PlanRunState(self),
            "direction_transfer": DirectionTransferState(self),
            "undirection_transfer": UndirectionTransferState(self),
            "explore_neighbor": ExploreNeighborState(self),
            "explore_sub_line": ExploreSubLineState(self),
            "direction_stations": DirectionStationsState(self),
            "direction_lines": DirectionLinesState(self),
            "source_stations": SourceStationsState(self),
            "source_lines": SourceLinesState(self),
            "destination_stations": DestinationStationsState(self),
            "destination_lines": DestinationLinesState(self),
            "undirection_stations": UndirectionStationsState(self),
            "undirection_lines": UndirectionLinesState(self),
            "undirection_sub_lines": UndirectionSubLinesState(self),
        }
        self.background_state = None
        self._state = self.states["mode"]
        self._state.active = True
        self.state = self.states["mode"]
        self._speak_current_view()

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        if not self._state == value:
            if self._state:
                self._state.active = False
            self._state = value
            self._state.active = True

    def _collect_speech_items(self):
        speech_items = []
        speech_items.extend(self.message)
        self.message = []
        if self.state.hint and self.state.view.hint:
            speech_items.append(self.state.view.hint)
            self.state.hint = False
        speech_items.extend(self.state.view.display)
        return [item for item in speech_items if item]

    def _speak_current_view(self) -> None:
        speech_items = self._collect_speech_items()
        self.output.cancel_speech()
        self.output.speak(speech_items)

    def enter(self, command):
        key = command["key"]
        result = True
        if key == "enter":
            self.state.onok()
        else:
            try:
                result = getattr(self.state, key)()
            except AttributeError:
                result = False

        if not result:
            self.output.beep_failure()

        self._speak_current_view()
        return bool(result)


class State:
    def __init__(self, flow):
        self.flow = flow
        self._active = False
        self.hint = False
        self.view = None
        self.open_message = ""
        self.close_message = ""

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, value):
        if value is True:
            self.refresh_view()
            self.enter()
            self.hint = True
        else:
            self.exit()
        self._active = value

    def refresh_view(self):
        pass

    def enter(self):
        if self.open_message != "":
            self.flow.message.append(self.open_message)

    def exit(self):
        if self.close_message != "":
            self.flow.message.append(self.close_message)

    def onok(self):
        pass

    @property
    def help(self):
        return []

    def h(self):
        if len(self.help) > 0:
            self.flow.state = HelpState(state=self, flow=self.flow)
            return True
        else:
            return False


class ListState(State):
    def up(self):
        return self.view.up()

    def down(self):
        return self.view.down()

    def home(self):
        return self.view.home()

    def end(self):
        return self.view.end()


class HelpState(ListState):
    def __init__(self, state, *args, **kwargs):
        self.state = state
        super().__init__(*args, **kwargs)
        self.open_message = _("說明選單開啟")
        self.close_message = _("說明選單關閉")

    def refresh_view(self):
        self.view = ListView(
            data=[{
                "id": item["key"],
                "label": item["doc"],
                "description": _(f'按鍵{item["key"]}'),
            } for item in self.state.help],
            hint=_("請使用上下鍵瀏覽說明選單")
        )

    def onok(self):
        self.flow.state = self.state
        try:
            getattr(self.flow.state, self.view.id)()
        except AttributeError:
            pass

    def q(self):
        self.flow.state = self.state
        return True


class ModeState(ListState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.open_message = _("功能選單開啟")
        self.close_message = _("功能選單關閉")

    def refresh_view(self):
        self.view = ListView(
            data=[
                {"id": "direction", "label": _("方向探索")},
                {"id": "undirection", "label": _("線性探索")},
                {"id": "plan", "label": _("路線規劃")},
            ],
            hint=_("請使用上下鍵選擇導航模式")
        )

    def onok(self):
        result = False
        if self.view.id == "direction":
            result = self.d()
        elif self.view.id == "undirection":
            result = self.u()
        elif self.view.id == "plan":
            result = self.p()
        return result

    def enter(self):
        state = self.flow.background_state
        if state and self.flow.navigator["direction"].run:
            if self.open_message != "":
                self.flow.message.append(self.open_message)
        if self.open_message != "":
            self.flow.message.append(self.open_message)

    def exit(self):
        pass

    def d(self):
        self.flow.background_state = self.flow.states["direction_run"]
        self.flow.navigator["direction"].line = None
        self.flow.navigator["direction"].station = None
        self.flow.state = self.flow.states["direction_lines"]
        return True

    def p(self):
        self.flow.background_state = self.flow.states["plan_run"]
        self.flow.navigator["direction"].line = None
        self.flow.navigator["direction"].station = None
        self.flow.state = self.flow.states["source_lines"]
        return True

    def u(self):
        self.flow.navigator["undirection"].line = None
        self.flow.navigator["undirection"].station = None
        self.flow.state = self.flow.states["undirection_lines"]
        return True

    def q(self):
        state = self.flow.background_state
        if state and self.flow.navigator["direction"].run:
            self.flow.message.append(self.close_message)
            self.flow.state = state
            return True
        else:
            return False


class StationsState(ListState):
    def refresh_view(self):
        self.view = ListView(self.flow.navigator["direction"].stations_display, hint=_("切換至車站列表，請使用上下鍵選擇瀏覽車站所在的路線"))

    def onok(self):
        self.flow.navigator["direction"].station = self.view.id
        self.flow.state = self.flow.states["lines"]

    @property
    def help(self):
        return [
            {
                "key": "l",
                "doc": _("切換至路線列表"),
            },
        ]

    def l(self):
        self.flow.navigator["direction"].line = None
        self.flow.state = self.flow.states["lines"]
        return True

    def q(self):
        self.flow.navigator["direction"].line = None
        self.flow.navigator["direction"].station = None
        state = self.flow.background_state
        if state and self.flow.navigator["direction"].run:
            self.flow.message.append(_("車站瀏覽選單關閉"))
            self.flow.state = state
            return True
        else:
            return False


class LinesState(ListState):
    def refresh_view(self):
        self.view = ListView(self.flow.navigator["direction"].lines_display, hint=_("切換至路線列表，請使用上下鍵選擇瀏覽路線包含的車站"))

    def onok(self):
        self.flow.navigator["direction"].line = self.view.id
        self.flow.state = self.flow.states["stations"]

    @property
    def help(self):
        return [
            {
                "key": "s",
                "doc": _("切換至車站列表"),
            },
        ]

    def q(self):
        self.flow.navigator["direction"].line = None
        self.flow.navigator["direction"].station = None
        state = self.flow.background_state
        if state and self.flow.navigator["direction"].run:
            self.flow.message.append(_("車站瀏覽選單關閉"))
            self.flow.state = state
            return True
        else:
            return False

    def s(self):
        self.flow.navigator["direction"].station = None
        self.flow.state = self.flow.states["stations"]
        return True


class DirectionStationsState(ListState):
    def refresh_view(self):
        self.view = ListView(self.flow.navigator["direction"].stations_display, hint=_("切換至車站列表，請使用上下鍵選擇起點車站"))

    def onok(self):
        self.flow.navigator["direction"].station = self.view.id
        if self.flow.navigator["direction"].station and self.flow.navigator["direction"].line:
            result = list(self.flow.navigator["direction"].model.get_node_from_station_id_line_id(self.flow.navigator["direction"].station, self.flow.navigator["direction"].line))[0]
            self.flow.navigator["direction"].current = self.flow.navigator["direction"].source = result
            self.flow.navigator["direction"].line = None
            self.flow.navigator["direction"].station = None
            self.flow.state = self.flow.states["direction_end_point"]
        else:
            self.flow.state = self.flow.states["direction_lines"]

    @property
    def help(self):
        return [
            {
                "key": "l",
                "doc": _("切換至路線列表"),
            },
        ]

    def l(self):
        self.flow.navigator["direction"].line = None
        self.flow.navigator["direction"].station = None
        self.flow.state = self.flow.states["direction_lines"]
        return True


class DirectionLinesState(ListState):
    def refresh_view(self):
        self.view = ListView(self.flow.navigator["direction"].lines_display, hint=_("切換至路線列表，請使用上下鍵選擇路線"))

    def onok(self):
        self.flow.navigator["direction"].line = self.view.id
        if self.flow.navigator["direction"].station and self.flow.navigator["direction"].line:
            result = list(self.flow.navigator["direction"].model.get_node_from_station_id_line_id(self.flow.navigator["direction"].station, self.flow.navigator["direction"].line))[0]
            self.flow.navigator["direction"].current = self.flow.navigator["direction"].source = result
            self.flow.navigator["direction"].line = None
            self.flow.navigator["direction"].station = None
            self.flow.state = self.flow.states["direction_end_point"]
        else:
            self.flow.state = self.flow.states["direction_stations"]

    @property
    def help(self):
        return [
            {
                "key": "s",
                "doc": _("切換至車站列表"),
            },
        ]

    def enter(self):
        super().enter()
        if len(self.view._data) == 1:
            self.onok()

    def s(self):
        self.flow.navigator["direction"].line = None
        self.flow.navigator["direction"].station = None
        self.flow.state = self.flow.states["direction_stations"]
        return True


class DirectionEndPointState(ListState):
    def refresh_view(self):
        self.view = ListView(self.flow.navigator["direction"].end_points, hint=_("請用上下鍵瀏覽並選擇終點方向"))

    def onok(self):
        self.flow.navigator["direction"].destination = self.view.id
        self.flow.state = self.flow.states["direction_run"]


class UndirectionStationsState(ListState):
    def refresh_view(self):
        self.view = ListView(self.flow.navigator["undirection"].stations_display, hint=_("切換至車站列表，請使用上下鍵選擇起點車站"))

    def onok(self):
        self.flow.navigator["undirection"].station = self.view.id
        if self.flow.navigator["undirection"].station and self.flow.navigator["undirection"].line:
            self.flow.state = self.flow.states["undirection_sub_lines"]
        else:
            self.flow.state = self.flow.states["undirection_lines"]

    @property
    def help(self):
        return [
            {
                "key": "l",
                "doc": _("切換至路線列表"),
            },
        ]

    def l(self):
        self.flow.navigator["undirection"].line = None
        self.flow.state = self.flow.states["undirection_lines"]
        return True


class UndirectionLinesState(ListState):
    def refresh_view(self):
        self.view = ListView(self.flow.navigator["undirection"].lines_display, hint=_("切換至路線列表，請使用上下鍵選擇路線"))

    def onok(self):
        self.flow.navigator["undirection"].line = self.view.id
        if self.flow.navigator["undirection"].station and self.flow.navigator["undirection"].line:
            self.flow.state = self.flow.states["undirection_sub_lines"]
        else:
            self.flow.state = self.flow.states["undirection_stations"]

    @property
    def help(self):
        return [
            {
                "key": "s",
                "doc": _("切換至車站列表"),
            },
        ]

    def enter(self):
        super().enter()
        if len(self.view._data) == 1:
            self.onok()

    def s(self):
        self.flow.navigator["undirection"].station = None
        self.flow.state = self.flow.states["undirection_stations"]
        return True


class UndirectionSubLinesState(ListState):
    def refresh_view(self):
        self.view = ListView(self.flow.navigator["undirection"].sub_lines_display, hint=_("切換至子路線列表，請使用上下鍵選擇子路線"))

    def onok(self):
        self.flow.navigator["undirection"].sub_line = self.view.id
        result = list(self.flow.navigator["undirection"].model.get_node_from_station_id_line_id(self.flow.navigator["undirection"].station, self.flow.navigator["undirection"].line))[0]
        self.flow.navigator["undirection"].current = result
        self.flow.state = self.flow.states["undirection_run"]


class SourceStationsState(ListState):
    def refresh_view(self):
        self.view = ListView(self.flow.navigator["direction"].stations_display, hint=_("切換至車站列表，請使用上下鍵選擇起點車站"))

    def onok(self):
        self.flow.navigator["direction"].station = self.view.id
        if self.flow.navigator["direction"].station and self.flow.navigator["direction"].line:
            result = list(self.flow.navigator["direction"].model.get_node_from_station_id_line_id(self.flow.navigator["direction"].station, self.flow.navigator["direction"].line))[0]
            self.flow.navigator["direction"].current = self.flow.navigator["direction"].source = result
            self.flow.navigator["direction"].line = None
            self.flow.navigator["direction"].station = None
            self.flow.state = self.flow.states["destination_lines"]
        else:
            self.flow.state = self.flow.states["source_lines"]

    @property
    def help(self):
        return [
            {
                "key": "l",
                "doc": _("切換至路線列表"),
            },
        ]

    def enter(self):
        super().enter()
        if len(self.view._data) == 1:
            self.onok()

    def l(self):
        self.flow.navigator["direction"].line = None
        self.flow.state = self.flow.states["source_lines"]
        return True


class SourceLinesState(ListState):
    def refresh_view(self):
        self.view = ListView(self.flow.navigator["direction"].lines_display, hint=_("切換至路線列表，請使用上下鍵選擇路線"))

    def onok(self):
        self.flow.navigator["direction"].line = self.view.id
        if self.flow.navigator["direction"].station and self.flow.navigator["direction"].line:
            result = list(self.flow.navigator["direction"].model.get_node_from_station_id_line_id(self.flow.navigator["direction"].station, self.flow.navigator["direction"].line))[0]
            self.flow.navigator["direction"].current = self.flow.navigator["direction"].source = result
            self.flow.navigator["direction"].line = None
            self.flow.navigator["direction"].station = None
            self.flow.state = self.flow.states["destination_lines"]
        else:
            self.flow.state = self.flow.states["source_stations"]

    @property
    def help(self):
        return [
            {
                "key": "s",
                "doc": _("切換至車站列表"),
            },
        ]

    def enter(self):
        super().enter()
        if len(self.view._data) == 1:
            self.onok()

    def s(self):
        self.flow.navigator["direction"].station = None
        self.flow.state = self.flow.states["source_stations"]
        return True


class DestinationStationsState(ListState):
    def refresh_view(self):
        self.view = ListView(self.flow.navigator["direction"].stations_display, hint=_("切換至車站列表，請使用上下鍵選擇目的車站"))

    def onok(self):
        self.flow.navigator["direction"].station = self.view.id
        if self.flow.navigator["direction"].station and self.flow.navigator["direction"].line:
            result = list(self.flow.navigator["direction"].model.get_node_from_station_id_line_id(self.flow.navigator["direction"].station, self.flow.navigator["direction"].line))[0]
            self.flow.navigator["direction"].destination = result
            self.flow.navigator["direction"].line = None
            self.flow.navigator["direction"].station = None
            self.flow.state = self.flow.states["plan_run"]
        else:
            self.flow.state = self.flow.states["destination_lines"]

    @property
    def help(self):
        return [
            {
                "key": "l",
                "doc": _("切換至路線列表"),
            },
        ]

    def enter(self):
        super().enter()
        if len(self.view._data) == 1:
            self.onok()

    def l(self):
        self.flow.navigator["direction"].line = None
        self.flow.state = self.flow.states["destination_lines"]
        return True


class DestinationLinesState(ListState):
    def refresh_view(self):
        self.view = ListView(self.flow.navigator["direction"].lines_display, hint=_("切換至路線列表，請使用上下鍵選擇路線"))

    def onok(self):
        self.flow.navigator["direction"].line = self.view.id
        if self.flow.navigator["direction"].station and self.flow.navigator["direction"].line:
            result = list(self.flow.navigator["direction"].model.get_node_from_station_id_line_id(self.flow.navigator["direction"].station, self.flow.navigator["direction"].line))[0]
            self.flow.navigator["direction"].destination = result
            self.flow.navigator["direction"].line = None
            self.flow.navigator["direction"].station = None
            self.flow.state = self.flow.states["plan_run"]
        else:
            self.flow.state = self.flow.states["destination_stations"]

    @property
    def help(self):
        return [
            {
                "key": "s",
                "doc": _("切換至車站列表"),
            },
        ]

    def enter(self):
        super().enter()
        if len(self.view._data) == 1:
            self.onok()

    def s(self):
        self.flow.navigator["direction"].station = None
        self.flow.state = self.flow.states["destination_stations"]
        return True


class RunState(State):
    @property
    def help(self):
        return [
            {
                "key": "m",
                "doc": _("重新選擇導航模式"),
            },
            {
                "key": "v",
                "doc": _("瀏覽車站與路線列表"),
            },
        ]

    def v(self):
        self.flow.message.append(_("車站瀏覽選單開啟"))
        self.flow.state = self.flow.states["lines"]
        return True

    def m(self):
        self.flow.state = self.flow.states["mode"]
        return True


class DirectionRunState(RunState):
    def refresh_view(self):
        self.view = RunView(
            data={
                "transfer": self.flow.navigator["direction"].transfer_display,
                "current": self.flow.navigator["direction"].current_display,
            },
            hint=_("請使用左右鍵在車站間移動"),
        )

    def e(self):
        self.flow.navigator["direction"].source = self.flow.navigator["direction"].current
        self.flow.navigator["direction"].destination = None
        self.flow.state = self.flow.states["direction_end_point"]
        return True

    def left(self):
        pointer = self.flow.navigator["direction"].reverse
        if len(pointer) == 1:
            self.flow.navigator["direction"].source = self.flow.navigator["direction"].current = pointer[0]
            self.refresh_view()
            return True
        elif len(pointer) > 1:
            self.flow.state = self.flow.states["explore_neighbor"]
            return True
        else:
            return False

    def right(self):
        pointer = self.flow.navigator["direction"].forward
        if len(pointer) == 1:
            self.flow.navigator["direction"].current = pointer[0]
            self.refresh_view()
            result = True
        elif len(pointer) > 1:
            self.flow.navigator["direction"].current = pointer[0]
            self.refresh_view()
            result = True
        else:
            result = False
        return result

    def up(self):
        if len(self.flow.navigator["direction"].transfer_display) == 0:
            return False
        self.flow.state = self.flow.states["direction_transfer"]
        return True

    def down(self):
        if len(self.flow.navigator["direction"].transfer_display) == 0:
            return False
        self.flow.state = self.flow.states["direction_transfer"]
        return True


class UndirectionRunState(RunState):
    def refresh_view(self):
        self.view = RunView(
            data={
                "transfer": self.flow.navigator["undirection"].transfer_display,
                "current": self.flow.navigator["undirection"].current_display,
            },
            hint=_("請使用左右鍵在車站間移動"),
        )

    def left(self):
        pointer = self.flow.navigator["undirection"].previous
        if pointer:
            self.flow.navigator["undirection"].current = pointer
            self.refresh_view()
            result = True
        else:
            result = False
        return result

    def right(self):
        pointer = self.flow.navigator["undirection"].next
        if pointer:
            self.flow.navigator["undirection"].current = pointer
            self.refresh_view()
            result = True
        else:
            result = False
        return result

    def leftbck(self):
        pointer = self.flow.navigator["undirection"].previous
        if pointer:
            self.flow.navigator["undirection"].current = pointer
            self.refresh_view()
            result = True
        elif len(self.flow.navigator["undirection"].transfer_same_sub_line) >= 1:
            self.flow.state = self.flow.states["explore_sub_line"]
            result = True
        else:
            result = False
        return result

    def rightbck(self):
        pointer = self.flow.navigator["undirection"].next
        if pointer:
            self.flow.navigator["undirection"].current = pointer
            self.refresh_view()
            result = True
        elif len(self.flow.navigator["undirection"].transfer_same_sub_line) >= 1:
            self.flow.state = self.flow.states["explore_sub_line"]
            result = True
        else:
            result = False
        return result

    def up(self):
        if len(self.flow.navigator["undirection"].transfer_display) == 0:
            return False
        self.flow.state = self.flow.states["undirection_transfer"]
        return True

    def down(self):
        if len(self.flow.navigator["undirection"].transfer_display) == 0:
            return False
        self.flow.state = self.flow.states["undirection_transfer"]
        return True


class PlanRunState(RunState):
    def refresh_view(self):
        self.view = RunView(
            data={
                "transfer": [],
                "current": self.flow.navigator["direction"].current_display,
            },
            hint=_("路線規劃模式：請使用左右鍵在車站間移動"),
        )

    def left(self):
        pointer = self.flow.navigator["direction"].previous
        if pointer:
            self.flow.navigator["direction"].current = pointer
            self.refresh_view()
            result = True
        else:
            result = False
        return result

    def right(self):
        pointer = self.flow.navigator["direction"].next
        if pointer:
            self.flow.navigator["direction"].current = pointer
            self.refresh_view()
            result = True
        else:
            result = False
        return result


class DirectionTransferState(ListState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.open_message = _("轉乘選單開啟")
        self.close_message = _("轉乘選單關閉")

    def refresh_view(self):
        self.view = ListView(self.flow.navigator["direction"].transfer_display, hint="")

    def onok(self):
        self.flow.navigator["direction"].source = self.flow.navigator["direction"].current = self.view.id[0]
        self.flow.navigator["direction"].destination = self.view.id[1]

        line = self.flow.navigator["direction"].destination_display["label"]["line"]
        station = self.flow.navigator["direction"].destination_display["label"]["name"]

        self.flow.state = self.flow.states["direction_run"]
        self.flow.message.append(_(f"轉乘{line}往{station}"))

    def q(self):
        self.flow.state = self.flow.states["direction_run"]
        return True


class UndirectionTransferState(ListState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.open_message = _("轉乘選單開啟")
        self.close_message = _("轉乘選單關閉")

    def refresh_view(self):
        self.view = ListView(self.flow.navigator["undirection"].transfer_display, hint="")

    def onok(self):
        self.flow.navigator["undirection"].current = self.view.id["current"]
        self.flow.navigator["undirection"].sub_line = self.view.id["sub_line"]

        line = self.flow.navigator["undirection"].line_name_display["label"]
        left = self.flow.navigator["undirection"].left_point_name_display["label"]
        right = self.flow.navigator["undirection"].right_point_name_display["label"]

        self.flow.state = self.flow.states["undirection_run"]
        self.flow.message.append(_(f"轉乘{line}，{left}往{right}"))

    def q(self):
        self.flow.state = self.flow.states["undirection_run"]
        return True


class ExploreNeighborState(ListState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.open_message = _("探索選單開啟")
        self.close_message = _("探索選單關閉")

    def refresh_view(self):
        self.view = ListView(self.flow.navigator["direction"].reverse_display, hint=_("請使用上下鍵選擇探索的下一站"))

    def onok(self):
        self.flow.navigator["direction"].source = self.flow.navigator["direction"].current = self.view.id
        self.flow.state = self.flow.states["direction_run"]

    def q(self):
        self.flow.state = self.flow.states["direction_run"]
        return True


class ExploreSubLineState(ListState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.open_message = _("路線選單開啟")
        self.close_message = _("路線選單關閉")

    def refresh_view(self):
        self.view = ListView(self.flow.navigator["undirection"].transfer_display, hint=_("請使用上下鍵選擇路線"))

    def onok(self):
        if self.flow.navigator["undirection"].mode == "left":
            self.flow.navigator["undirection"].current = self.view.id[-1]
        elif self.flow.navigator["undirection"].mode == "right":
            self.flow.navigator["undirection"].current = self.view.id[0]
        self.flow.navigator["undirection"].sub_line = self.view.id
        self.flow.state = self.flow.states["undirection_run"]

    def q(self):
        self.flow.state = self.flow.states["undirection_run"]
        return True


class ListView:
    def __init__(self, data, hint="", cyclic=False):
        self._data = data
        self.hint = hint

        self._cyclic = cyclic
        self._index = 0

    @property
    def pointer(self):
        return self._data[self._index]

    @property
    def id(self):
        return self.pointer["id"] if "id" in self.pointer else ""

    @property
    def attribute(self):
        return self.pointer["attribute"] if "attribute" in self.pointer else ""

    @property
    def label(self):
        return self.pointer["label"] if "label" in self._data[self._index] else ""

    @property
    def description(self):
        return self.pointer["description"] if "description" in self._data[self._index] else ""

    @property
    def extra(self):
        return f'{len(self._data)} 之 {self._index + 1}'

    @property
    def display(self):
        return [self.attribute, self.label, self.description, self.extra]

    def up(self):
        index = self._index - 1
        if not self._cyclic and index < 0:
            return False
        index %= len(self._data)
        self._index = index
        return True

    def down(self):
        index = self._index + 1
        if not self._cyclic and index >= len(self._data):
            return False
        index %= len(self._data)
        self._index = index
        return True

    def home(self):
        self._index = 0
        return True

    def end(self):
        self._index = len(self._data) - 1
        return True


class RunView:
    def __init__(self, data, hint=""):
        self._data = data
        self.hint = hint

    @property
    def pointer(self):
        return self._data["current"]

    @property
    def id(self):
        return self.pointer["id"]

    @property
    def attribute(self):
        return self.pointer["attribute"] if "attribute" in self.pointer else ""

    @property
    def label(self):
        return self.pointer["label"] if "label" in self.pointer else ""

    @property
    def description(self):
        return self.pointer["description"] if "description" in self.pointer else ""

    @property
    def extra(self):
        if len(self._data["transfer"]) > 0:
            return f'可轉乘，如要轉乘請用上下鍵瀏覽並選擇項目'
        return f''

    @property
    def display(self):
        return [self.attribute, self.label, self.description, self.extra]
