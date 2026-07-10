from collections.abc import Callable
from typing import Any

from accessibility_toolkit.input.capture import HotkeyCapture, InputCapture, KeyEventDecision
from accessibility_toolkit.input.events import CapturedKeyEvent
from accessibility_toolkit.events import (
    ErrorRaised,
    SpeechEngineChanged,
)
from accessibility_toolkit.input import (
    AppKeyEventResult,
    InputActivationUseCase,
    KeyboardPipelineResult,
    assemble_pipeline_result,
    should_pass_through_system_toggle,
)
from accessibility_toolkit.input import KeyEventHandler
from accessibility_toolkit.output import Capabilities, ClipboardService
from apps.nvda_remote.state import ConnectionState, ControlState, RuntimeState
from accessibility_toolkit.input import HID
from accessibility_toolkit.interop.protocol.connection_info import ConnectionInfo
from accessibility_toolkit.interop.protocol.messages import RemoteMessageType
from accessibility_toolkit.interop.protocol.routing.message_router import MessageRouter
from accessibility_toolkit.interop.protocol.session.remote_session import RemoteSession
from accessibility_toolkit.interop.protocol.transport.base import Transport

from apps.nvda_remote.use_cases.connection import RemoteConnectionUseCase
from apps.nvda_remote.use_cases.protocol_events import RemoteProtocolEventHandler
from apps.nvda_remote.use_cases.status_presentation import RemoteStatusPresenter
from apps.nvda_remote.use_cases import (
    NvdaRemoteControlModeUseCase,
    NvdaRemoteInputForwardingUseCase,
)
from apps.nvda_remote.events import (
    NvdaRemoteEvent,
    RemoteTransportDisconnected,
)
from accessibility_toolkit.interaction import ModeManager


class RemoteControlMode:
    mode_id = "remote_control"
    enter_usage = HID.F11
    exit_usage = HID.F11

    def __init__(self, control_mode, input_forwarding):
        self._control_mode = control_mode
        self._input_forwarding = input_forwarding

    def can_enter(self) -> bool:
        return True

    def enter(self) -> bool:
        self._control_mode.start_control()
        return True

    def exit(self) -> bool:
        self._control_mode.stop_control()
        self._input_forwarding.clear()
        return True

    def handle_key_event(self, event):
        return self._input_forwarding.handle(CapturedKeyEvent(key_event=event, native_context=None))


class NvdaRemoteAppService(KeyEventHandler):
    _LOCAL_STOP_USAGE = HID.F11
    enter_usage = RemoteControlMode.enter_usage

    def __init__(
        self,
        *,
        transport: Transport,
        input_capture: InputCapture,
        hotkey_capture: HotkeyCapture,
        clipboard: ClipboardService,
        capabilities: Capabilities,
        main_thread_dispatch: Callable[[Callable[[], None]], None] | None = None,
        use_windows_native_key_payload: bool = False,
    ) -> None:
        self.transport = transport
        self.input_capture = input_capture
        self.hotkey_capture = hotkey_capture
        self.clipboard = clipboard
        self._capabilities = capabilities
        self.state = RuntimeState()
        self._status_listener: Callable[[NvdaRemoteEvent], None] | None = None
        self._main_thread_dispatch = main_thread_dispatch or (lambda callback: callback())
        self._suppressed_keyups: set[int] = set()

        self.session = RemoteSession(
            transport=transport,
            on_event=self._on_protocol_event,
        )
        self.router = MessageRouter(
            on_speech=self._capabilities.speech.speak,
            on_cancel=self._capabilities.speech.cancel,
            on_pause=self._capabilities.speech.pause,
            on_clipboard=self.clipboard.set_text,
            on_tone=self._handle_tone,
            on_status=self._on_protocol_event,
        )

        self._control_mode = NvdaRemoteControlModeUseCase(
            state=self.state,
            notify_error=self._notify_error,
            notify_status=self._notify_status_listener,
        )
        self._input_forwarding = NvdaRemoteInputForwardingUseCase(
            is_connected=lambda: self.state.connection_state != ConnectionState.IDLE,
            is_controlling=lambda: self.state.control_state == ControlState.CONTROLLING,
            send_key=lambda payload: self.transport.send(RemoteMessageType.KEY, **payload),
            on_local_stop=self.stop_control,
            local_stop_usage=self._LOCAL_STOP_USAGE,
            use_windows_native_key_payload=use_windows_native_key_payload,
        )

        self._activation = InputActivationUseCase(
            input_capture=input_capture,
            hotkey_capture=hotkey_capture,
            is_active=lambda: self.state.control_state == ControlState.CONTROLLING,
            set_active=self._set_control_active,
            notify_error=self._notify_error,
        )
        self._mode_manager = ModeManager(
            activation=self._activation,
            notify_status=self._notify_status_listener,
        )
        self._mode_manager.register(
            RemoteControlMode(self._control_mode, self._input_forwarding)
        )

        self._status_presenter = RemoteStatusPresenter(
            dispatch=self._main_thread_dispatch,
            get_listener=lambda: self._status_listener,
        )

        self._connection = RemoteConnectionUseCase(
            state=self.state,
            exit_active=self._activation.exit_active,
            ensure_hotkey_started=self._ensure_hotkey_started,
            stop_capture=self._stop_capture,
            stop_hotkey=self._stop_hotkey,
            notify=self._status_presenter.notify,
        )

        self._protocol_events = RemoteProtocolEventHandler(
            on_connected=self._connection.handle_connected,
            on_disconnected=self._connection.handle_disconnected,
            notify_remote_message=self._status_presenter.notify,
        )

    def _set_control_active(self, active: bool) -> None:
        self.state.control_state = (
            ControlState.CONTROLLING if active else ControlState.CONNECTED
        )

    def _handle_idle_hotkey(self) -> None:
        if self.state.connection_state == ConnectionState.IDLE:
            return
        if self.state.control_state == ControlState.CONTROLLING:
            return
        self._main_thread_dispatch(self.start_control)

    def bind(self) -> None:
        self.input_capture.set_listener(self.handle_key_event)
        self.hotkey_capture.set_handler(self._handle_idle_hotkey)
        self.transport.set_message_handler(self._handle_transport_message)

    def connect(self, host: str, port: int, key: str, insecure: bool = False) -> None:
        self.session.connect(
            ConnectionInfo(hostname=host, port=port, key=key, insecure=insecure)
        )
        self.transport.start_reader()

    def disconnect(self) -> None:
        if self.state.control_state == ControlState.CONTROLLING:
            self.stop_control()
        elif self.state.connection_state != ConnectionState.IDLE:
            if self._mode_manager.active_mode_id is not None:
                self._mode_manager.exit_active_mode()
            self._activation.exit_active()
        self.transport.stop_reader()
        self.session.disconnect()

    def start_control(self) -> None:
        if self.state.connection_state == ConnectionState.IDLE:
            self._notify_error("Not connected")
            return
        self._mode_manager.activate_mode("remote_control")

    def stop_control(self) -> None:
        if self.state.control_state != ControlState.CONTROLLING:
            return
        self._mode_manager.exit_active_mode()
        self._suppressed_keyups.clear()
        self._input_forwarding.clear()

    def push_clipboard(self) -> None:
        self.transport.send(
            RemoteMessageType.SET_CLIPBOARD_TEXT,
            text=self.clipboard.get_text(),
        )

    def is_clipboard_available(self) -> bool:
        return bool(getattr(self.clipboard, "supported", True))

    def set_status_listener(
        self, listener: Callable[[NvdaRemoteEvent], None] | None
    ) -> None:
        self._status_listener = listener

    def notify_speech_engine_changed(self, engine_id: str) -> None:
        self._notify_status_listener(SpeechEngineChanged(engine_id))

    def shutdown(self) -> None:
        self.disconnect()
        self._capabilities.speech.shutdown()

    def handle_key_event(self, event: CapturedKeyEvent) -> KeyboardPipelineResult:
        key_event = event.key_event
        should_pass_through_toggle = should_pass_through_system_toggle(event)
        if not key_event.pressed and key_event.usage in self._suppressed_keyups:
            self._suppressed_keyups.discard(key_event.usage)
            return assemble_pipeline_result(send_to_system=False, app_result=AppKeyEventResult.HANDLED_STOP)
        if key_event.pressed and key_event.usage == self._LOCAL_STOP_USAGE and self._mode_manager.active_mode_id is not None:
            self._suppressed_keyups.add(self._LOCAL_STOP_USAGE)
        if key_event.pressed and key_event.usage == RemoteControlMode.exit_usage and self._mode_manager.active_mode_id is not None:
            mode_result = self._mode_manager.handle_key_event(key_event)
            return assemble_pipeline_result(send_to_system=False, app_result=mode_result)
        if self.state.control_state == ControlState.CONTROLLING:
            decision = self._input_forwarding.handle(event)
            if decision == KeyEventDecision.SUPPRESS:
                return assemble_pipeline_result(
                    send_to_system=should_pass_through_toggle,
                    app_result=AppKeyEventResult.HANDLED_STOP,
                )
            else:
                return assemble_pipeline_result(send_to_system=True, app_result=AppKeyEventResult.HANDLED_STOP)
        if should_pass_through_toggle:
            return assemble_pipeline_result(send_to_system=True, app_result=AppKeyEventResult.UNHANDLED)
        mode_result = self._mode_manager.handle_key_event(key_event)
        send_to_system = mode_result == AppKeyEventResult.UNHANDLED
        return assemble_pipeline_result(send_to_system=send_to_system, app_result=mode_result)

    def _handle_tone(
        self,
        hz: float,
        length: int,
        left: int = 50,
        right: int = 50,
    ) -> None:
        tone = self._capabilities.tone
        if tone is None:
            return
        tone.beep(hz, length, left, right)

    def _handle_transport_message(self, payload: dict[str, Any]) -> None:
        if payload.get("type") == "transport_disconnected":
            reason = payload.get("reason")
            self._notify_status_listener(
                RemoteTransportDisconnected(
                    None if reason is None else str(reason)
                )
            )
            self._connection.handle_disconnected()
            return
        if self.session.handle_message(payload):
            return
        self.router.handle_message(payload)

    def _on_protocol_event(self, event: object) -> None:
        self._protocol_events.handle(event)

    def _notify_status_listener(
        self,
        status: NvdaRemoteEvent,
    ) -> None:
        self._status_presenter.notify(status)

    def _notify_error(self, message: str) -> None:
        self._notify_status_listener(ErrorRaised(message))

    def _ensure_capture_started(self) -> None:
        if not self.input_capture.running:
            self.input_capture.start()

    def _stop_capture(self) -> None:
        if self.input_capture.running:
            self.input_capture.stop()
        self._suppressed_keyups.clear()
        self._input_forwarding.clear()

    def _ensure_hotkey_started(self) -> None:
        if not self.hotkey_capture.running:
            self.hotkey_capture.start()

    def _stop_hotkey(self) -> None:
        if self.hotkey_capture.running:
            self.hotkey_capture.stop()
