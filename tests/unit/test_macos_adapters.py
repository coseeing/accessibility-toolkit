import pytest

from adapters.inputs.base import KeyEventDecision
from adapters.macos.event_tap import (
    MacOSEventTapManager,
    QuartzEventTapBackend,
    RawMacKeyEvent,
)
from adapters.macos.hid_map import KEYCODE_TO_USAGE
from adapters.macos.keymap import key_event_from_macos
from adapters.macos.permissions import AccessibilityPermissions
from interop.key import HID, KeyEvent


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


def test_key_event_from_macos_maps_letter_keydown_to_hid():
    event = key_event_from_macos(key_code=0, pressed=True, is_repeat=False)

    assert event == KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)


def test_key_event_from_macos_maps_f11_keyup_to_hid():
    event = key_event_from_macos(key_code=103, pressed=False, is_repeat=False)

    assert event == KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.F11, pressed=False)


def test_key_event_from_macos_rejects_unknown_key_code():
    event = key_event_from_macos(key_code=999, pressed=True, is_repeat=False)
    assert event is None


def test_keycode_table_contains_f11_mapping():
    assert KEYCODE_TO_USAGE[103] == 0x44


def test_key_event_from_macos_maps_digit_to_hid():
    event = key_event_from_macos(key_code=18, pressed=True, is_repeat=False)
    assert event == KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.DIGIT_1, pressed=True)

    event = key_event_from_macos(key_code=29, pressed=True, is_repeat=False)
    assert event == KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.DIGIT_0, pressed=True)


def test_key_event_from_macos_maps_minus_equals_to_hid():
    event = key_event_from_macos(key_code=27, pressed=True, is_repeat=False)
    assert event == KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.MINUS, pressed=True)

    event = key_event_from_macos(key_code=24, pressed=True, is_repeat=False)
    assert event == KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.EQUALS, pressed=True)


class FakePermissions:
    def __init__(self, trusted=True):
        self.trusted = trusted
        self.listen_trusted = trusted
        self.calls = []

    def is_trusted(self, *, prompt=False):
        self.calls.append(("trusted", prompt))
        return self.trusted

    def has_listen_event_access(self, *, prompt=False):
        self.calls.append(("listen", prompt))
        return self.listen_trusted


class FakeQuartzBackend:
    def __init__(self):
        self._source = None
        self._startup_error: Exception | None = None
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

    def attach_and_run(self, tap):
        self.actions.append(("attach_and_run", tap))
        self.run_calls += 1
        return None

    def set_ready_event(self, ready):
        self._ready_event = ready

    def pop_startup_error(self):
        exc = self._startup_error
        self._startup_error = None
        return exc

    def release_thread_source(self):
        pass

    def run_loop_run(self):
        self.run_calls += 1

    def run_loop_stop(self):
        self.stop_calls += 1
        self.actions.append("stop")

    def release(self, value):
        self.actions.append(("release", value))
        self.released.append(value)


class FakeThread:
    def __init__(self, *, target, name, daemon, args=None, actions=None):
        self.target = target
        self.args = args
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


class FakeEvent:
    def __init__(self):
        self._set = False

    def set(self):
        self._set = True

    def wait(self, timeout=None):
        return True

    def is_set(self):
        return True


def test_event_tap_manager_requires_accessibility_permission():
    manager = MacOSEventTapManager(
        permissions=FakePermissions(trusted=False),
        backend=FakeQuartzBackend(),
        start_thread=False,
    )

    with pytest.raises(RuntimeError, match="macOS accessibility permission is required"):
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

    def fake_thread(*, target, name, daemon, **kwargs):
        thread = FakeThread(target=target, name=name, daemon=daemon)
        created_threads.append(thread)
        return thread

    monkeypatch.setattr("adapters.macos.event_tap.threading.Thread", fake_thread)
    monkeypatch.setattr("adapters.macos.event_tap.threading.Event", FakeEvent)
    manager = MacOSEventTapManager(
        permissions=FakePermissions(),
        backend=backend,
    )

    manager.start()

    assert backend.run_calls == 0
    assert len(created_threads) == 1
    assert created_threads[0].target == backend.attach_and_run
    assert created_threads[0].name == "macos-event-tap"
    assert created_threads[0].daemon is True
    assert created_threads[0].started is True


def test_event_tap_manager_threaded_stop_joins_before_releasing_resources(monkeypatch):
    backend = FakeQuartzBackend()
    created_threads = []

    def fake_thread(*, target, name, daemon, **kwargs):
        thread = FakeThread(
            target=target,
            name=name,
            daemon=daemon,
            actions=backend.actions,
        )
        created_threads.append(thread)
        return thread

    monkeypatch.setattr("adapters.macos.event_tap.threading.Thread", fake_thread)
    monkeypatch.setattr("adapters.macos.event_tap.threading.Event", FakeEvent)
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
    assert seen == [KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)]


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
    assert seen == [KeyEvent(usage_page=HID.KEYBOARD_PAGE, usage=HID.A, pressed=True)]


class FakeQuartzModule:
    kCGEventKeyDown = 10
    kCGEventKeyUp = 11
    kCGEventFlagsChanged = 12
    kCGKeyboardEventKeycode = 200
    kCGKeyboardEventAutorepeat = 201
    kCGSessionEventTap = 0
    kCGHeadInsertEventTap = 0
    kCGEventTapOptionDefault = 0
    kCFRunLoopDefaultMode = "kCFRunLoopDefaultMode"
    kCGEventFlagMaskShift = 0x20000
    kCGEventFlagMaskControl = 0x4000
    kCGEventFlagMaskAlternate = 0x80000
    kCGEventFlagMaskCommand = 0x100000
    kCGEventFlagMaskAlphaShift = 0x10000
    kCGEventSourceStateHIDSystemState = 1

    def __init__(self):
        self.taps_created = []
        self.sources_created = []
        self.sources_added = []
        self.enabled_calls = []
        self.released = []
        self.stopped_rls = []
        self.run_calls = 0
        self.stop_calls = 0
        self._ready: Any = None
        self._startup_error: Exception | None = None

    def set_ready(self, callback=None) -> None:
        if callback is not None:
            self._ready = callback

    def CGEventSourceFlagsState(self, source_state):
        return 0

    def CFRunLoopGetCurrent(self):
        return "CurrentRunLoop"

    def CGEventTapCreate(self, location, place, options, mask, callback, user_data):
        tap = object()
        self.taps_created.append((tap, location, place, options, mask, callback, user_data))
        return tap

    def CFMachPortCreateRunLoopSource(self, allocator, tap, order):
        source = object()
        self.sources_created.append((source, allocator, tap, order))
        return source

    def CFRunLoopAddSource(self, rl, source, mode):
        self.sources_added.append((rl, source, mode))

    def CGEventTapEnable(self, tap, enabled):
        self.enabled_calls.append((tap, enabled))

    def CFRunLoopRun(self):
        self.run_calls += 1

    def CFRunLoopStop(self, rl):
        self.stop_calls += 1
        self.stopped_rls.append(rl)

    def CFRelease(self, obj):
        self.released.append(obj)

    @staticmethod
    def CGEventMaskBit(event_type):
        return 1 << event_type

    @staticmethod
    def CGEventGetIntegerValueField(event, field):
        return event.get(field, 0)

    @staticmethod
    def CGEventGetFlags(event):
        return event.get("flags", 0)

    def attach_and_run(self, tap):
        source = object()
        self.sources_created.append((source, None, tap, 0))
        self.sources_added.append(("CurrentRunLoop", source, self.kCFRunLoopDefaultMode))
        self.enabled_calls.append((tap, True))
        self.run_calls += 1
        if self._ready is not None:
            self._ready()
        return None

    def set_ready(self, callback=None):
        self._ready = callback

    def release_thread_source(self):
        pass

    def pop_startup_error(self):
        exc = self._startup_error
        self._startup_error = None
        return exc


def test_quartz_backend_exists_with_correct_interface():
    backend = QuartzEventTapBackend()
    assert hasattr(backend, "create_event_tap")
    assert hasattr(backend, "create_run_loop_source")
    assert hasattr(backend, "add_source")
    assert hasattr(backend, "enable_tap")
    assert hasattr(backend, "run_loop_run")
    assert hasattr(backend, "run_loop_stop")
    assert hasattr(backend, "release")
    assert callable(backend.create_event_tap)
    assert callable(backend.create_run_loop_source)
    assert callable(backend.add_source)
    assert callable(backend.enable_tap)
    assert callable(backend.run_loop_run)
    assert callable(backend.run_loop_stop)
    assert callable(backend.release)


def test_quartz_backend_create_event_tap_raises_without_quartz():
    backend = QuartzEventTapBackend()
    with pytest.raises(RuntimeError, match="Quartz"):
        backend.create_event_tap(lambda e: KeyEventDecision.PASS_THROUGH)


def test_quartz_backend_methods_raise_without_quartz():
    backend = QuartzEventTapBackend()
    with pytest.raises(RuntimeError, match="Quartz"):
        backend.create_run_loop_source(object())
    with pytest.raises(RuntimeError, match="Quartz"):
        backend.add_source(object())
    with pytest.raises(RuntimeError, match="Quartz"):
        backend.enable_tap(object(), True)
    with pytest.raises(RuntimeError, match="Quartz"):
        backend.run_loop_run()
    backend.run_loop_stop()
    with pytest.raises(RuntimeError, match="Quartz"):
        backend.release(object())


def test_quartz_backend_create_event_tap_returns_tap_and_stores_callback():
    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    callback = lambda e: KeyEventDecision.PASS_THROUGH
    result = backend.create_event_tap(callback)
    tap, *_ = fake_q.taps_created[0]
    assert result is tap
    _, _, _, _, _, stored_cb, user_data = fake_q.taps_created[0]
    assert stored_cb is not callback
    assert user_data is None


def test_quartz_backend_cg_callback_translates_keydown():
    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    received = []
    backend.create_event_tap(lambda e: received.append(e) or KeyEventDecision.PASS_THROUGH)
    cg_callback = fake_q.taps_created[0][5]

    fake_event = {
        fake_q.kCGKeyboardEventKeycode: 0,
        fake_q.kCGKeyboardEventAutorepeat: 0,
    }
    result = cg_callback(None, fake_q.kCGEventKeyDown, fake_event, None)

    assert len(received) == 1
    assert received[0] == RawMacKeyEvent(key_code=0, pressed=True, is_repeat=False)
    assert result is fake_event


def test_quartz_backend_cg_callback_translates_keyup():
    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    received = []
    backend.create_event_tap(lambda e: received.append(e) or KeyEventDecision.PASS_THROUGH)
    cg_callback = fake_q.taps_created[0][5]

    fake_event = {
        fake_q.kCGKeyboardEventKeycode: 103,
        fake_q.kCGKeyboardEventAutorepeat: 0,
    }
    result = cg_callback(None, fake_q.kCGEventKeyUp, fake_event, None)

    assert len(received) == 1
    assert received[0] == RawMacKeyEvent(key_code=103, pressed=False, is_repeat=False)
    assert result is fake_event


def test_quartz_backend_cg_callback_detects_repeat():
    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    received = []
    backend.create_event_tap(lambda e: received.append(e) or KeyEventDecision.PASS_THROUGH)
    cg_callback = fake_q.taps_created[0][5]

    fake_event = {
        fake_q.kCGKeyboardEventKeycode: 0,
        fake_q.kCGKeyboardEventAutorepeat: 1,
    }
    cg_callback(None, fake_q.kCGEventKeyDown, fake_event, None)

    assert received[0] == RawMacKeyEvent(key_code=0, pressed=True, is_repeat=True)


def test_quartz_backend_cg_callback_returns_none_to_suppress():
    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    backend.create_event_tap(lambda e: KeyEventDecision.SUPPRESS)
    cg_callback = fake_q.taps_created[0][5]

    fake_event = {fake_q.kCGKeyboardEventKeycode: 0, fake_q.kCGKeyboardEventAutorepeat: 0}
    result = cg_callback(None, fake_q.kCGEventKeyDown, fake_event, None)

    assert result is None


def test_quartz_backend_cg_callback_returns_event_to_pass_through():
    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    backend.create_event_tap(lambda e: KeyEventDecision.PASS_THROUGH)
    cg_callback = fake_q.taps_created[0][5]

    fake_event = {fake_q.kCGKeyboardEventKeycode: 0, fake_q.kCGKeyboardEventAutorepeat: 0}
    result = cg_callback(None, fake_q.kCGEventKeyDown, fake_event, None)

    assert result is fake_event


def test_quartz_backend_cg_callback_ignores_flags_changed():
    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    called = []
    backend.create_event_tap(lambda e: called.append(e) or KeyEventDecision.PASS_THROUGH)
    cg_callback = fake_q.taps_created[0][5]

    fake_event = {fake_q.kCGKeyboardEventKeycode: 0, fake_q.kCGKeyboardEventAutorepeat: 0}
    result = cg_callback(None, fake_q.kCGEventFlagsChanged, fake_event, None)

    assert called == []
    assert result is fake_event


def test_quartz_backend_cg_callback_flagschanged_shift_pressed():
    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    received = []
    backend.create_event_tap(lambda e: received.append(e) or KeyEventDecision.PASS_THROUGH)
    cg_callback = fake_q.taps_created[0][5]

    fake_event = {
        fake_q.kCGKeyboardEventKeycode: 56,
        "flags": fake_q.kCGEventFlagMaskShift,
    }
    cg_callback(None, fake_q.kCGEventFlagsChanged, fake_event, None)

    assert received == [RawMacKeyEvent(key_code=56, pressed=True, is_repeat=False)]


def test_quartz_backend_cg_callback_flagschanged_shift_released():
    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    received = []
    backend.create_event_tap(lambda e: received.append(e) or KeyEventDecision.PASS_THROUGH)
    cg_callback = fake_q.taps_created[0][5]

    press_event = {
        fake_q.kCGKeyboardEventKeycode: 56,
        "flags": fake_q.kCGEventFlagMaskShift,
    }
    release_event = {
        fake_q.kCGKeyboardEventKeycode: 56,
        "flags": 0,
    }
    cg_callback(None, fake_q.kCGEventFlagsChanged, press_event, None)
    cg_callback(None, fake_q.kCGEventFlagsChanged, release_event, None)

    assert received == [
        RawMacKeyEvent(key_code=56, pressed=True, is_repeat=False),
        RawMacKeyEvent(key_code=56, pressed=False, is_repeat=False),
    ]


def test_quartz_backend_cg_callback_flagschanged_command_pressed():
    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    received = []
    backend.create_event_tap(lambda e: received.append(e) or KeyEventDecision.PASS_THROUGH)
    cg_callback = fake_q.taps_created[0][5]

    fake_event = {
        fake_q.kCGKeyboardEventKeycode: 55,
        "flags": fake_q.kCGEventFlagMaskCommand,
    }
    cg_callback(None, fake_q.kCGEventFlagsChanged, fake_event, None)

    assert received == [RawMacKeyEvent(key_code=55, pressed=True, is_repeat=False)]


def test_quartz_backend_cg_callback_flagschanged_capslock_pressed():
    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    received = []
    backend.create_event_tap(lambda e: received.append(e) or KeyEventDecision.PASS_THROUGH)
    cg_callback = fake_q.taps_created[0][5]

    fake_event = {
        fake_q.kCGKeyboardEventKeycode: 57,
        "flags": fake_q.kCGEventFlagMaskAlphaShift,
    }
    cg_callback(None, fake_q.kCGEventFlagsChanged, fake_event, None)

    assert received == [RawMacKeyEvent(key_code=57, pressed=True, is_repeat=False)]


def test_quartz_backend_enable_tap():
    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    tap = object()

    backend.enable_tap(tap, True)
    backend.enable_tap(tap, False)

    assert fake_q.enabled_calls == [(tap, True), (tap, False)]


def test_quartz_backend_run_loop_run_and_stop():
    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)

    backend.run_loop_run()
    assert fake_q.run_calls == 1

    backend.run_loop_stop()
    assert fake_q.stop_calls == 1
    assert fake_q.stopped_rls == ["CurrentRunLoop"]


def test_quartz_backend_release():
    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    obj = object()

    backend.release(obj)
    assert fake_q.released == [obj]


def test_quartz_backend_create_run_loop_source_and_add_source():
    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    tap = object()

    source = backend.create_run_loop_source(tap)
    assert source is fake_q.sources_created[0][0]
    _, allocator, tap_arg, order = fake_q.sources_created[0]
    assert allocator is None
    assert tap_arg is tap
    assert order == 0

    backend.add_source(source)
    assert len(fake_q.sources_added) == 1


def test_quartz_backend_create_event_tap_uses_correct_constants():
    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    backend.create_event_tap(lambda e: KeyEventDecision.PASS_THROUGH)

    _, location, place, options, mask, callback, user_data = fake_q.taps_created[0]

    assert location == fake_q.kCGSessionEventTap
    assert place == fake_q.kCGHeadInsertEventTap
    assert options == fake_q.kCGEventTapOptionDefault
    assert mask == (
        fake_q.CGEventMaskBit(fake_q.kCGEventKeyDown)
        | fake_q.CGEventMaskBit(fake_q.kCGEventKeyUp)
        | fake_q.CGEventMaskBit(fake_q.kCGEventFlagsChanged)
    )
    assert user_data is None


class NullTapQuartzModule(FakeQuartzModule):
    def CGEventTapCreate(self, location, place, options, mask, callback, user_data):
        FakeQuartzModule.CGEventTapCreate(self, location, place, options, mask, callback, user_data)
        return None


def test_quartz_backend_rejects_null_event_tap():
    fake_q = NullTapQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    with pytest.raises(RuntimeError, match="Failed to create Quartz event tap"):
        backend.create_event_tap(lambda e: KeyEventDecision.PASS_THROUGH)


def test_quartz_backend_run_loop_stop_uses_stored_run_loop():
    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)

    backend.run_loop_run()
    stored = backend._run_loop
    assert stored == "CurrentRunLoop"

    backend.run_loop_stop()
    assert fake_q.stopped_rls == ["CurrentRunLoop"]


def test_quartz_backend_run_loop_blocks_on_real_thread():
    import threading
    import time

    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)

    blocking = threading.Event()
    running = threading.Event()

    def thread_body():
        class RunLoop:
            pass
        fake_q.CFRunLoopGetCurrent = lambda: RunLoop()
        backend.run_loop_run()
        blocking.set()

    fake_q.CFRunLoopRun = lambda: (running.set(), blocking.wait())

    thread = threading.Thread(target=thread_body, daemon=True)
    thread.start()
    running.wait(timeout=5)

    assert backend._run_loop is not None
    assert not blocking.is_set()

    fake_q.CFRunLoopStop = lambda rl: blocking.set()
    backend.run_loop_stop()
    assert blocking.wait(timeout=5)
    thread.join(timeout=5)
    assert not thread.is_alive()


def test_quartz_backend_attach_and_run_signals_ready_after_bootstrap():
    import threading

    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    ready_event = threading.Event()
    backend.set_ready_event(ready_event)
    tap = object()

    blocking = threading.Event()

    def fake_run():
        blocking.wait()

    fake_q.CFRunLoopRun = fake_run

    thread = threading.Thread(target=backend.attach_and_run, args=(tap,), daemon=True)
    thread.start()
    assert ready_event.wait(timeout=5)
    assert backend.pop_startup_error() is None
    assert backend._source is not None

    # verify bootstrap happened
    assert len(fake_q.sources_created) == 1
    assert len(fake_q.sources_added) == 1
    assert len(fake_q.enabled_calls) == 1
    assert fake_q.enabled_calls[0] == (tap, True)

    # cleanup
    fake_q.CFRunLoopStop = lambda rl: blocking.set()
    backend.run_loop_stop()
    thread.join(timeout=5)
    assert not thread.is_alive()


def test_quartz_backend_attach_and_run_captures_bootstrap_error_and_cleans_source():
    import threading

    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    ready_event = threading.Event()
    backend.set_ready_event(ready_event)
    tap = object()

    original_cf_mach = fake_q.CFMachPortCreateRunLoopSource
    def failing_cf_mach(*args, **kwargs):
        result = original_cf_mach(*args, **kwargs)
        raise RuntimeError("Simulated CFMachPortCreateRunLoopSource failure")
    fake_q.CFMachPortCreateRunLoopSource = failing_cf_mach

    backend.attach_and_run(tap)

    assert ready_event.is_set()
    assert backend.pop_startup_error() is not None
    assert backend._source is None


def test_quartz_backend_attach_and_run_signals_ready_on_outer_exception():
    import threading

    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    ready_event = threading.Event()
    backend.set_ready_event(ready_event)
    tap = object()

    fake_q.CFRunLoopGetCurrent = lambda: (_ for _ in ()).throw(RuntimeError("Simulated CFRunLoopGetCurrent failure"))

    backend.attach_and_run(tap)

    assert ready_event.is_set()
    assert backend.pop_startup_error() is not None
    assert backend._source is None


def test_quartz_backend_attach_and_run_releases_source_on_source_add_failure():
    import threading

    fake_q = FakeQuartzModule()
    backend = QuartzEventTapBackend(quartz=fake_q)
    ready_event = threading.Event()
    backend.set_ready_event(ready_event)
    tap = object()

    original_add = fake_q.CFRunLoopAddSource
    def failing_add(*args, **kwargs):
        original_add(*args, **kwargs)
        raise RuntimeError("Simulated CFRunLoopAddSource failure")
    fake_q.CFRunLoopAddSource = failing_add

    backend.attach_and_run(tap)

    assert ready_event.is_set()
    assert backend.pop_startup_error() is not None
    assert backend._source is None
    assert len(fake_q.released) >= 1


def test_key_event_from_macos_maps_semicolon_quote_and_grave_to_hid():
    assert key_event_from_macos(key_code=41, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.SEMICOLON,
        pressed=True,
    )
    assert key_event_from_macos(key_code=39, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.QUOTE,
        pressed=True,
    )
    assert key_event_from_macos(key_code=50, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.GRAVE,
        pressed=True,
    )


def test_key_event_from_macos_maps_navigation_keys_to_hid():
    assert key_event_from_macos(key_code=114, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.INSERT,
        pressed=True,
    )
    assert key_event_from_macos(key_code=117, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.DELETE,
        pressed=True,
    )
    assert key_event_from_macos(key_code=121, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.PAGE_DOWN,
        pressed=True,
    )


def test_key_event_from_macos_distinguishes_numpad_keys_from_main_cluster_keys():
    assert key_event_from_macos(key_code=83, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.KEYPAD_1,
        pressed=True,
    )
    assert key_event_from_macos(key_code=75, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.KEYPAD_DIVIDE,
        pressed=True,
    )
    assert key_event_from_macos(key_code=65, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.KEYPAD_DECIMAL,
        pressed=True,
    )


def test_key_event_from_macos_maps_non_us_backslash_to_hid():
    assert key_event_from_macos(key_code=10, pressed=True, is_repeat=False) == KeyEvent(
        usage_page=HID.KEYBOARD_PAGE,
        usage=HID.NON_US_BACKSLASH,
        pressed=True,
    )
