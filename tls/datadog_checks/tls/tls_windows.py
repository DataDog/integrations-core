# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re
import ssl

from cryptography.x509.base import load_der_x509_certificate

from datadog_checks.base import ConfigurationError
from datadog_checks.base.log import get_check_logger
from datadog_checks.tls.const import SERVICE_CHECK_VALIDATION


class TLSWindowsCheck(object):
    def __init__(self, agent_check):
        self.agent_check = agent_check
        self.log = get_check_logger()
        self.log.debug('Selecting windows certificates for method of collection')
        if self.agent_check._tls_validate_hostname and self.agent_check._server_hostname:
            self.agent_check._tags.append('server_hostname:{}'.format(self.agent_check._server_hostname))

    def _get_windows_cert(self, store, cert_filters):
        certs = []
        try:
            self.log.debug('Reading from Windows cert store')
            for cert, _encoding, _trust in ssl.enum_certificates(store):
                decoded_cert = self._parse_cert(cert)
                if self.agent_check._cert_subject:
                    for cert_filter in cert_filters:
                        if re.search(cert_filter, str(decoded_cert.subject)):
                            if decoded_cert not in certs:
                                certs.append(decoded_cert)
                                break
                else:
                    if decoded_cert not in certs:
                        certs.append(decoded_cert)
        except Exception as e:
            self.log.debug('Error occurred while reading from Windows cert store: %s', str(e))
            self.agent_check.service_check(
                SERVICE_CHECK_VALIDATION,
                self.agent_check.CRITICAL,
                tags=self.agent_check._tags,
                message='Unable to open the certificate: {}'.format(e),
            )
            return None
        return certs

    def _parse_cert(self, cert):
        # Load https://cryptography.io/en/latest/x509/reference/#cryptography.x509.Certificate
        try:
            self.log.debug('Parsing certificate')
            cert = load_der_x509_certificate(cert)
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

        cert_filters = [re.compile(cert_filter, re.IGNORECASE) for cert_filter in self.agent_check._cert_subject]

        for store in self.agent_check._certificate_stores:
            certs = self._get_windows_cert(store, cert_filters)

            for cert in certs:
                self.agent_check.validate_certificate(cert, ['certificate_store:{}'.format(store)])
                self.agent_check.check_age(cert, ['certificate_store:{}'.format(store)])
