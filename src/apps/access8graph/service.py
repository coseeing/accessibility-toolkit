from pathlib import Path

from adapters.inputs.base import HotkeyCapture, InputCapture
from adapters.inputs.captured_event import CapturedKeyEvent
from application.input import (
    assemble_pipeline_result,
    InputActivationUseCase,
    KeyboardPipelineResult,
    should_pass_through_system_toggle,
)
from application.input.results import AppKeyEventResult
from application.keyboard import KeyEventHandler, KeyboardInputService
from application.output_capabilities import OutputCapabilities
from interop.key import HID

from apps.access8graph.flow import MrtFlow
from apps.access8graph.graphml import Graph, MrtDirectionNavigator, MrtModel, MrtUndirectionNavigator
from apps.access8graph.input import Access8GraphKeyTranslator
from apps.access8graph.output import Access8GraphFlowOutput
from apps.shared.mode_manager import ModeManager
from apps.shared.speech_settings_controller import SpeechSettingsController


class Access8GraphNavigationMode:
    mode_id = "navigation"
    enter_usage = HID.F10
    exit_usage = HID.ESCAPE

    def __init__(self, service):
        self._service = service

    def can_enter(self) -> bool:
        return self._service.get_selected_graphml_path() is not None

    def enter(self) -> bool:
        try:
            self._service._start_flow()
        except Exception as error:
            self._service._notify_status_listener(
                {"kind": "error", "message": str(error)}
            )
            return False
        return True

    def exit(self) -> bool:
        self._service._stop_flow()
        return True

    def handle_key_event(self, event):
        translator = Access8GraphKeyTranslator()
        command = translator.translate(event)
        if command is None:
            return AppKeyEventResult.HANDLED_STOP
        flow = self._service._flow
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
        outputs: OutputCapabilities,
        main_thread_dispatch=None,
    ) -> None:
        self.hotkey_capture = hotkey_capture
        self.input_capture = input_capture
        self._outputs = outputs
        self._input_service: KeyboardInputService | None = None
        self._status_listener = None
        self._main_thread_dispatch = main_thread_dispatch or (
            lambda callback: callback()
        )
        self._selected_path: str | None = None
        self._navigation_running = False
        self._flow = None
        self._hotkey_start_in_progress = False
        self._hotkey_start_reported_error = False

        self._flow_output = Access8GraphFlowOutput(outputs=outputs)
        self._speech_settings = SpeechSettingsController(
            speech=outputs.speech,
        )
        self._activation = InputActivationUseCase(
            input_capture=input_capture,
            hotkey_capture=hotkey_capture,
            is_active=self.is_navigation_running,
            set_active=self._set_navigation_active,
            notify_error=lambda message: self._notify_status_listener(
                {"kind": "error", "message": message}
            ),
        )
        self._mode_manager = ModeManager(
            activation=self._activation,
            notify_status=self._notify_status_listener,
        )

    def attach_input_service(self, input_service: KeyboardInputService) -> None:
        self._input_service = input_service
        self._mode_manager.register(
            Access8GraphNavigationMode(self)
        )

    def bind(self) -> None:
        self.input_capture.set_listener(self.handle_key_event)
        self.hotkey_capture.set_handler(self._handle_idle_hotkey)

    def set_status_listener(self, listener) -> None:
        self._status_listener = listener

    def choose_graphml(self, path: str) -> None:
        graphml_path = Path(path)
        if graphml_path.suffix.lower() != ".graphml":
            raise ValueError("Selected file must have a .graphml extension")
        if not graphml_path.is_file():
            raise FileNotFoundError(str(graphml_path))
        self._selected_path = str(graphml_path)

    def get_selected_graphml_path(self) -> str | None:
        return self._selected_path

    def start_navigation(self) -> None:
        if self._selected_path is None:
            raise RuntimeError("No GraphML file selected")
        if not Path(self._selected_path).is_file():
            raise FileNotFoundError(
                f"GraphML file no longer exists: {self._selected_path}"
            )
        if not self._mode_manager.activate_mode("navigation"):
            raise RuntimeError("Failed to start navigation")

    def stop_navigation(self) -> None:
        if self._mode_manager.active_mode_id == "navigation":
            self._mode_manager.exit_active_mode()
        else:
            self._stop_flow()

    def is_navigation_running(self) -> bool:
        return self._navigation_running

    def _set_navigation_active(self, active: bool) -> None:
        self._navigation_running = active

    def _start_flow(self) -> None:
        graph = Graph(path=self._selected_path)
        model = MrtModel(graph)
        self._flow = MrtFlow(
            navigator={
                "direction": MrtDirectionNavigator(model),
                "undirection": MrtUndirectionNavigator(model),
            },
            output=self._flow_output,
        )

    def _stop_flow(self) -> None:
        self._navigation_running = False
        self._flow = None
        self._flow_output.cancel_speech()

    def get_speech_backend_options(self) -> tuple[tuple[str, str], ...]:
        return self._speech_settings.get_backend_options()

    def get_selected_speech_backend(self) -> str:
        return self._speech_settings.get_selected_backend()

    def set_speech_backend(self, backend_id: str) -> None:
        self._speech_settings.set_backend(backend_id)
        self._notify_status_listener(
            {"kind": "speech_backend", "backend_id": backend_id}
        )

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
        self._outputs.speech.shutdown()

    def handle_key_event(self, event: CapturedKeyEvent) -> KeyboardPipelineResult:
        try:
            app_result = self._mode_manager.handle_key_event(event.key_event)
        except Exception as error:
            self._notify_status_listener({"kind": "error", "message": str(error)})
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

    def _notify_status_listener(self, status: dict[str, str]) -> None:
        if (
            self._hotkey_start_in_progress
            and status.get("kind") == "error"
        ):
            self._hotkey_start_reported_error = True
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
            self._notify_status_listener({"kind": "error", "message": str(error)})
        finally:
            self._hotkey_start_in_progress = False
            self._hotkey_start_reported_error = False
