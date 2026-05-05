# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import socket
from collections.abc import Callable

_DEFAULT_READ_MAX = 4096


def tcp_probe(
    host: str,
    port: int,
    *,
    send: bytes = b"",
    verify: Callable[[bytes], bool],
    timeout: float = 0.5,
    read_max: int = _DEFAULT_READ_MAX,
) -> bool:
    """Open a TCP connection, optionally send bytes, read up to ``read_max``,
    and apply the verifier.

    Returns True iff the connection succeeded and the verifier accepted the
    bytes received within the timeout. All socket errors yield False.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            if send:
                sock.sendall(send)
            chunks: list[bytes] = []
            remaining = read_max
            while remaining > 0:
                try:
                    chunk = sock.recv(min(4096, remaining))
                except socket.timeout:
                    break
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            buf = b"".join(chunks)
    except OSError:
        return False
    return bool(verify(buf))
