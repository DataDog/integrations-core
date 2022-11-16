# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from cryptography.x509 import load_der_x509_certificate, load_pem_x509_certificate

from datadog_checks.base import ConfigurationError
from datadog_checks.base.log import get_check_logger
from datadog_checks.tls.const import SERVICE_CHECK_VALIDATION


class TLSLocalCheck(object):
    def __init__(self, agent_check):
        self.agent_check = agent_check
        self.log = get_check_logger()
        self.log.debug('Selecting local connection for method of collection')
        if self.agent_check._tls_validate_hostname and self.agent_check._server_hostname:
            self.agent_check._tags.append('server_hostname:{}'.format(self.agent_check._server_hostname))

    def _get_local_cert(self):
        try:
            with open(self.agent_check._local_cert_path, 'rb') as f:
                self.log.debug('Reading from local cert path')
                cert = f.read()
        except Exception as e:
            self.log.debug('Error occurred while reading from local cert path: %s', str(e))
            self.agent_check.service_check(
                SERVICE_CHECK_VALIDATION,
                self.agent_check.CRITICAL,
                tags=self.agent_check._tags,
                message='Unable to open the certificate: {}'.format(e),
            )
            return None
        # Load https://cryptography.io/en/latest/x509/reference/#cryptography.x509.Certificate
        try:
            self.log.debug('Parsing certificate')
            cert = self.local_cert_loader(cert)
            self.log.debug('Deserialized certificate: %s', cert)
        except Exception as e:
            message = 'Unable to parse the certificate: {}'.format(e)
            self.log.debug(message)
            self.agent_check.service_check(
                SERVICE_CHECK_VALIDATION,
                self.agent_check.CRITICAL,
                tags=self.agent_check._tags,
                message='Unable to parse the certificate: {}'.format(e),
            )
            return None
        return cert

    def check(self):
        if self.agent_check._tls_validate_hostname and not self.agent_check._server_hostname:
            raise ConfigurationError(
                'You must specify `server_hostname` in your configuration file, or disable `tls_validate_hostname`.'
            )

        cert = self._get_local_cert()
        self.agent_check.validate_certificate(cert)
        self.agent_check.check_age(cert)

    @staticmethod
    def local_cert_loader(cert):
        if b'-----BEGIN CERTIFICATE-----' in cert:
            return load_pem_x509_certificate(cert)
        return load_der_x509_certificate(cert)
