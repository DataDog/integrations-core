import os
from contextlib import contextmanager

from datadog_checks.dev import run_command


@contextmanager
def mock_socket(src_to_dest_mapping):
    """
    :param src_to_dest_mapping: Mapping from source hostname to a tuple of destination hostname and port
    """
    import socket
    _orig_getaddrinfo = socket.getaddrinfo
    _orig_connect = socket.socket.connect

    def patched_getaddrinfo(host, *args, **kwargs):
        if host in src_to_dest_mapping:
            # See socket.getaddrinfo, just updating the hostname here.
            # https://docs.python.org/3/library/socket.html#socket.getaddrinfo
            dest_addr, dest_port = src_to_dest_mapping[host]
            return [(2, 1, 6, '', (dest_addr, dest_port))]

        return _orig_getaddrinfo(host, *args, **kwargs)

    def patched_connect(self, address):
        host, port = address[0], address[1]
        if host in src_to_dest_mapping:
            dest_addr, dest_port = src_to_dest_mapping[host]
            host, port = dest_addr, dest_port

        return _orig_connect(self, (host, port))

    socket.getaddrinfo = patched_getaddrinfo
    socket.socket.connect = patched_connect
    yield
    socket.getaddrinfo = _orig_getaddrinfo
    socket.socket.connect = _orig_connect


@contextmanager
def mock_e2e_agent(check_name, hosts):
    """Only for e2e testing"""
    container_id = "dd_{}_{}".format(check_name, os.environ["TOX_ENV_NAME"])
    commands = []
    for host in hosts:
        commands.append(r'bash -c "printf \"127.0.0.1 {}\n\" >> /etc/hosts"'.format(host))

    for command in commands:
        run_command('docker exec {} {}'.format(container_id, command))

    yield

    commands = ['cp /etc/hosts /hosts.new']
    for host in hosts:
        commands.append(r'bash -c "sed -i \"/127.0.0.1 {}/d\" /hosts.new"'.format(host))
    commands.append('cp -f /hosts.new /etc/hosts')
    for command in commands:
        run_command('docker exec {} {}'.format(container_id, command))
