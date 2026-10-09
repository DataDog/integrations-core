# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Bespoke evalya workload for rabbitmq.connection.pending_packets.

The gauge reports bytes the broker has queued on a connection's socket but not
yet handed to the kernel, which is non-zero only while the client reads slower
than the broker delivers. Every off-the-shelf client drains its socket as fast
as it can, so this one reads its consumer socket at a fixed, low byte rate
through a small receive buffer, while a second connection publishes faster than
that. The kernel buffers stay full and the broker's send queue never empties.

It throttles rather than stops reading: RabbitMQ (through ranch) closes a
connection whose socket send blocks for 30s, so a client that never reads
only shows pending bytes for about 30s per connection.

Stdlib only: a minimal AMQP 0-9-1 client, just enough frames for a PLAIN login,
a queue declare, an auto-ack consume, and publishes.

Bounded: auto-ack leaves nothing unacked, x-max-length caps the queue (the
publisher outpaces the reader, so it stays full and drops from the head), the
publish and read rates are fixed, and the consumer reconnects periodically.
"""

import os
import socket
import struct
import threading
import time
from collections.abc import Callable

FRAME_METHOD, FRAME_HEADER, FRAME_BODY = 1, 2, 3
FRAME_END = b'\xce'

HOST = os.environ.get('RABBITMQ_HOST', 'rabbitmq-broker')
PORT = int(os.environ.get('RABBITMQ_AMQP_PORT', '5672'))
USER = os.environ.get('RABBITMQ_USER', 'guest')
PASSWORD = os.environ.get('RABBITMQ_PASSWORD', 'guest')

QUEUE = 'slow-reader'
MAX_LENGTH = 1000
MESSAGE_BYTES = 1024
PUBLISH_PER_SECOND = 100  # ~100 KiB/s in
READ_BYTES_PER_SECOND = 32 * 1024  # ~32 KiB/s out, so the backlog never drains
RECV_BUFFER = 4096
RECONNECT_SECONDS = 600


def log(msg: str) -> None:
    print(f'slow-reader: {msg}', flush=True)


def shortstr(value: str) -> bytes:
    data = value.encode()
    return struct.pack('>B', len(data)) + data


def longstr(value: bytes) -> bytes:
    return struct.pack('>I', len(value)) + value


def table(entries: dict[str, int]) -> bytes:
    # Only signed 32-bit integer values ('I') are needed here.
    body = b''.join(shortstr(k) + b'I' + struct.pack('>i', v) for k, v in entries.items())
    return struct.pack('>I', len(body)) + body


def frame(frame_type: int, channel: int, payload: bytes) -> bytes:
    return struct.pack('>BHI', frame_type, channel, len(payload)) + payload + FRAME_END


def method(channel: int, class_id: int, method_id: int, args: bytes = b'') -> bytes:
    return frame(FRAME_METHOD, channel, struct.pack('>HH', class_id, method_id) + args)


def recv_exact(sock: socket.socket, size: int) -> bytes:
    data = b''
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError('broker closed the connection')
        data += chunk
    return data


def expect(sock: socket.socket, class_id: int, method_id: int) -> bytes:
    """Read frames until the given method arrives and return its arguments."""
    while True:
        frame_type, _, size = struct.unpack('>BHI', recv_exact(sock, 7))
        payload = recv_exact(sock, size + 1)[:-1]
        if frame_type != FRAME_METHOD:
            continue
        got = struct.unpack('>HH', payload[:4])
        if got in ((10, 50), (20, 40)):  # connection.close, channel.close
            raise ConnectionError(f'broker closed with {payload[4:]!r}')
        if got == (class_id, method_id):
            return payload[4:]


def connect(rcvbuf: int | None = None) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if rcvbuf:
        # Before connect, so the advertised TCP window starts small.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, rcvbuf)
    sock.settimeout(30)
    sock.connect((HOST, PORT))
    sock.sendall(b'AMQP\x00\x00\x09\x01')
    expect(sock, 10, 10)  # connection.start
    login = b'\x00' + USER.encode() + b'\x00' + PASSWORD.encode()
    sock.sendall(method(0, 10, 11, table({}) + shortstr('PLAIN') + longstr(login) + shortstr('en_US')))
    channel_max, frame_max, _ = struct.unpack('>HIH', expect(sock, 10, 30)[:8])
    # Heartbeats off: the reader lags by design and the publisher never reads.
    sock.sendall(method(0, 10, 31, struct.pack('>HIH', channel_max, frame_max, 0)))
    sock.sendall(method(0, 10, 40, shortstr('/') + shortstr('') + b'\x00'))
    expect(sock, 10, 41)
    sock.sendall(method(1, 20, 10, shortstr('')))
    expect(sock, 20, 11)
    declare = struct.pack('>H', 0) + shortstr(QUEUE) + b'\x00' + table({'x-max-length': MAX_LENGTH})
    sock.sendall(method(1, 50, 10, declare))
    expect(sock, 50, 11)
    return sock


def publish_forever() -> None:
    sock = connect()
    body = b'x' * MESSAGE_BYTES
    content = (
        method(1, 60, 40, struct.pack('>H', 0) + shortstr('') + shortstr(QUEUE) + b'\x00')
        + frame(FRAME_HEADER, 1, struct.pack('>HHQH', 60, 0, len(body), 0))
        + frame(FRAME_BODY, 1, body)
    )
    # Blocks on TCP back-pressure while a broker alarm is active.
    sock.settimeout(None)
    while True:
        sock.sendall(content)
        time.sleep(1 / PUBLISH_PER_SECOND)


def read_slowly() -> None:
    sock = connect(rcvbuf=RECV_BUFFER)
    no_ack = 0b10
    consume = struct.pack('>H', 0) + shortstr(QUEUE) + shortstr('') + struct.pack('>B', no_ack) + table({})
    sock.sendall(method(1, 60, 20, consume))
    expect(sock, 60, 21)
    log(f'consuming {QUEUE} at {READ_BYTES_PER_SECOND} B/s for {RECONNECT_SECONDS}s')
    deadline = time.monotonic() + RECONNECT_SECONDS
    try:
        while time.monotonic() < deadline:
            if not sock.recv(RECV_BUFFER):
                raise ConnectionError('broker closed the connection')
            time.sleep(RECV_BUFFER / READ_BYTES_PER_SECOND)
    finally:
        sock.close()


def retry_forever(name: str, run: Callable[[], None]) -> None:
    while True:
        try:
            run()
        except (OSError, ConnectionError) as e:
            log(f'{name}: {e}; retrying in 5s')
            time.sleep(5)


def main() -> None:
    if os.environ.get('ACTIVITY_GEN', '1') == '0':
        log('disabled via ACTIVITY_GEN=0; idling')
        while True:
            time.sleep(3600)
    log(f'publishing {MESSAGE_BYTES}B messages to {QUEUE} at {PUBLISH_PER_SECOND}/s')
    threading.Thread(target=retry_forever, args=('publisher', publish_forever), daemon=True).start()
    retry_forever('consumer', read_slowly)


if __name__ == '__main__':
    main()
