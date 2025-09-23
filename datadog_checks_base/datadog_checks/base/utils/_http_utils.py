# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any


def __getattr__(name: str) -> Any:
    # This is used to lazily load imports when the path contains subpackages
    if name == 'HostHeaderSSLAdapter':
        from requests_toolbelt.adapters.host_header_ssl import HostHeaderSSLAdapter

        return HostHeaderSSLAdapter

    if name == 'BotoAWSRequestsAuth':
        from aws_requests_auth.boto_utils import BotoAWSRequestsAuth

        return BotoAWSRequestsAuth

    if name == 'oauth2':
        from oauthlib import oauth2

        return oauth2

    if name == 'cryptography_serialization':
        from cryptography.hazmat.primitives import serialization

        return serialization

    if name == 'cryptography_x509_load_certificate':
        from cryptography.x509 import load_der_x509_certificate

        return load_der_x509_certificate

    if name == 'cryptography_x509_ExtensionNotFound':
        from cryptography.x509.extensions import ExtensionNotFound

        return ExtensionNotFound

    if name == 'cryptography_x509_AuthorityInformationAccessOID':
        from cryptography.x509.oid import AuthorityInformationAccessOID

        return AuthorityInformationAccessOID

    if name == 'cryptography_x509_ExtensionOID':
        from cryptography.x509.oid import ExtensionOID

        return ExtensionOID

    raise AttributeError(f'`{__name__}` object has no attribute `{name}`')
