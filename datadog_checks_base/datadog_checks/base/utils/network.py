import socket
import ssl

from requests.adapters import HTTPAdapter, PoolManager
from six import PY2

if PY2:
    from contextlib import closing as _closing

    def closing(sock):
        return _closing(sock)


else:

    def closing(sock):
        return sock


def create_socket_connection(hostname, port=443, sock_type=socket.SOCK_STREAM, timeout=10):
    """See: https://github.com/python/cpython/blob/40ee9a3640d702bce127e9877c82a99ce817f0d1/Lib/socket.py#L691"""
    err = None
    try:
        for res in socket.getaddrinfo(hostname, port, 0, sock_type):
            af, socktype, proto, canonname, sa = res
            sock = None
            try:
                sock = socket.socket(af, socktype, proto)
                sock.settimeout(timeout)
                sock.connect(sa)
                # Break explicitly a reference cycle
                err = None
                return sock

            except socket.error as _:
                err = _
                if sock is not None:
                    sock.close()

        if err is not None:
            raise err
        else:
            raise socket.error('No valid addresses found, try checking your IPv6 connectivity')  # noqa: G
    except socket.gaierror as e:
        err_code, message = e.args
        if err_code == socket.EAI_NODATA or err_code == socket.EAI_NONAME:
            raise socket.error('Unable to resolve host, check your DNS: {}'.format(message))  # noqa: G

        raise


class CertAdapter(HTTPAdapter):
    def __init__(self, **kwargs):
        self.certs = kwargs['certs']
        super(CertAdapter, self).__init__()

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        context = ssl.create_default_context()
        for cert in self.certs:
            context.load_verify_locations(cadata=cert)
        pool_kwargs['ssl_context'] = context
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, block=block, strict=True, **pool_kwargs)
