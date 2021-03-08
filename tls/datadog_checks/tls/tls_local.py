# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_der_x509_certificate, load_pem_x509_certificate
from tls.datadog_checks.tls import TLSCheck
from tls.datadog_checks.tls.const import SERVICE_CHECK_VALIDATION

from datadog_checks.base import ConfigurationError


class TLSLocalCheck(TLSCheck):
    def __init__(self, name, init_config, instances):
        super(TLSLocalCheck, self).__init__(name, init_config, instances)
        self.log.debug('Selecting local connection for method of collection')
        if self._tls_validate_hostname and self._server_hostname:
            self._tags.append('server_hostname:{}'.format(self._server_hostname))

    def _get_local_cert(self):
        try:
            with open(self._local_cert_path, 'rb') as f:
                self.log.debug('Reading from local cert path')
                cert = f.read()
        except Exception as e:
            self.log.debug('Error occurred while reading from local cert path: %s', str(e))
            self.service_check(
                SERVICE_CHECK_VALIDATION,
                self.CRITICAL,
                tags=self._tags,
                message='Unable to open the certificate: {}'.format(e),
            )
            return None
        # Load https://cryptography.io/en/latest/x509/reference/#cryptography.x509.Certificate
        try:
            self.log.debug('Parsing certificate')
            cert = self.local_cert_loader(cert)
            self.log.debug('Deserialized certificate: %s', cert)
        except Exception as e:
            self.service_check(
                SERVICE_CHECK_VALIDATION,
                self.CRITICAL,
                tags=self._tags,
                message='Unable to parse the certificate: {}'.format(e),
            )
            return None
        return cert

    def check(self, _):
        if self._tls_validate_hostname and not self._server_hostname:
            raise ConfigurationError(
                'You must specify `server_hostname` in your configuration file, or disable `tls_validate_hostname`.'
            )

        cert = self._get_local_cert()
        self.validate_certificate(cert)
        self.check_age(cert)

    @staticmethod
    def local_cert_loader(cert):
        backend = default_backend()
        if b'-----BEGIN CERTIFICATE-----' in cert:
            return load_pem_x509_certificate(cert, backend)
        return load_der_x509_certificate(cert, backend)
