from pathlib import Path

from adapters.inputs.base import HotkeyCapture, InputCapture
from adapters.inputs.captured_event import CapturedKeyEvent
from application.input import (
    AppKeyEventResult,
    assemble_pipeline_result,
    InputActivationUseCase,
    KeyboardPipelineResult,
    should_pass_through_system_toggle,
)
from application.keyboard import KeyEventHandler, KeyboardInputService
from application.output_capabilities import OutputCapabilities
from interop.key import HID

from apps.access8graph.flow import MrtFlow
from apps.access8graph.graphml import (
    Graph,
    MrtDirectionNavigator,
    MrtModel,
    MrtUndirectionNavigator,
)
from apps.access8graph.input import Access8GraphKeyTranslator
from apps.access8graph.output import Access8GraphFlowOutput
from apps.shared.speech_settings_controller import SpeechSettingsController


class Access8GraphAppService(KeyEventHandler):
    enter_usage = HID.F10

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
        self._speech_settings = SpeechSettingsController(
            speech=outputs.speech,
        )
        self._translator = Access8GraphKeyTranslator()
        self._selected_graphml_path: str | None = None
        self._flow: MrtFlow | None = None
        self._navigation_active = False
        self._activation = InputActivationUseCase(
            input_capture=input_capture,
            hotkey_capture=hotkey_capture,
            is_active=self.is_navigation_running,
            set_active=self._set_navigation_active,
            notify_error=lambda message: self._notify_status_listener(
                {"kind": "error", "message": message}
            ),
        )

    def attach_input_service(self, input_service: KeyboardInputService) -> None:
        self._input_service = input_service

    def bind(self) -> None:
        self.input_capture.set_listener(self.handle_key_event)
        self.hotkey_capture.set_handler(self._handle_idle_hotkey)

    def set_status_listener(self, listener) -> None:
        self._status_listener = listener

    def choose_graphml(self, path: str) -> None:
        if not path.endswith(".graphml"):
            raise ValueError("Path must end with .graphml")
        if not Path(path).exists():
            raise FileNotFoundError(f"File not found: {path}")
        self._selected_graphml_path = path

    def start_navigation(self) -> None:
        if self._selected_graphml_path is None:
            raise RuntimeError("No GraphML file selected")
        graph = Graph(path=self._selected_graphml_path)
        model = MrtModel(graph)
        direction_navigator = MrtDirectionNavigator(model)
        undirection_navigator = MrtUndirectionNavigator(model)
        navigator = {
            "direction": direction_navigator,
            "undirection": undirection_navigator,
        }
        flow_output = Access8GraphFlowOutput(self._outputs)
        self._flow = MrtFlow(navigator, flow_output)
        self._activation.enter_active()

    def stop_navigation(self) -> None:
        if self._flow is not None:
            self._activation.exit_active()
            self._flow = None

    def is_navigation_running(self) -> bool:
        return self._navigation_active

    def _set_navigation_active(self, active: bool) -> None:
        self._navigation_active = active

    def handle_key_event(self, event: CapturedKeyEvent) -> KeyboardPipelineResult:
        send_to_system = should_pass_through_system_toggle(event)

        if not self.is_navigation_running():
            return assemble_pipeline_result(
                send_to_system=send_to_system,
                app_result=AppKeyEventResult.UNHANDLED,
            )

        command = self._translator.translate(event.key_event)
        if command is None:
            return assemble_pipeline_result(
                send_to_system=False,
                app_result=AppKeyEventResult.HANDLED_STOP,
            )

        if command["key"] == "escape":
            self.stop_navigation()
            return assemble_pipeline_result(
                send_to_system=False,
                app_result=AppKeyEventResult.HANDLED_STOP,
            )

        self._flow.enter(command)
        return assemble_pipeline_result(
            send_to_system=False,
            app_result=AppKeyEventResult.HANDLED_STOP,
        )

    def get_backend_options(self) -> tuple[tuple[str, str], ...]:
        return self._speech_settings.get_backend_options()

    def get_selected_backend(self) -> str:
        return self._speech_settings.get_selected_backend()

    def set_backend(self, backend_id: str) -> None:
        self._speech_settings.set_backend(backend_id)
        self._notify_status_listener(
            {"kind": "speech_backend", "backend_id": backend_id}
        )

    def list_voices(self) -> tuple[tuple[str, str], ...]:
        return self._speech_settings.list_voices()

    def get_voice(self) -> str | None:
        return self._speech_settings.get_voice()

    def set_voice(self, voice_id: str) -> None:
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

    def _notify_status_listener(self, status: dict[str, str]) -> None:
        if self._status_listener is not None:
            self._status_listener(status)

    def _handle_idle_hotkey(self) -> None:
        if self.is_navigation_running():
            return
        self._main_thread_dispatch(self.start_navigation)
