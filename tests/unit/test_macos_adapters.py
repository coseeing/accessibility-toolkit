import pytest

from adapters.inputs.base import KeyEventDecision
from adapters.macos.event_tap import MacOSEventTapManager, RawMacKeyEvent
from adapters.macos.keymap import KEYCODE_TO_VK, key_event_from_macos
from adapters.macos.permissions import AccessibilityPermissions
from interop.key.key_event import KeyEvent


def test_accessibility_permissions_returns_false_without_prompt():
    called = []

    def fake_checker(options):
        called.append(options)
        return False

    permissions = AccessibilityPermissions(checker=fake_checker)

    assert permissions.is_trusted(prompt=False) is False
    assert called == [None]


def test_accessibility_permissions_passes_prompt_option():
    called = []

    def fake_checker(options):
        called.append(options)
        return True

    permissions = AccessibilityPermissions(
        checker=fake_checker,
        prompt_key="prompt-key",
        true_value=True,
    )

    assert permissions.is_trusted(prompt=True) is True
    assert called == [{"prompt-key": True}]


def test_key_event_from_macos_maps_letter_keydown():
    event = key_event_from_macos(key_code=0, pressed=True, is_repeat=False)

    assert event == KeyEvent(vk=0x41, scan=30, extended=False, pressed=True)


def test_key_event_from_macos_maps_f11_keyup():
    event = key_event_from_macos(key_code=103, pressed=False, is_repeat=False)

    assert event == KeyEvent(vk=0x7A, scan=87, extended=False, pressed=False)


def test_key_event_from_macos_maps_common_digit_key():
    event = key_event_from_macos(key_code=18, pressed=True, is_repeat=False)

    assert event == KeyEvent(vk=0x31, scan=2, extended=False, pressed=True)


def test_key_event_from_macos_maps_common_modifier_key():
    event = key_event_from_macos(key_code=56, pressed=True, is_repeat=False)

    assert event == KeyEvent(vk=0x10, scan=42, extended=False, pressed=True)


def test_key_event_from_macos_maps_right_command_key():
    event = key_event_from_macos(key_code=54, pressed=True, is_repeat=False)

    assert event == KeyEvent(vk=0x5C, scan=92, extended=True, pressed=True)


def test_key_event_from_macos_maps_function_key_without_extended_flag():
    event = key_event_from_macos(key_code=109, pressed=True, is_repeat=False)

    assert event == KeyEvent(vk=0x79, scan=68, extended=False, pressed=True)


def test_key_event_from_macos_maps_navigation_key_with_extended_flag():
    event = key_event_from_macos(key_code=121, pressed=False, is_repeat=False)

    assert event == KeyEvent(vk=0x22, scan=81, extended=True, pressed=False)


def test_key_event_from_macos_maps_keypad_digit_key():
    event = key_event_from_macos(key_code=82, pressed=True, is_repeat=False)

    assert event == KeyEvent(vk=0x60, scan=82, extended=False, pressed=True)


def test_key_event_from_macos_maps_keypad_operator_key():
    event = key_event_from_macos(key_code=75, pressed=False, is_repeat=False)

    assert event == KeyEvent(vk=0x6F, scan=53, extended=True, pressed=False)


def test_key_event_from_macos_returns_none_for_unmapped_function_block_key():
    assert key_event_from_macos(key_code=105, pressed=True, is_repeat=False) is None


def test_key_event_from_macos_returns_none_for_unknown_key_code():
    assert key_event_from_macos(key_code=999, pressed=True, is_repeat=False) is None


def test_keycode_table_contains_f11_mapping():
    assert KEYCODE_TO_VK[103] == 0x7A


class FakePermissions:
    def __init__(self, trusted=True, listen_trusted=True):
        self.trusted = trusted
        self.listen_trusted = listen_trusted
        self.calls = []
        self.listen_calls = []

    def is_trusted(self, *, prompt=False):
        self.calls.append(prompt)
        return self.trusted

    def has_listen_event_access(self, *, prompt=False):
        self.listen_calls.append(prompt)
        return self.listen_trusted


class FakeQuartzBackend:
    def __init__(self):
        self.created = 0
        self.enabled = []
        self.released = []
        self.actions = []
        self.run_calls = 0
        self.stop_calls = 0
        self.tap = object()
        self.source = object()

    def create_event_tap(self, callback):
        self.created += 1
        self.callback = callback
        return self.tap

    def create_run_loop_source(self, tap):
        assert tap is self.tap
        return self.source

    def add_source(self, source):
        assert source is self.source

    def enable_tap(self, tap, enabled):
        self.enabled.append((tap, enabled))

    def run_loop_run(self):
        self.run_calls += 1

    def run_loop_stop(self):
        self.stop_calls += 1
        self.actions.append("stop")

    def release(self, value):
        self.actions.append(("release", value))
        self.released.append(value)


class FailingQuartzBackend(FakeQuartzBackend):
    def __init__(self, *, fail_step):
        super().__init__()
        self.fail_step = fail_step

    def create_run_loop_source(self, tap):
        source = super().create_run_loop_source(tap)
        if self.fail_step == "create_run_loop_source":
            raise RuntimeError("run loop source failed")
        return source

    def add_source(self, source):
        super().add_source(source)
        if self.fail_step == "add_source":
            raise RuntimeError("add source failed")

    def enable_tap(self, tap, enabled):
        super().enable_tap(tap, enabled)
        if self.fail_step == "enable_tap":
            raise RuntimeError("enable tap failed")


class FakeThread:
    def __init__(self, *, target, name, daemon, actions=None):
        self.target = target
        self.name = name
        self.daemon = daemon
        self.actions = actions
        self.started = False
        self.join_calls = []

    def start(self):
        self.started = True

    def join(self, timeout=None):
        if self.actions is not None:
            self.actions.append(("join", timeout))
        self.join_calls.append(timeout)


def test_event_tap_manager_requires_accessibility_permission():
    manager = MacOSEventTapManager(
        permissions=FakePermissions(trusted=False),
        backend=FakeQuartzBackend(),
        start_thread=False,
    )

    with pytest.raises(RuntimeError, match="macOS accessibility permission is required"):
        manager.start()


def test_event_tap_manager_requires_input_monitoring_permission():
    manager = MacOSEventTapManager(
        permissions=FakePermissions(listen_trusted=False),
        backend=FakeQuartzBackend(),
        start_thread=False,
    )

    with pytest.raises(RuntimeError, match="macOS input monitoring permission is required"):
        manager.start()


def test_event_tap_manager_starts_backend_once():
    backend = FakeQuartzBackend()
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
        start_thread=False,
    )

    manager.start()
    manager.start()

    assert backend.created == 1
    assert backend.enabled == [(backend.tap, True)]


def test_event_tap_manager_threaded_start_does_not_run_loop_inline(monkeypatch):
    backend = FakeQuartzBackend()
    created_threads = []

    def fake_thread(*, target, name, daemon):
        thread = FakeThread(target=target, name=name, daemon=daemon)
        created_threads.append(thread)
        return thread

    monkeypatch.setattr("adapters.macos.event_tap.threading.Thread", fake_thread)
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
    )

    manager.start()

    assert backend.run_calls == 0
    assert len(created_threads) == 1
    assert created_threads[0].target == backend.run_loop_run
    assert created_threads[0].name == "macos-event-tap"
    assert created_threads[0].daemon is True
    assert created_threads[0].started is True


def test_event_tap_manager_threaded_stop_joins_before_releasing_resources(monkeypatch):
    backend = FakeQuartzBackend()
    created_threads = []

    def fake_thread(*, target, name, daemon):
        thread = FakeThread(
            target=target,
            name=name,
            daemon=daemon,
            actions=backend.actions,
        )
        created_threads.append(thread)
        return thread

    monkeypatch.setattr("adapters.macos.event_tap.threading.Thread", fake_thread)
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
    )

    manager.start()
    manager.stop()

    assert len(created_threads) == 1
    assert created_threads[0].join_calls == [None]
    assert backend.actions == [
        "stop",
        ("join", None),
        ("release", backend.source),
        ("release", backend.tap),
    ]


def test_event_tap_manager_threaded_stop_skips_join_on_current_thread(monkeypatch):
    backend = FakeQuartzBackend()
    created_threads = []

    def fake_thread(*, target, name, daemon):
        thread = FakeThread(
            target=target,
            name=name,
            daemon=daemon,
            actions=backend.actions,
        )
        created_threads.append(thread)
        return thread

    monkeypatch.setattr("adapters.macos.event_tap.threading.Thread", fake_thread)
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
    )

    manager.start()
    monkeypatch.setattr(
        "adapters.macos.event_tap.threading.current_thread",
        lambda: created_threads[0],
    )
    manager.stop()

    assert len(created_threads) == 1
    assert created_threads[0].join_calls == []
    assert backend.actions == [
        "stop",
        ("release", backend.source),
        ("release", backend.tap),
    ]


def test_event_tap_manager_routes_keyboard_decision():
    backend = FakeQuartzBackend()
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
        start_thread=False,
    )
    seen = []
    manager.set_keyboard_listener(lambda event: seen.append(event) or KeyEventDecision.SUPPRESS)

    manager.start()
    decision = manager.handle_raw_event(
        RawMacKeyEvent(key_code=0, pressed=True, is_repeat=False)
    )

    assert seen == [RawMacKeyEvent(key_code=0, pressed=True, is_repeat=False)]
    assert decision == KeyEventDecision.SUPPRESS


def test_event_tap_manager_hotkey_handler_suppresses_matching_event():
    backend = FakeQuartzBackend()
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
        start_thread=False,
    )
    seen = []
    manager.set_hotkey_handler(
        lambda event: seen.append(event) or event.key_code == 103
    )

    manager.start()
    decision = manager.handle_raw_event(
        RawMacKeyEvent(key_code=103, pressed=True, is_repeat=False)
    )

    assert seen == [RawMacKeyEvent(key_code=103, pressed=True, is_repeat=False)]
    assert decision == KeyEventDecision.SUPPRESS


def test_event_tap_manager_stop_releases_resources():
    backend = FakeQuartzBackend()
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
        start_thread=False,
    )

    manager.start()
    manager.stop()

    assert backend.stop_calls == 1
    assert backend.released == [backend.source, backend.tap]


def test_event_tap_manager_start_releases_created_resources_on_partial_failure():
    backend = FailingQuartzBackend(fail_step="enable_tap")
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
        start_thread=False,
    )

    with pytest.raises(RuntimeError, match="enable tap failed"):
        manager.start()

    assert backend.released == [backend.source, backend.tap]
    assert manager.running is False


class FakeManager:
    def __init__(self):
        self.listener = None
        self.hotkey_handler = None
        self.running = False
        self.started = 0
        self.stopped = 0
        self.start_error = None

    def set_keyboard_listener(self, listener):
        self.listener = listener

    def set_hotkey_handler(self, handler):
        self.hotkey_handler = handler

    def start(self):
        self.started += 1
        if self.start_error is not None:
            raise self.start_error
        self.running = True

    def stop(self):
        self.stopped += 1
        self.running = False


def test_macos_keyboard_capture_binds_listener_and_translates_event():
    from adapters.macos.keyboard_hook import MacOSKeyboardCapture

    manager = FakeManager()
    capture = MacOSKeyboardCapture(manager=manager)
    seen = []
    capture.set_listener(lambda event: seen.append(event) or KeyEventDecision.SUPPRESS)

    capture.start()
    decision = manager.listener(RawMacKeyEvent(key_code=0, pressed=True, is_repeat=False))

    assert decision == KeyEventDecision.SUPPRESS
    assert seen == [KeyEvent(vk=0x41, scan=30, extended=False, pressed=True)]


def test_macos_keyboard_capture_translates_common_digit_key():
    from adapters.macos.keyboard_hook import MacOSKeyboardCapture

    manager = FakeManager()
    capture = MacOSKeyboardCapture(manager=manager)
    seen = []
    capture.set_listener(lambda event: seen.append(event) or KeyEventDecision.SUPPRESS)

    capture.start()
    decision = manager.listener(
        RawMacKeyEvent(key_code=18, pressed=True, is_repeat=False)
    )

    assert decision == KeyEventDecision.SUPPRESS
    assert seen == [KeyEvent(vk=0x31, scan=2, extended=False, pressed=True)]


def test_macos_keyboard_capture_ignores_unsupported_key_code():
    from adapters.macos.keyboard_hook import MacOSKeyboardCapture

    manager = FakeManager()
    capture = MacOSKeyboardCapture(manager=manager)
    seen = []
    capture.set_listener(lambda event: seen.append(event) or KeyEventDecision.SUPPRESS)

    capture.start()
    decision = manager.listener(
        RawMacKeyEvent(key_code=999, pressed=True, is_repeat=False)
    )

    assert decision == KeyEventDecision.PASS_THROUGH
    assert seen == []


def test_macos_keyboard_capture_proxies_lifecycle():
    from adapters.macos.keyboard_hook import MacOSKeyboardCapture

    manager = FakeManager()
    capture = MacOSKeyboardCapture(manager=manager)

    capture.start()
    capture.stop()

    assert manager.started == 1
    assert manager.stopped == 1
    assert capture.running is False


def test_macos_keyboard_capture_clears_listener_when_start_fails():
    from adapters.macos.keyboard_hook import MacOSKeyboardCapture

    manager = FakeManager()
    manager.start_error = RuntimeError("boom")
    capture = MacOSKeyboardCapture(manager=manager)
    capture.set_listener(lambda event: KeyEventDecision.PASS_THROUGH)

    with pytest.raises(RuntimeError, match="boom"):
        capture.start()

    assert manager.listener is None


def test_macos_hotkey_capture_triggers_f11_once_on_keydown():
    from adapters.macos.hotkey import MacOSHotkeyCapture

    backend = FakeQuartzBackend()
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
        start_thread=False,
    )
    triggered = []
    capture = MacOSHotkeyCapture(manager=manager)
    capture.set_handler(lambda: triggered.append("f11"))

    capture.start()
    assert manager.handle_raw_event(
        RawMacKeyEvent(key_code=103, pressed=True, is_repeat=False)
    ) == KeyEventDecision.SUPPRESS
    assert manager.handle_raw_event(
        RawMacKeyEvent(key_code=103, pressed=True, is_repeat=True)
    ) == KeyEventDecision.SUPPRESS
    assert manager.handle_raw_event(
        RawMacKeyEvent(key_code=103, pressed=False, is_repeat=False)
    ) == KeyEventDecision.SUPPRESS

    assert triggered == ["f11"]


def test_macos_hotkey_capture_ignores_non_f11_keys():
    from adapters.macos.hotkey import MacOSHotkeyCapture

    backend = FakeQuartzBackend()
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
        start_thread=False,
    )
    triggered = []
    capture = MacOSHotkeyCapture(manager=manager)
    capture.set_handler(lambda: triggered.append("f11"))

    capture.start()
    decision = manager.handle_raw_event(
        RawMacKeyEvent(key_code=0, pressed=True, is_repeat=False)
    )

    assert decision == KeyEventDecision.PASS_THROUGH
    assert triggered == []


def test_macos_hotkey_capture_clears_handler_when_start_fails():
    from adapters.macos.hotkey import MacOSHotkeyCapture

    manager = FakeManager()
    manager.start_error = RuntimeError("boom")
    capture = MacOSHotkeyCapture(manager=manager)
    capture.set_handler(lambda: None)

    with pytest.raises(RuntimeError, match="boom"):
        capture.start()

    assert manager.hotkey_handler is None


def test_macos_hotkey_capture_stop_preserves_active_keyboard_capture():
    from adapters.macos.hotkey import MacOSHotkeyCapture
    from adapters.macos.keyboard_hook import MacOSKeyboardCapture

    backend = FakeQuartzBackend()
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
        start_thread=False,
    )
    hotkey = MacOSHotkeyCapture(manager=manager)
    keyboard = MacOSKeyboardCapture(manager=manager)
    seen = []
    keyboard.set_listener(lambda event: seen.append(event) or KeyEventDecision.SUPPRESS)
    hotkey.set_handler(lambda: None)

    keyboard.start()
    hotkey.start()
    hotkey.stop()
    decision = manager.handle_raw_event(
        RawMacKeyEvent(key_code=0, pressed=True, is_repeat=False)
    )

    assert manager.running is True
    assert backend.stop_calls == 0
    assert decision == KeyEventDecision.SUPPRESS
    assert seen == [KeyEvent(vk=0x41, scan=30, extended=False, pressed=True)]


def test_event_tap_manager_reenables_tap_after_disable_signal():
    backend = FakeQuartzBackend()
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
        start_thread=False,
    )
    manager.start()

    manager.handle_tap_disabled()

    assert backend.enabled == [(backend.tap, True), (backend.tap, True)]


def test_accessibility_permissions_prompt_key_error_is_clear():
    permissions = AccessibilityPermissions(checker=lambda options: True)

    with pytest.raises(RuntimeError, match="Prompt key is required when prompt=True"):
        permissions.is_trusted(prompt=True)


def test_accessibility_permissions_reports_listen_event_access():
    permissions = AccessibilityPermissions(
        checker=lambda options: True,
        listen_checker=lambda: True,
    )

    assert permissions.has_listen_event_access(prompt=False) is True
