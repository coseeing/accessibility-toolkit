import threading

from accessibility_toolkit.remote.serializer import JSONSerializer
from accessibility_toolkit.remote.transport import RelayTransport


def test_replacement_reader_cannot_publish_delayed_old_disconnect():
    transport = RelayTransport(serializer=JSONSerializer())
    first_reader_started = threading.Event()
    release_first_reader = threading.Event()
    replacement_reader_blocked = threading.Event()
    release_replacement_reader = threading.Event()
    receive_calls = 0
    receive_lock = threading.Lock()
    messages = []

    def receive_once():
        nonlocal receive_calls
        with receive_lock:
            receive_calls += 1
            call_number = receive_calls
        if call_number == 1:
            first_reader_started.set()
            release_first_reader.wait(timeout=2)
        if call_number == 2:
            return {"type": "replacement_reader_message"}
        replacement_reader_blocked.set()
        release_replacement_reader.wait(timeout=2)
        raise ConnectionError("delayed close")

    transport.receive_once = receive_once
    transport.set_message_handler(messages.append)
    transport.start_reader()
    assert first_reader_started.wait(timeout=1)
    old_reader = transport._reader_thread

    transport.stop_reader()
    transport.start_reader()
    assert replacement_reader_blocked.wait(timeout=1)
    transport.stop_reader()
    release_first_reader.set()
    release_replacement_reader.set()
    old_reader.join(timeout=2)

    assert messages == [{"type": "replacement_reader_message"}]
