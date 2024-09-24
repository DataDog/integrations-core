# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from ipaddress import ip_address

# https://github.com/python/cpython/blob/ef516d11c1a0f885dba0aba8cf5366502077cdd4/Lib/ssl.py#L158-L165
DEFAULT_PROTOCOL_VERSIONS = {'TLSv1.2', 'TLSv1.3'}
SUPPORTED_PROTOCOL_VERSIONS = {'SSLv3', 'TLSv1', 'TLSv1.1', 'TLSv1.2', 'TLSv1.3'}


def get_protocol_versions(versions):
    if not versions:
        return DEFAULT_PROTOCOL_VERSIONS.copy()

    protocol_versions = set()

    for version in versions:
        if isinstance(version, str) and version.startswith(('v', 'V')):
            version = version[1:]

        try:
            version = float(version)
        except (TypeError, ValueError):
            lowered = version.lower()
            if lowered == 'tlsv1.0':
                lowered = 'tlsv1'

            for supported_version in SUPPORTED_PROTOCOL_VERSIONS:
                if lowered == supported_version.lower():
                    version = supported_version
                    break
        else:
            if version == 1.0:
                version = 1

            version = 'TLSv{}'.format(version)

        protocol_versions.add(version)

    return protocol_versions


def is_ip_address(hostname):
    try:
        ip_address(str(hostname))
    except ValueError:
        return False

    return True


def days_to_seconds(days):
    return int(days * 24 * 60 * 60)


def seconds_to_days(seconds):
    return seconds / 60 / 60 / 24
