# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ssl
from hashlib import sha256
from struct import pack, unpack

from cryptography.x509.base import load_der_x509_certificate
from cryptography.x509.extensions import ExtensionNotFound
from cryptography.x509.oid import AuthorityInformationAccessOID, ExtensionOID

from datadog_checks.base import ConfigurationError, is_affirmative
from datadog_checks.base.log import get_check_logger
from datadog_checks.base.utils.time import get_timestamp

from .const import SERVICE_CHECK_CAN_CONNECT, SERVICE_CHECK_EXPIRATION, SERVICE_CHECK_VALIDATION
from .utils import closing


class TLSRemoteCheck(object):
    def __init__(self, agent_check):
        self.agent_check = agent_check
        self.log = get_check_logger()
        self.log.debug('Selecting remote connection for method of collection')
        self.agent_check._tags.append('server_hostname:{}'.format(self.agent_check._server_hostname))
        self.agent_check._tags.append('server:{}'.format(self.agent_check._server))
        self.agent_check._tags.append('port:{}'.format(self.agent_check._port))

        self._fetch_intermediate_certs = is_affirmative(
            self.agent_check.instance.get(
                'fetch_intermediate_certs', self.agent_check.init_config.get('fetch_intermediate_certs', False)
            )
        )
        self._intermediate_cert_refresh_interval = (
            # Convert minutes to seconds
            float(self.agent_check.instance.get('intermediate_cert_refresh_interval', 60))
            * 60
        )

    def check(self):
        if not self.agent_check._server:
            raise ConfigurationError('You must specify `server` in your configuration file.')

        if self._fetch_intermediate_certs:
            self.fetch_intermediate_certs()

        sock = self._get_connection()
        cert, protocol_version = self._get_cert_and_protocol_version(sock)

        self.agent_check.check_protocol_version(protocol_version)
        self.agent_check.validate_certificate(cert)
        self.agent_check.check_age(cert)

    def _get_cert_and_protocol_version(self, sock):
        cert = None
        protocol_version = None
        if sock is None:
            self.log.debug("Could not validate certificate because there is no connection")
            return cert, protocol_version
        # Get the cert & TLS version from the connection
        with closing(sock):
            self.log.debug('Getting cert and TLS protocol version')
            try:
                with closing(
                    self.agent_check.get_tls_context().wrap_socket(
                        sock, server_hostname=self.agent_check._server_hostname
                    )
                ) as secure_sock:
                    protocol_version = secure_sock.version()
                    der_cert = secure_sock.getpeercert(binary_form=True)
                    self.log.debug('Received serialized peer certificate and TLS protocol version %s', protocol_version)
            except Exception as e:
                # https://docs.python.org/3/library/ssl.html#ssl.SSLCertVerificationError
                err_code = getattr(e, 'verify_code', None)
                message = getattr(e, 'verify_message', str(e))
                self.log.debug('Error occurred while getting cert and TLS version from connection: %s', str(e))
                self.agent_check.service_check(
                    SERVICE_CHECK_VALIDATION, self.agent_check.CRITICAL, tags=self.agent_check._tags, message=message
                )

                # There's no sane way to tell it to not validate just the expiration
                # This only works on Python 3.7+, see: https://bugs.python.org/issue28182
                # https://github.com/openssl/openssl/blob/0b45d8eec051fd9816b6bf46a975fa461ffc983d/include/openssl/x509_vfy.h#L109
                if err_code == 10:
                    self.agent_check.service_check(
                        SERVICE_CHECK_EXPIRATION,
                        self.agent_check.CRITICAL,
                        tags=self.agent_check._tags,
                        message='Certificate has expired',
                    )
                self.log.debug('Returning cert %s and protocol version %s', cert, protocol_version)
                return cert, protocol_version

        # Load https://cryptography.io/en/latest/x509/reference/#cryptography.x509.Certificate
        try:
            self.log.debug('Deserializing peer certificate')
            cert = load_der_x509_certificate(der_cert)
            self.log.debug('Deserialized peer certificate: %s', cert)
            return cert, protocol_version
        except Exception as e:
            self.log.debug('Error while deserializing peer certificate: %s', str(e))
            self.agent_check.service_check(
                SERVICE_CHECK_VALIDATION,
                self.agent_check.CRITICAL,
                tags=self.agent_check._tags,
                message='Unable to parse the certificate: {}'.format(e),
            )
            self.log.debug('Returning cert %s and protocol version %s', cert, protocol_version)
            return cert, protocol_version

    def _get_connection(self):
        try:
            self.log.debug('Checking that TLS service check can connect')
            sock = self.agent_check.create_connection()
            if self.agent_check._start_tls:
                self._switch_starttls(sock)
        except Exception as e:
            self.log.debug('Error occurred while connecting to socket: %s', str(e))
            self.agent_check.service_check(
                SERVICE_CHECK_CAN_CONNECT, self.agent_check.CRITICAL, tags=self.agent_check._tags, message=str(e)
            )
            return
        else:
            self.log.debug('TLS check able to connect')
            self.agent_check.service_check(SERVICE_CHECK_CAN_CONNECT, self.agent_check.OK, tags=self.agent_check._tags)
        return sock

    def _switch_starttls(self, sock):
        protocol = self.agent_check._start_tls
        if protocol == "postgres":
            self.log.debug('Switching connection to encrypted for %s protocol', protocol)
            version_ssl = pack('!I', 1234 << 16 | 5679)
            length = pack('!I', 8)
            packet = length + version_ssl

            sock.sendall(packet)
            data = self._read_n_bytes_from_socket(sock, 1)
            if data != b'S':
                raise Exception('Postgres endpoint does not support TLS')
        elif protocol == "mysql":
            self.log.debug('Switching connection to encrypted for %s protocol', protocol)
            cap_protocol_41 = 1 << 9
            cap_ssl = 1 << 11
            cap_secure_connection = 1 << 15
            capabilities = cap_protocol_41 | cap_ssl | cap_secure_connection
            max_packet_len = 2**24 - 1
            charset_id = 8  # latin1
            # Form Protocol::SSLRequest packet
            data_init = pack("<iIB23s", capabilities, max_packet_len, charset_id, b"")
            # Form Mysql Protocol::Packet
            packet_len = pack("<I", len(data_init))[:3]
            packet_seq = pack("<B", 1)
            packet = packet_len + packet_seq + data_init
            # Read 4 bytes of header to get packet length
            packet_header = self._read_n_bytes_from_socket(sock, 4)
            btrl, btrh, packet_number = unpack("<HBB", packet_header)
            bytes_to_read = btrl + (btrh << 16)
            # Read Mysql welcome message
            data = self._read_n_bytes_from_socket(sock, bytes_to_read)
            sock.sendall(packet)
        else:
            raise Exception('Unsupported starttls protocol: ' + protocol)

    def _read_n_bytes_from_socket(self, sock, n):
        buf = bytearray(n)
        view = memoryview(buf)
        while n:
            nbytes = sock.recv_into(view, n)
            view = view[nbytes:]  # slicing views is cheap
            n -= nbytes
        return buf

    def fetch_intermediate_certs(self):
        # TODO: prefer stdlib implementation when available, see https://bugs.python.org/issue18617
        try:
            sock = self.agent_check.create_connection()
            if self.agent_check._start_tls:
                self._switch_starttls(sock)
        except Exception as e:
            self.log.error('Error occurred while connecting to socket to discover intermediate certificates: %s', e)
            return

        with closing(sock):
            try:
                context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)
                context.verify_mode = ssl.CERT_NONE

                with closing(
                    context.wrap_socket(sock, server_hostname=self.agent_check._server_hostname)
                ) as secure_sock:
                    der_cert = secure_sock.getpeercert(binary_form=True)
                    protocol_version = secure_sock.version()
                    if protocol_version and protocol_version not in self.agent_check.allowed_versions:
                        self.log.warning(
                            'Protocol version not allowed for intermediate certificates: %s', protocol_version
                        )
            except Exception as e:
                self.log.error('Error occurred while getting cert to discover intermediate certificates: %s', e)
                return

        self.load_intermediate_certs(der_cert)

    def load_intermediate_certs(self, der_cert):
        # https://tools.ietf.org/html/rfc3280#section-4.2.2.1
        # https://tools.ietf.org/html/rfc5280#section-5.2.7
        try:
            cert = load_der_x509_certificate(der_cert)
        except Exception as e:
            self.log.error('Error while deserializing peer certificate to discover intermediate certificates: %s', e)
            return

        try:
            authority_information_access = cert.extensions.get_extension_for_oid(
                ExtensionOID.AUTHORITY_INFORMATION_ACCESS
            )
        except ExtensionNotFound:
            self.log.debug(
                'No Authority Information Access extension found, skipping discovery of intermediate certificates'
            )
            return

        for access_description in authority_information_access.value:
            if access_description.access_method != AuthorityInformationAccessOID.CA_ISSUERS:
                continue

            uri = access_description.access_location.value
            if (
                uri in self.agent_check._intermediate_cert_uri_cache
                and get_timestamp() - self.agent_check._intermediate_cert_uri_cache[uri]
                < self._intermediate_cert_refresh_interval
            ):
                continue

            # Assume HTTP for now
            try:
                response = self.agent_check.http.get(uri)  # SKIP_HTTP_VALIDATION
                response.raise_for_status()
            except Exception as e:
                self.log.error('Error fetching intermediate certificate from `%s`: %s', uri, e)
                continue
            else:
                access_time = get_timestamp()
                intermediate_cert = response.content

            cert_id = sha256(intermediate_cert).digest()
            if cert_id not in self.agent_check._intermediate_cert_id_cache:
                self.agent_check.get_tls_context().load_verify_locations(cadata=intermediate_cert)
                self.agent_check._intermediate_cert_id_cache.add(cert_id)

            self.agent_check._intermediate_cert_uri_cache[uri] = access_time
            self.load_intermediate_certs(intermediate_cert)
