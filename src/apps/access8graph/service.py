from collections.abc import Callable

from adapters.inputs.base import HotkeyCapture, InputCapture
from adapters.inputs.captured_event import CapturedKeyEvent
from application.events import AppEvent, ErrorRaised, SpeechEngineChanged
from application.input import (
    assemble_pipeline_result,
    InputActivationUseCase,
    KeyboardPipelineResult,
    should_pass_through_system_toggle,
)
from application.input.results import AppKeyEventResult
from application.keyboard import KeyEventHandler, KeyboardInputService
from application.output import Capabilities
from interop.key import HID
from interop.speech.speech_sequence import SpeechSequence

from apps.access8graph.events import GraphNavigationChanged
from apps.access8graph.input import Access8GraphKeyTranslator
from apps.access8graph.output import Access8GraphFlowOutput
from apps.access8graph.use_cases import (
    Access8GraphNavigationSession,
    GraphSelectionUseCase,
    MrtFlowFactory,
)
from apps.shared.mode_manager import ModeManager
from apps.shared.speech_settings_controller import SpeechSettingsController


class Access8GraphNavigationMode:
    mode_id = "navigation"
    enter_usage = HID.F10
    exit_usage = HID.ESCAPE

    def __init__(self, navigation):
        self._navigation = navigation

    def can_enter(self) -> bool:
        return self._navigation.can_start()

    def enter(self) -> bool:
        try:
            self._navigation.start_flow()
        except Exception as error:
            self._navigation._notify_status(ErrorRaised(str(error)))
            return False
        return True

    def exit(self) -> bool:
        self._navigation.stop_flow()
        return True

    def handle_key_event(self, event):
        translator = Access8GraphKeyTranslator()
        command = translator.translate(event)
        if command is None:
            return AppKeyEventResult.HANDLED_STOP
        flow = self._navigation.current_flow
        if flow is None:
            return AppKeyEventResult.UNHANDLED
        flow.enter(command)
        return AppKeyEventResult.HANDLED_STOP


class Access8GraphAppService(KeyEventHandler):
    enter_usage = Access8GraphNavigationMode.enter_usage

    def __init__(
        self,
        *,
        hotkey_capture: HotkeyCapture,
        input_capture: InputCapture,
        capabilities: Capabilities,
        on_speech_engine_changed: Callable[[str], None] | None = None,
        on_voice_changed: Callable[[str, str], None] | None = None,
        on_numeric_setting_changed: Callable[[str, str, int], None] | None = None,
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

        self._flow_output = Access8GraphFlowOutput(capabilities=capabilities)
        self._speech_settings = SpeechSettingsController(
            speech=capabilities.speech,
            on_engine_changed=on_speech_engine_changed,
            on_voice_changed=on_voice_changed,
            on_numeric_setting_changed=on_numeric_setting_changed,
        )
        self._graph_selection = GraphSelectionUseCase()
        self._navigation = Access8GraphNavigationSession(
            graph_selection=self._graph_selection,
            flow_factory=MrtFlowFactory(output=self._flow_output),
            flow_output=self._flow_output,
            notify_status=self._notify_status_listener,
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
            Access8GraphNavigationMode(self._navigation)
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
        if not self._mode_manager.activate_mode("navigation"):
            raise RuntimeError("Failed to start navigation")

    def stop_navigation(self) -> None:
        if self._mode_manager.active_mode_id == "navigation":
            self._mode_manager.exit_active_mode()
        else:
            self._navigation.stop_flow()

    def is_navigation_running(self) -> bool:
        return self._navigation.is_active()

    def get_speech_engine_options(self) -> tuple[tuple[str, str], ...]:
        return self._speech_settings.get_engine_options()

    def get_selected_speech_engine(self) -> str:
        return self._speech_settings.get_selected_engine()

    def set_speech_engine(self, engine_id: str) -> None:
        self._speech_settings.set_engine(engine_id)
        self._notify_status_listener(SpeechEngineChanged(engine_id))

    def get_supported_numeric_settings(self):
        return self._speech_settings.get_supported_numeric_settings()

    def get_available_voices(self) -> tuple[tuple[str, str], ...]:
        return self._speech_settings.list_voices()

    def get_selected_voice(self) -> str | None:
        return self._speech_settings.get_voice()

    def set_selected_voice(self, voice_id: str) -> None:
        self._speech_settings.set_voice(voice_id)

    def get_rate(self) -> int | None:
        return self._speech_settings.get_rate()

    def set_rate(self, value: int) -> None:
        self._speech_settings.set_rate(value)

    def get_pitch(self) -> int | None:
        return self._speech_settings.get_pitch()

    def set_pitch(self, value: int) -> None:
        self._speech_settings.set_pitch(value)

    def get_volume(self) -> int | None:
        return self._speech_settings.get_volume()

    def set_volume(self, value: int) -> None:
        self._speech_settings.set_volume(value)

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
