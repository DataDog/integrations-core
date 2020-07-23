# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import socket
import ssl
from datetime import datetime
from os.path import expanduser, isdir

import service_identity
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_der_x509_certificate, load_pem_x509_certificate
from six import text_type
from six.moves.urllib.parse import urlparse

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative

from .utils import closing, days_to_seconds, get_protocol_versions, is_ip_address, seconds_to_days

# Python 3 only
PROTOCOL_TLS_CLIENT = getattr(ssl, 'PROTOCOL_TLS_CLIENT', ssl.PROTOCOL_TLS)


class TLSCheck(AgentCheck):
    SERVICE_CHECK_CAN_CONNECT = 'tls.can_connect'
    SERVICE_CHECK_VERSION = 'tls.version'
    SERVICE_CHECK_VALIDATION = 'tls.cert_validation'
    SERVICE_CHECK_EXPIRATION = 'tls.cert_expiration'

    DEFAULT_EXPIRE_DAYS_WARNING = 14
    DEFAULT_EXPIRE_DAYS_CRITICAL = 7
    DEFAULT_EXPIRE_SECONDS_WARNING = days_to_seconds(DEFAULT_EXPIRE_DAYS_WARNING)
    DEFAULT_EXPIRE_SECONDS_CRITICAL = days_to_seconds(DEFAULT_EXPIRE_DAYS_CRITICAL)

    def __init__(self, name, init_config, instances):
        super(TLSCheck, self).__init__(name, init_config, instances)

        self._name = self.instance.get('name')
        self._local_cert_path = self.instance.get('local_cert_path', '')
        self._timeout = float(self.instance.get('timeout', 10))

        server = self.instance.get('server', '')
        parsed_uri = urlparse(server)

        # Handle IP addresses, see: https://bugs.python.org/issue754016
        if not parsed_uri.hostname:
            parsed_uri = urlparse('//{}'.format(server))

        self._server = parsed_uri.hostname

        # TODO: Support (implement) UDP
        # https://chris-wood.github.io/2016/05/06/OpenSSL-DTLS.html
        transport = self.instance.get('transport', 'tcp').lower()
        if transport == 'udp':
            # SOCK_DGRAM
            self._sock_type = socket.SOCK_STREAM
            # Default to 4433 (no standard port, but it's what OpenSSL uses)
            self._port = int(self.instance.get('port', parsed_uri.port or 443))
        else:
            self._sock_type = socket.SOCK_STREAM
            self._port = int(self.instance.get('port', parsed_uri.port or 443))

        self._validate_cert = is_affirmative(self.instance.get('validate_cert', True))

        # https://en.wikipedia.org/wiki/Server_Name_Indication
        self._server_hostname = self.instance.get('server_hostname', self._server)
        self._validate_hostname = is_affirmative(self.instance.get('validate_hostname', True))

        self._cert = self.instance.get('cert')
        if self._cert:
            self._cert = expanduser(self._cert)

        self._private_key = self.instance.get('private_key')
        if self._private_key:
            self._private_key = expanduser(self._private_key)

        self._cafile = None
        self._capath = None
        ca_cert = self.instance.get('ca_cert')
        if ca_cert:
            ca_cert = expanduser(ca_cert)
            if isdir(ca_cert):
                self._capath = ca_cert
            else:
                self._cafile = ca_cert

        # Thresholds expressed in seconds take precedence over those expressed in days
        self._seconds_warning = (
            int(self.instance.get('seconds_warning', 0))
            or days_to_seconds(float(self.instance.get('days_warning', 0)))
            or self.DEFAULT_EXPIRE_SECONDS_WARNING
        )
        self._seconds_critical = (
            int(self.instance.get('seconds_critical', 0))
            or days_to_seconds(float(self.instance.get('days_critical', 0)))
            or self.DEFAULT_EXPIRE_SECONDS_CRITICAL
        )

        # https://docs.python.org/3/library/ssl.html#ssl.SSLSocket.version
        self._allowed_versions = get_protocol_versions(
            self.instance.get('allowed_versions', self.init_config.get('allowed_versions', []))
        )

        # Global tags
        self._tags = self.instance.get('tags', [])
        if self._name:
            self._tags.append('name:{}'.format(self._name))

        # Decide the method of collection for this instance (local file vs remote connection)
        if self._local_cert_path:
            self.check = self.check_local
            if self._validate_hostname and self._server_hostname:
                self._tags.append('server_hostname:{}'.format(self._server_hostname))
        else:
            self.check = self.check_remote
            self._tags.append('server_hostname:{}'.format(self._server_hostname))
            self._tags.append('server:{}'.format(self._server))
            self._tags.append('port:{}'.format(self._port))

        # Assign lazily since these aren't used by both collection methods
        self._validation_data = None
        self._tls_context = None

    def check_remote(self, instance):
        if not self._server:
            raise ConfigurationError('You must specify `server` in your configuration file.')

        try:
            sock = self.create_connection()
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_CAN_CONNECT, self.CRITICAL, tags=self._tags, message=str(e))
            return
        else:
            self.service_check(self.SERVICE_CHECK_CAN_CONNECT, self.OK, tags=self._tags)

        # Get the cert & TLS version from the connection
        with closing(sock):
            try:
                with closing(self.tls_context.wrap_socket(sock, server_hostname=self._server_hostname)) as secure_sock:
                    der_cert = secure_sock.getpeercert(binary_form=True)
                    protocol_version = secure_sock.version()
            except Exception as e:
                # https://docs.python.org/3/library/ssl.html#ssl.SSLCertVerificationError
                err_code = getattr(e, 'verify_code', None)
                message = getattr(e, 'verify_message', str(e))
                self.service_check(self.SERVICE_CHECK_VALIDATION, self.CRITICAL, tags=self._tags, message=message)

                # There's no sane way to tell it to not validate just the expiration
                # This only works on Python 3.7+, see: https://bugs.python.org/issue28182
                # https://github.com/openssl/openssl/blob/0b45d8eec051fd9816b6bf46a975fa461ffc983d/include/openssl/x509_vfy.h#L109
                if err_code == 10:
                    self.service_check(
                        self.SERVICE_CHECK_EXPIRATION, self.CRITICAL, tags=self._tags, message='Certificate has expired'
                    )

                return

        # Load https://cryptography.io/en/latest/x509/reference/#cryptography.x509.Certificate
        try:
            cert = load_der_x509_certificate(der_cert, default_backend())
        except Exception as e:
            self.service_check(
                self.SERVICE_CHECK_VALIDATION,
                self.CRITICAL,
                tags=self._tags,
                message='Unable to parse the certificate: {}'.format(e),
            )
            return

        self.check_protocol_version(protocol_version)
        self.validate_certificate(cert)
        self.check_age(cert)

    def check_local(self, instance):
        if self._validate_hostname and not self._server_hostname:
            raise ConfigurationError(
                'You must specify `server_hostname` in your configuration file, or disable `validate_hostname`.'
            )

        try:
            with open(self._local_cert_path, 'rb') as f:
                cert = f.read()
        except Exception as e:
            self.service_check(
                self.SERVICE_CHECK_VALIDATION,
                self.CRITICAL,
                tags=self._tags,
                message='Unable to open the certificate: {}'.format(e),
            )
            return

        # Load https://cryptography.io/en/latest/x509/reference/#cryptography.x509.Certificate
        try:
            cert = self.local_cert_loader(cert)
        except Exception as e:
            self.service_check(
                self.SERVICE_CHECK_VALIDATION,
                self.CRITICAL,
                tags=self._tags,
                message='Unable to parse the certificate: {}'.format(e),
            )
            return

        self.validate_certificate(cert)
        self.check_age(cert)

    def check_protocol_version(self, version):
        if version in self._allowed_versions:
            self.service_check(self.SERVICE_CHECK_VERSION, self.OK, tags=self._tags)
        else:
            self.service_check(
                self.SERVICE_CHECK_VERSION,
                self.CRITICAL,
                tags=self._tags,
                message='Disallowed protocol version: {}'.format(version),
            )

    def validate_certificate(self, cert):
        if self._validate_hostname:
            validator, host_type = self.validation_data

            try:
                validator(cert, text_type(self._server_hostname))
            except service_identity.VerificationError:
                self.service_check(
                    self.SERVICE_CHECK_VALIDATION,
                    self.CRITICAL,
                    tags=self._tags,
                    message='The {} on the certificate does not match the given host'.format(host_type),
                )
                return
            except service_identity.CertificateError as e:  # no cov
                self.service_check(
                    self.SERVICE_CHECK_VALIDATION,
                    self.CRITICAL,
                    tags=self._tags,
                    message='The certificate contains invalid/unexpected data: {}'.format(e),
                )
                return

        self.service_check(self.SERVICE_CHECK_VALIDATION, self.OK, tags=self._tags)

    def check_age(self, cert):
        delta = cert.not_valid_after - datetime.utcnow()
        seconds_left = delta.total_seconds()
        days_left = seconds_to_days(seconds_left)

        self.gauge('tls.days_left', days_left, tags=self._tags)
        self.gauge('tls.seconds_left', seconds_left, tags=self._tags)

        if seconds_left <= 0:
            self.service_check(
                self.SERVICE_CHECK_EXPIRATION, self.CRITICAL, tags=self._tags, message='Certificate has expired'
            )
        elif seconds_left < self._seconds_critical:
            self.service_check(
                self.SERVICE_CHECK_EXPIRATION,
                self.CRITICAL,
                tags=self._tags,
                message='Certificate will expire in only {} days'.format(days_left),
            )
        elif seconds_left < self._seconds_warning:
            self.service_check(
                self.SERVICE_CHECK_EXPIRATION,
                self.WARNING,
                tags=self._tags,
                message='Certificate will expire in {} days'.format(days_left),
            )
        else:
            self.service_check(self.SERVICE_CHECK_EXPIRATION, self.OK, tags=self._tags)

    def create_connection(self):
        """See: https://github.com/python/cpython/blob/40ee9a3640d702bce127e9877c82a99ce817f0d1/Lib/socket.py#L691"""
        err = None
        try:
            for res in socket.getaddrinfo(self._server, self._port, 0, self._sock_type):
                af, socktype, proto, canonname, sa = res
                sock = None
                try:
                    sock = socket.socket(af, socktype, proto)
                    sock.settimeout(self._timeout)
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

    @property
    def validation_data(self):
        if self._validation_data is None:
            if is_ip_address(self._server_hostname):
                self._validation_data = (service_identity.cryptography.verify_certificate_ip_address, 'IP address')
            else:
                self._validation_data = (service_identity.cryptography.verify_certificate_hostname, 'hostname')

        return self._validation_data

    def local_cert_loader(self, cert):
        backend = default_backend()
        if b'-----BEGIN CERTIFICATE-----' in cert:
            return load_pem_x509_certificate(cert, backend)
        return load_der_x509_certificate(cert, backend)

    @property
    def tls_context(self):
        if self._tls_context is None:
            # https://docs.python.org/3/library/ssl.html#ssl.SSLContext
            # https://docs.python.org/3/library/ssl.html#ssl.PROTOCOL_TLS
            self._tls_context = ssl.SSLContext(protocol=PROTOCOL_TLS_CLIENT)

            # Run our own validation later on if need be
            # https://docs.python.org/3/library/ssl.html#ssl.SSLContext.check_hostname
            #
            # IMPORTANT: This must be set before verify_mode in Python 3.7+, see:
            # https://docs.python.org/3/library/ssl.html#ssl.SSLContext.check_hostname
            self._tls_context.check_hostname = False

            # https://docs.python.org/3/library/ssl.html#ssl.SSLContext.verify_mode
            self._tls_context.verify_mode = ssl.CERT_REQUIRED if self._validate_cert else ssl.CERT_NONE

            # https://docs.python.org/3/library/ssl.html#ssl.SSLContext.load_verify_locations
            if self._cafile or self._capath:  # no cov
                self._tls_context.load_verify_locations(self._cafile, self._capath, None)

            # https://docs.python.org/3/library/ssl.html#ssl.SSLContext.load_default_certs
            else:
                self._tls_context.load_default_certs(ssl.Purpose.SERVER_AUTH)

            # https://docs.python.org/3/library/ssl.html#ssl.SSLContext.load_cert_chain
            if self._cert:  # no cov
                self._tls_context.load_cert_chain(self._cert, keyfile=self._private_key)

            # https://docs.python.org/3/library/ssl.html#ssl.create_default_context
            if 'SSLv3' in self._allowed_versions:  # no cov
                self._tls_context.options &= ~ssl.OP_NO_SSLv3

        return self._tls_context
