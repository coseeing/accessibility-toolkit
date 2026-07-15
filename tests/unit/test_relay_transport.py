import socket
import threading
import time

from accessibility_toolkit.remote.serializer import JSONSerializer
from accessibility_toolkit.remote.transport import RelayTransport


class TrackedSocket:
    def __init__(self, sock):
        self.sock = sock
        self.recv_started = threading.Event()
        self.partial_received = threading.Event()

    def recv(self, size):
        self.recv_started.set()
        data = self.sock.recv(size)
        if data == b'{"type":"old':
            self.partial_received.set()
        return data

    def sendall(self, data):
        self.sock.sendall(data)

    def shutdown(self, how):
        self.sock.shutdown(how)

    def close(self):
        self.sock.close()


def test_replacement_reader_owns_socket_and_partial_buffer():
    old_client, old_server = socket.socketpair()
    new_client, new_server = socket.socketpair()
    old_socket = TrackedSocket(old_client)
    new_socket = TrackedSocket(new_client)
    sockets = iter((old_socket, new_socket))
    messages = []
    transport = RelayTransport(
        serializer=JSONSerializer(),
        socket_factory=lambda _host, _port: next(sockets),
        use_tls=False,
    )
    transport.set_message_handler(messages.append)

    try:
        transport.connect("old.example", 6837)
        transport.start_reader()
        assert old_socket.recv_started.wait(timeout=1)
        old_server.sendall(b'{"type":"old')
        assert old_socket.partial_received.wait(timeout=1)
        old_reader = transport._reader_thread

        transport.stop_reader()
        transport.connect("new.example", 6837)
        transport.start_reader()
        assert new_socket.recv_started.wait(timeout=1)

        new_server.sendall(b'{"type":"new"}\n')
        old_server.close()
        deadline = time.monotonic() + 2
        while old_reader.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)

        assert messages == [{"type": "new"}]
        assert transport.connected is True
    finally:
        transport.stop_reader()
        transport.close()
        old_server.close()
        new_server.close()
