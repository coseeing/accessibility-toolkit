from pathlib import Path

import pytest

from application.input.results import AppKeyEventResult
from apps.access8graph.events import GraphNavigationChanged
from apps.access8graph.use_cases.command_dispatch import Access8GraphCommandDispatcher
from apps.access8graph.use_cases.graph_selection import GraphSelectionUseCase
from apps.access8graph.use_cases.navigation import Access8GraphNavigationSession
from interop.key import HID, KeyEvent


def test_graph_selection_accepts_existing_graphml_file(tmp_path: Path) -> None:
    path = tmp_path / "map.GRAPHML"
    path.write_text("<graphml />", encoding="utf-8")
    selection = GraphSelectionUseCase()

    selection.choose_graphml(str(path))

    assert selection.get_selected_graphml_path() == str(path)
    assert selection.require_existing_graphml_path() == path


def test_graph_selection_rejects_non_graphml_file(tmp_path: Path) -> None:
    path = tmp_path / "map.txt"
    path.write_text("<graphml />", encoding="utf-8")
    selection = GraphSelectionUseCase()

    with pytest.raises(ValueError, match="\\.graphml"):
        selection.choose_graphml(str(path))


def test_graph_selection_rejects_missing_file() -> None:
    selection = GraphSelectionUseCase()

    with pytest.raises(FileNotFoundError):
        selection.choose_graphml("/missing/map.graphml")


def test_graph_selection_requires_selected_path_before_start() -> None:
    selection = GraphSelectionUseCase()

    with pytest.raises(RuntimeError, match="No GraphML file selected"):
        selection.require_existing_graphml_path()


class FakeFlowOutput:
    def __init__(self) -> None:
        self.cancel_count = 0

    def cancel_speech(self) -> None:
        self.cancel_count += 1


class FakeFlowFactory:
    def __init__(self) -> None:
        self.paths = []
        self.flow = object()

    def create(self, path: Path):
        self.paths.append(path)
        return self.flow


def test_navigation_session_starts_flow_and_reports_active_state(tmp_path: Path) -> None:
    path = tmp_path / "map.graphml"
    path.write_text("<graphml />", encoding="utf-8")
    selection = GraphSelectionUseCase()
    selection.choose_graphml(str(path))
    statuses = []
    output = FakeFlowOutput()
    factory = FakeFlowFactory()
    session = Access8GraphNavigationSession(
        graph_selection=selection,
        flow_factory=factory,
        flow_output=output,
        notify_status=statuses.append,
    )

    session.set_active(True)
    session.start_flow()

    assert session.is_active() is True
    assert session.current_flow is factory.flow
    assert factory.paths == [path]
    assert statuses == [GraphNavigationChanged(active=True)]


def test_navigation_session_stop_flow_clears_flow_cancels_speech_and_reports_state(
    tmp_path: Path,
) -> None:
    path = tmp_path / "map.graphml"
    path.write_text("<graphml />", encoding="utf-8")
    selection = GraphSelectionUseCase()
    selection.choose_graphml(str(path))
    statuses = []
    output = FakeFlowOutput()
    factory = FakeFlowFactory()
    session = Access8GraphNavigationSession(
        graph_selection=selection,
        flow_factory=factory,
        flow_output=output,
        notify_status=statuses.append,
    )
    session.set_active(True)
    session.start_flow()
    statuses.clear()

    session.stop_flow()

    assert session.is_active() is False
    assert session.current_flow is None
    assert output.cancel_count == 1
    assert statuses == [GraphNavigationChanged(active=False)]


class FakeTranslator:
    def __init__(self, command) -> None:
        self.command = command
        self.events = []

    def translate(self, event):
        self.events.append(event)
        return self.command


class FakeNavigationWithFlow:
    def __init__(self, flow) -> None:
        self.current_flow = flow


class RecordingFlow:
    def __init__(self) -> None:
        self.commands = []

    def enter(self, command) -> bool:
        self.commands.append(command)
        return True


def test_command_dispatcher_consumes_unknown_keys() -> None:
    dispatcher = Access8GraphCommandDispatcher(
        translator=FakeTranslator(None),
        navigation=FakeNavigationWithFlow(RecordingFlow()),
    )

    result = dispatcher.handle_key_event(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F1, pressed=True)
    )

    assert result is AppKeyEventResult.HANDLED_STOP


def test_command_dispatcher_returns_unhandled_without_active_flow() -> None:
    dispatcher = Access8GraphCommandDispatcher(
        translator=FakeTranslator({"key": "down", "repeat": 0, "pressing": 0}),
        navigation=FakeNavigationWithFlow(None),
    )

    result = dispatcher.handle_key_event(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.DOWN, pressed=True)
    )

    assert result is AppKeyEventResult.UNHANDLED


def test_command_dispatcher_sends_commands_to_active_flow() -> None:
    flow = RecordingFlow()
    command = {"key": "down", "repeat": 0, "pressing": 0}
    dispatcher = Access8GraphCommandDispatcher(
        translator=FakeTranslator(command),
        navigation=FakeNavigationWithFlow(flow),
    )

    result = dispatcher.handle_key_event(
        KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.DOWN, pressed=True)
    )

    assert result is AppKeyEventResult.HANDLED_STOP
    assert flow.commands == [command]
