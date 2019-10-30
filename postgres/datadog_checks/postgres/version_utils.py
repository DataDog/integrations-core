# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re

import semver

V8_3 = semver.parse("8.3.0")
V9 = semver.parse("9.0.0")
V9_1 = semver.parse("9.1.0")
V9_2 = semver.parse("9.2.0")
V9_4 = semver.parse("9.4.0")
V9_6 = semver.parse("9.6.0")
V10 = semver.parse("10.0.0")


def get_version(db):
    cursor = db.cursor()
    cursor.execute('SHOW SERVER_VERSION;')
    raw_version = cursor.fetchone()[0]
    version = _parse_version(raw_version)
    return raw_version, version


def _parse_version(raw_version):
    try:
        # Only works for MAJOR.MINOR.PATCH(-PRE_RELEASE)
        return semver.parse_version_info(raw_version)
    except ValueError:
        try:
            # Version may be missing minor eg: 10.0
            version = raw_version.split(' ')[0].split('.')
            version = [int(part) for part in version]
            while len(version) < 3:
                version.append(0)
            return semver.parse_version_info('{}.{}.{}'.format(*version))
        except ValueError as e:
            # Postgres might be in development, with format \d+[beta|rc]\d+
            match = re.match(r'(\d+)([a-zA-Z]+)(\d+)', raw_version)
            if match:
                version = list(match.groups())
                return semver.parse_version_info('{}.0.0-{}.{}'.format(*version))
    raise Exception("Cannot determine which version is {}".format(raw_version))


def transform_version(raw_version, options=None):
    version = _parse_version(raw_version)
    return {
        'version.major': version.major,
        'version.minor': version.minor,
        'version.patch': version.patch,
        'version.release': version.prerelease,
        'version.raw': raw_version,
        'version.scheme': 'semver',
    }
