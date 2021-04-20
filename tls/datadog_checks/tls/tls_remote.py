# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ssl
from hashlib import sha256

from cryptography.hazmat.backends import default_backend
from cryptography.x509.base import load_der_x509_certificate
from cryptography.x509.extensions import ExtensionNotFound
from cryptography.x509.oid import AuthorityInformationAccessOID, ExtensionOID

from datadog_checks.base import ConfigurationError, is_affirmative
from datadog_checks.base.utils.time import get_timestamp

from . import TLSCheck
from .const import SERVICE_CHECK_CAN_CONNECT, SERVICE_CHECK_EXPIRATION, SERVICE_CHECK_VALIDATION
from .utils import closing


class TLSRemoteCheck(TLSCheck):
    def __init__(self, name, init_config, instances):
        super(TLSRemoteCheck, self).__init__(name, init_config, instances)
        self.log.debug('Selecting remote connection for method of collection')
        self._tags.append('server_hostname:{}'.format(self._server_hostname))
        self._tags.append('server:{}'.format(self._server))
        self._tags.append('port:{}'.format(self._port))

        self._fetch_intermediate_certs = is_affirmative(
            self.instance.get('fetch_intermediate_certs', self.init_config.get('fetch_intermediate_certs', False))
        )
        self._intermediate_cert_refresh_interval = (
            # Convert minutes to seconds
            float(self.instance.get('intermediate_cert_refresh_interval', 60))
            * 60
        )

    def check(self, _):
        if not self._server:
            raise ConfigurationError('You must specify `server` in your configuration file.')

        if self._fetch_intermediate_certs:
            self.fetch_intermediate_certs()

        sock = self._get_connection()
        cert, protocol_version = self._get_cert_and_protocol_version(sock)

        self.check_protocol_version(protocol_version)
        self.validate_certificate(cert)
        self.check_age(cert)

    def _get_cert_and_protocol_version(self, sock):
        if sock is None:
            self.log.debug("Could not validate certificate because there is no connection")
            return None, None
        # Get the cert & TLS version from the connection
        with closing(sock):
            self.log.debug('Getting cert and TLS protocol version')
            try:
                with closing(
                    self.get_tls_context().wrap_socket(sock, server_hostname=self._server_hostname)
                ) as secure_sock:
                    der_cert = secure_sock.getpeercert(binary_form=True)
                    protocol_version = secure_sock.version()
                    self.log.debug('Received serialized peer certificate and TLS protocol version %s', protocol_version)
            except Exception as e:
                # https://docs.python.org/3/library/ssl.html#ssl.SSLCertVerificationError
                err_code = getattr(e, 'verify_code', None)
                message = getattr(e, 'verify_message', str(e))
                self.log.debug('Error occurred while getting cert and TLS version from connection: %s', str(e))
                self.service_check(SERVICE_CHECK_VALIDATION, self.CRITICAL, tags=self._tags, message=message)

                # There's no sane way to tell it to not validate just the expiration
                # This only works on Python 3.7+, see: https://bugs.python.org/issue28182
                # https://github.com/openssl/openssl/blob/0b45d8eec051fd9816b6bf46a975fa461ffc983d/include/openssl/x509_vfy.h#L109
                if err_code == 10:
                    self.service_check(
                        SERVICE_CHECK_EXPIRATION, self.CRITICAL, tags=self._tags, message='Certificate has expired'
                    )

                return None, None

        # Load https://cryptography.io/en/latest/x509/reference/#cryptography.x509.Certificate
        try:
            self.log.debug('Deserializing peer certificate')
            cert = load_der_x509_certificate(der_cert, default_backend())
            self.log.debug('Deserialized peer certificate: %s', cert)
            return cert, protocol_version
        except Exception as e:
            self.log.debug('Error while deserializing peer certificate: %s', str(e))
            self.service_check(
                SERVICE_CHECK_VALIDATION,
                self.CRITICAL,
                tags=self._tags,
                message='Unable to parse the certificate: {}'.format(e),
            )
            return None, None

    def _get_connection(self):
        try:
            self.log.debug('Checking that TLS service check can connect')
            sock = self.create_connection()
        except Exception as e:
            self.log.debug('Error occurred while connecting to socket: %s', str(e))
            self.service_check(SERVICE_CHECK_CAN_CONNECT, self.CRITICAL, tags=self._tags, message=str(e))
            return
        else:
            self.log.debug('TLS check able to connect')
            self.service_check(SERVICE_CHECK_CAN_CONNECT, self.OK, tags=self._tags)
        return sock

    def fetch_intermediate_certs(self):
        # TODO: prefer stdlib implementation when available, see https://bugs.python.org/issue18617
        try:
            sock = self.create_connection()
        except Exception as e:
            self.log.error('Error occurred while connecting to socket to discover intermediate certificates: %s', e)
            return

        with closing(sock):
            try:
                context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)
                context.verify_mode = ssl.CERT_NONE

                with closing(context.wrap_socket(sock, server_hostname=self._server_hostname)) as secure_sock:
                    der_cert = secure_sock.getpeercert(binary_form=True)
            except Exception as e:
                self.log.error('Error occurred while getting cert to discover intermediate certificates: %s', e)
                return

        self.load_intermediate_certs(der_cert)

    def load_intermediate_certs(self, der_cert):
        # https://tools.ietf.org/html/rfc3280#section-4.2.2.1
        # https://tools.ietf.org/html/rfc5280#section-5.2.7
        try:
            cert = load_der_x509_certificate(der_cert, default_backend())
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
                uri in self._intermediate_cert_uri_cache
                and get_timestamp() - self._intermediate_cert_uri_cache[uri] < self._intermediate_cert_refresh_interval
            ):
                continue

            # Assume HTTP for now
            try:
                response = self.http.get(uri)  # SKIP_HTTP_VALIDATION
                response.raise_for_status()
            except Exception as e:
                self.log.error('Error fetching intermediate certificate from `%s`: %s', uri, e)
                continue
            else:
                access_time = get_timestamp()
                intermediate_cert = response.content

            cert_id = sha256(intermediate_cert).digest()
            if cert_id not in self._intermediate_cert_id_cache:
                self.get_tls_context().load_verify_locations(cadata=intermediate_cert)
                self._intermediate_cert_id_cache.add(cert_id)

            self._intermediate_cert_uri_cache[uri] = access_time
            self.load_intermediate_certs(intermediate_cert)
