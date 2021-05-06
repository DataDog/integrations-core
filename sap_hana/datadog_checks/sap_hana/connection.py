import socket

from pyhdb.connection import INITIALIZATION_BYTES, Connection, version_struct


class HanaConnection(Connection):
    def __init__(self, host, port, user, password, tls_context=None, autocommit=False, timeout=None):
        super(HanaConnection, self).__init__(host, port, user, password, autocommit, timeout)
        self.tls_context = tls_context

    def _open_socket_and_init_protocoll(self):
        """Overrides this method from pyhdb to add SSL support.
        Original implementation here can be found here:
        https://github.com/SAP/PyHDB/blob/v0.3.4/pyhdb/connection.py#L65"""

        # Create socket
        self._socket = socket.create_connection((self.host, self.port), self._timeout)

        # Wrap socket if tls_context is set
        if self.tls_context:
            self._socket = self.tls_context.wrap_socket(self._socket, server_hostname=self.host)

        # Initialization Handshake
        self._socket.sendall(INITIALIZATION_BYTES)

        response = self._socket.recv(8)
        if len(response) != 8:
            raise Exception("Connection failed")

        self.product_version = version_struct.unpack(response[0:3])
        self.protocol_version = version_struct.unpack_from(response[3:8])
