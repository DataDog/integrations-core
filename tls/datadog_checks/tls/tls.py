# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import socket
import ssl
from datetime import datetime

import service_identity
from six import text_type
from six.moves.urllib.parse import urlparse

from datadog_checks.base import AgentCheck, is_affirmative

from .const import (
    DEFAULT_EXPIRE_SECONDS_CRITICAL,
    DEFAULT_EXPIRE_SECONDS_WARNING,
    SERVICE_CHECK_EXPIRATION,
    SERVICE_CHECK_VALIDATION,
    SERVICE_CHECK_VERSION,
)
from .utils import days_to_seconds, get_protocol_versions, is_ip_address, seconds_to_days

# Python 3 only
PROTOCOL_TLS_CLIENT = getattr(ssl, 'PROTOCOL_TLS_CLIENT', ssl.PROTOCOL_TLS)


class TLSCheck(AgentCheck):
    # This remapper is used to support legacy TLS integration config values
    TLS_CONFIG_REMAPPER = {
        'cert': {'name': 'tls_cert'},
        'private_key': {'name': 'tls_private_key'},
        'ca_cert': {'name': 'tls_ca_cert'},
        'validate_hostname': {'name': 'tls_validate_hostname'},
        'validate_cert': {'name': 'tls_verify'},
    }

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

        self._start_tls = self.instance.get('start_tls')

        # https://en.wikipedia.org/wiki/Server_Name_Indication
        self._server_hostname = self.instance.get('server_hostname', self._server)

        # `validate_hostname` is still supported for legacy implementations of TLS
        self._tls_validate_hostname = is_affirmative(self.instance.get('tls_validate_hostname', True))
        self._validate_hostname = is_affirmative(self.instance.get('validate_hostname', True))

        # If either `tls_validate_hostname` or `validate_hostname` is false, then set to false
        if not self._tls_validate_hostname or not self._validate_hostname:
            self._tls_validate_hostname = False

        # Thresholds expressed in seconds take precedence over those expressed in days
        self._seconds_warning = (
            int(self.instance.get('seconds_warning', 0))
            or days_to_seconds(float(self.instance.get('days_warning', 0)))
            or DEFAULT_EXPIRE_SECONDS_WARNING
        )
        self._seconds_critical = (
            int(self.instance.get('seconds_critical', 0))
            or days_to_seconds(float(self.instance.get('days_critical', 0)))
            or DEFAULT_EXPIRE_SECONDS_CRITICAL
        )

        # https://docs.python.org/3/library/ssl.html#ssl.SSLSocket.version
        self.allowed_versions = get_protocol_versions(
            self.instance.get('allowed_versions', self.init_config.get('allowed_versions', []))
        )

        self._send_cert_duration = self.instance.get('send_cert_duration', False)

        # Global tags
        self._tags = self.instance.get('tags', [])
        if self._name:
            self._tags.append('name:{}'.format(self._name))

        # Assign lazily since these aren't used by both collection methods
        self._validation_data = None

        # Only fetch intermediate certs from the indicated URIs occasionally
        self._intermediate_cert_uri_cache = {}

        # Only load intermediate certs once
        self._intermediate_cert_id_cache = set()

        local_cert_path = instances[0].get('local_cert_path', '')

        # Decide the method of collection for this instance (local file vs remote connection)
        if local_cert_path:
            from .tls_local import TLSLocalCheck

            self.checker = TLSLocalCheck(self)
        else:
            from .tls_remote import TLSRemoteCheck

            self.checker = TLSRemoteCheck(self)

    def check(self, _):
        self.checker.check()

    def check_protocol_version(self, version):
        if version is None:
            self.log.debug('Could not fetch protocol version')
            return

        self.log.debug('Checking protocol version')
        if version in self.allowed_versions:
            self.log.debug('Protocol version is allowed')
            self.service_check(SERVICE_CHECK_VERSION, self.OK, tags=self._tags)
        else:
            self.service_check(
                SERVICE_CHECK_VERSION,
                self.CRITICAL,
                tags=self._tags,
                message='Disallowed protocol version: {}'.format(version),
            )

    def validate_certificate(self, cert):
        if cert is None:
            self.log.debug('Could not validate the certificate')
            return
        self.log.debug('Validating certificate')
        if self._tls_validate_hostname:
            validator, host_type = self.validation_data

            try:
                validator(cert, text_type(self._server_hostname))
            except service_identity.VerificationError:
                message = 'The {} on the certificate does not match the given host'.format(host_type)
                self.log.debug(message)
                self.service_check(
                    SERVICE_CHECK_VALIDATION,
                    self.CRITICAL,
                    tags=self._tags,
                    message=message,
                )
                return
            except service_identity.CertificateError as e:  # no cov
                message = 'The certificate contains invalid/unexpected data: {}'.format(e)
                self.log.debug(message)
                self.service_check(
                    SERVICE_CHECK_VALIDATION,
                    self.CRITICAL,
                    tags=self._tags,
                    message=message,
                )
                return
        self.log.debug('Certificate is valid')
        self.service_check(SERVICE_CHECK_VALIDATION, self.OK, tags=self._tags)

    def check_age(self, cert):
        if cert is None:
            self.log.debug('Cannot verify certificate expiration')
            return

        if self._send_cert_duration:
            self.log.debug('Checking issued days of certificate')
            issued_delta = cert.not_valid_after - cert.not_valid_before
            issued_seconds = issued_delta.total_seconds()
            issued_days = seconds_to_days(issued_seconds)

            self.count('tls.issued_days', issued_days, tags=self._tags)
            self.count('tls.issued_seconds', issued_seconds, tags=self._tags)

        self.log.debug('Checking age of certificate')
        delta = cert.not_valid_after - datetime.utcnow()
        seconds_left = delta.total_seconds()
        days_left = seconds_to_days(seconds_left)

        self.gauge('tls.days_left', days_left, tags=self._tags)
        self.gauge('tls.seconds_left', seconds_left, tags=self._tags)

        if seconds_left <= 0:
            self.service_check(
                SERVICE_CHECK_EXPIRATION, self.CRITICAL, tags=self._tags, message='Certificate has expired'
            )
        elif seconds_left < self._seconds_critical:
            self.service_check(
                SERVICE_CHECK_EXPIRATION,
                self.CRITICAL,
                tags=self._tags,
                message='Certificate will expire in only {} days'.format(days_left),
            )
        elif seconds_left < self._seconds_warning:
            self.service_check(
                SERVICE_CHECK_EXPIRATION,
                self.WARNING,
                tags=self._tags,
                message='Certificate will expire in {} days'.format(days_left),
            )
        else:
            self.log.debug('Age is valid')
            self.service_check(SERVICE_CHECK_EXPIRATION, self.OK, tags=self._tags)

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
