from accessibility_toolkit.input.capture import HotkeyCapture, InputCapture
from accessibility_toolkit.input.events import CapturedKeyEvent
from accessibility_toolkit.events import AppEvent, ErrorRaised, SpeechEngineChanged
from accessibility_toolkit.input import (
    assemble_pipeline_result,
    InputActivationUseCase,
    KeyboardPipelineResult,
    should_pass_through_system_toggle,
)
from accessibility_toolkit.input import AppKeyEventResult
from accessibility_toolkit.input import KeyEventHandler, KeyboardInputService
from accessibility_toolkit.application.output import Capabilities
from accessibility_toolkit.input import HID
from accessibility_toolkit.interop.speech.speech_sequence import SpeechSequence

from apps.access8graph.events import GraphNavigationChanged
from apps.access8graph.input import Access8GraphKeyTranslator
from apps.access8graph.output import Access8GraphFlowOutput
from apps.access8graph.use_cases import (
    Access8GraphCommandDispatcher,
    Access8GraphNavigationSession,
    GraphSelectionUseCase,
    MrtFlowFactory,
)
from accessibility_toolkit.application_support.mode_manager import ModeManager


class Access8GraphNavigationMode:
    mode_id = "navigation"
    enter_usage = HID.F10
    exit_usage = HID.ESCAPE

    def __init__(self, *, navigation, command_dispatcher):
        self._navigation = navigation
        self._command_dispatcher = command_dispatcher

    def can_enter(self) -> bool:
        return self._navigation.can_start()

    def enter(self) -> bool:
        try:
            self._navigation.start_flow()
        except Exception as error:
            self._navigation.report_error(str(error))
            return False
        return True

    def exit(self) -> bool:
        self._navigation.stop_flow()
        return True

    def handle_key_event(self, event):
        return self._command_dispatcher.handle_key_event(event)


class Access8GraphAppService(KeyEventHandler):
    enter_usage = Access8GraphNavigationMode.enter_usage

    def __init__(
        self,
        *,
        hotkey_capture: HotkeyCapture,
        input_capture: InputCapture,
        capabilities: Capabilities,
        main_thread_dispatch=None,
    ) -> None:
        self.hotkey_capture = hotkey_capture
        self.input_capture = input_capture
        self._capabilities = capabilities
        self._input_service: KeyboardInputService | None = None
        self._status_listener = None
        self._main_thread_dispatch = main_thread_dispatch or (
            lambda callback: callback()
        )
        self._hotkey_start_in_progress = False
        self._hotkey_start_reported_error = False

        self._flow_output = Access8GraphFlowOutput(
            speech=capabilities.speech, tone=capabilities.tone
        )
        self._graph_selection = GraphSelectionUseCase()
        self._navigation = Access8GraphNavigationSession(
            graph_selection=self._graph_selection,
            flow_factory=MrtFlowFactory(output=self._flow_output),
            flow_output=self._flow_output,
            notify_status=self._notify_status_listener,
        )
        self._command_dispatcher = Access8GraphCommandDispatcher(
            translator=Access8GraphKeyTranslator(),
            navigation=self._navigation,
        )
        self._activation = InputActivationUseCase(
            input_capture=input_capture,
            hotkey_capture=hotkey_capture,
            is_active=self._navigation.is_active,
            set_active=self._navigation.set_active,
            notify_error=lambda message: self._notify_status_listener(
                ErrorRaised(message)
            ),
        )
        self._mode_manager = ModeManager(
            activation=self._activation,
            notify_status=self._notify_status_listener,
        )

    def attach_input_service(self, input_service: KeyboardInputService) -> None:
        self._input_service = input_service
        self._mode_manager.register(
            Access8GraphNavigationMode(
                navigation=self._navigation,
                command_dispatcher=self._command_dispatcher,
            )
        )

    def bind(self) -> None:
        self.input_capture.set_listener(self.handle_key_event)
        self.hotkey_capture.set_handler(self._handle_idle_hotkey)

    def set_status_listener(self, listener) -> None:
        self._status_listener = listener

    def choose_graphml(self, path: str) -> None:
        self._graph_selection.choose_graphml(path)

    def get_selected_graphml_path(self) -> str | None:
        return self._graph_selection.get_selected_graphml_path()

    def start_navigation(self) -> None:
        self._graph_selection.require_existing_graphml_path()
        if not self._mode_manager.activate_mode("navigation"):
            raise RuntimeError("Failed to start navigation")

    def stop_navigation(self) -> None:
        if self._mode_manager.active_mode_id == "navigation":
            self._mode_manager.exit_active_mode()
        else:
            self._navigation.stop_flow()

    def is_navigation_running(self) -> bool:
        return self._navigation.is_active()

    def notify_speech_engine_changed(self, engine_id: str) -> None:
        self._notify_status_listener(SpeechEngineChanged(engine_id))

    def shutdown(self) -> None:
        self.stop_navigation()
        if self._input_service is not None and self._input_service.running:
            self._input_service.stop()
        if self.hotkey_capture is not None and self.hotkey_capture.running:
            self.hotkey_capture.stop()
        self._capabilities.speech.shutdown()

    def handle_key_event(self, event: CapturedKeyEvent) -> KeyboardPipelineResult:
        try:
            app_result = self._mode_manager.handle_key_event(event.key_event)
        except Exception as error:
            self._notify_status_listener(ErrorRaised(str(error)))
            self.stop_navigation()
            return KeyboardPipelineResult(
                send_to_system=False,
                app_result=AppKeyEventResult.HANDLED_STOP,
            )
        send_to_system = (
            should_pass_through_system_toggle(event)
            and app_result is not AppKeyEventResult.HANDLED_STOP
        )
        return assemble_pipeline_result(
            send_to_system=send_to_system, app_result=app_result
        )

    def _notify_status_listener(
        self, status: AppEvent | GraphNavigationChanged
    ) -> None:
        if self._hotkey_start_in_progress and isinstance(status, ErrorRaised):
            self._hotkey_start_reported_error = True
        if isinstance(status, ErrorRaised):
            self._capabilities.speech.speak(SpeechSequence(items=(status.message,)))
        if self._status_listener is not None:
            self._main_thread_dispatch(lambda: self._status_listener(status))

    def _handle_idle_hotkey(self) -> None:
        if self.is_navigation_running():
            return
        self._main_thread_dispatch(self._start_navigation_from_hotkey)

    def _start_navigation_from_hotkey(self) -> None:
        self._hotkey_start_in_progress = True
        self._hotkey_start_reported_error = False
        try:
            self.start_navigation()
        except Exception as error:
            if self._hotkey_start_reported_error:
                return
            self._notify_status_listener(ErrorRaised(str(error)))
        finally:
            self._hotkey_start_in_progress = False
            self._hotkey_start_reported_error = False
