import os  # noqa: F401
from contextlib import contextmanager

from datadog_checks.dev import run_command  # noqa: F401


@contextmanager
def mock_local(src_to_dest_mapping):
    """
    Mock 'socket' to resolve hostname based on a provided mapping.
    This method has no effect for e2e tests.
    :param src_to_dest_mapping: Mapping from source hostname to a tuple of destination hostname and port.
        If port is None or evaluates to False, then only the host will be overridden and not the port.
    """
    import socket

    _orig_getaddrinfo = socket.getaddrinfo
    _orig_connect = socket.socket.connect

    def patched_getaddrinfo(host, port, *args, **kwargs):
        if host in src_to_dest_mapping:
            # See socket.getaddrinfo, just updating the hostname here.
            # https://docs.python.org/3/library/socket.html#socket.getaddrinfo
            dest_addr, dest_port = src_to_dest_mapping[host]
            new_port = dest_port or port
            return [(2, 1, 6, '', (dest_addr, new_port))]

        return _orig_getaddrinfo(host, port, *args, **kwargs)

    def patched_connect(self, address):
        host, port = address[0], address[1]
        if host in src_to_dest_mapping:
            dest_addr, dest_port = src_to_dest_mapping[host]
            host, port = dest_addr, dest_port

        return _orig_connect(self, (host, port))

    socket.getaddrinfo = patched_getaddrinfo
    socket.socket.connect = patched_connect
    try:
        yield
    except Exception:
        raise
    finally:
        socket.getaddrinfo = _orig_getaddrinfo
        socket.socket.connect = _orig_connect
