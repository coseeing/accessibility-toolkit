import socket
import ssl
import threading
import logging
from collections.abc import Callable
from enum import Enum
from typing import Any

from remote_core.serializer import JSONSerializer


logger = logging.getLogger(__name__)


class RelayTransport:
    def __init__(
        self,
        serializer: JSONSerializer,
        socket_factory: Callable[[str, int], socket.socket] | None = None,
        ssl_context_factory: Callable[[], ssl.SSLContext] | None = None,
        use_tls: bool = True,
    ) -> None:
        self.serializer = serializer
        self.connected = False
        self.connected_to: tuple[str, int, bool] | None = None
        self._socket_factory = socket_factory or self._create_connection
        self._ssl_context_factory = ssl_context_factory or ssl.create_default_context
        self._use_tls = use_tls
        self._socket: socket.socket | None = None
        self._recv_buffer = b""
        self._message_handler: Callable[[dict[str, Any]], None] | None = None
        self._reader_thread: threading.Thread | None = None
        self._reader_stop = threading.Event()
        self.sent: list[bytes] = []

    def connect(self, hostname: str, port: int, insecure: bool = False) -> None:
        raw_socket = self._socket_factory(hostname, port)
        if self._use_tls:
            context = self._ssl_context_factory()
            if insecure:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            raw_socket = context.wrap_socket(
                raw_socket,
                server_hostname=hostname,
            )
        self._socket = raw_socket
        self.connected = True
        self.connected_to = (hostname, port, insecure)

    def close(self) -> None:
        self._reader_stop.set()
        sock = self._socket
        self._socket = None
        self.connected = False
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        if (
            self._reader_thread is not None
            and self._reader_thread is not threading.current_thread()
        ):
            self._reader_thread.join(timeout=1)
        self._reader_thread = None

    def send(self, message_type: str | Enum, **payload: Any) -> None:
        if not self.connected or self._socket is None:
            raise RuntimeError("Transport is not connected")
        data = self.serializer.serialize(message_type, **payload)
        self._socket.sendall(data)
        self.sent.append(data)

    def receive_once(self) -> dict[str, Any]:
        if not self.connected or self._socket is None:
            raise RuntimeError("Transport is not connected")

        while True:
            if self.serializer.SEP in self._recv_buffer:
                frame, self._recv_buffer = self._recv_buffer.split(
                    self.serializer.SEP,
                    1,
                )
                if not frame:
                    continue
                logger.debug("Relay transport received frame: %r", frame)
                payload = self.serializer.deserialize(frame)
                logger.debug("Relay transport decoded payload type=%r", payload.get("type"))
                return payload

            chunk = self._socket.recv(4096)
            if chunk == b"":
                self.connected = False
                raise ConnectionError("Relay connection closed")
            self._recv_buffer += chunk

    def set_message_handler(
        self,
        callback: Callable[[dict[str, Any]], None] | None,
    ) -> None:
        self._message_handler = callback

    def start_reader(self) -> None:
        if self._message_handler is None:
            raise RuntimeError("Message handler is not set")
        if self._reader_thread is not None and self._reader_thread.is_alive():
            return
        self._reader_stop.clear()
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

    def stop_reader(self) -> None:
        self._reader_stop.set()
        if (
            self._reader_thread is not None
            and self._reader_thread is not threading.current_thread()
        ):
            self._reader_thread.join(timeout=1)
        self._reader_thread = None

    def _read_loop(self) -> None:
        while not self._reader_stop.is_set():
            try:
                payload = self.receive_once()
            except (ConnectionError, OSError, RuntimeError):
                break
            if self._message_handler is not None:
                self._message_handler(payload)

    @staticmethod
    def _create_connection(hostname: str, port: int) -> socket.socket:
        return socket.create_connection((hostname, port))
