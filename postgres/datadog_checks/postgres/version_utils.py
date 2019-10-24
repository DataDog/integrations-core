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
    version_parts = None
    try:
        # Only works for MAJOR.MINOR.PATCH(-PRE_RELEASE)
        version_parts = semver.parse(raw_version)
    except ValueError:
        try:
            # Version may be missing minor eg: 10.0
            version = raw_version.split(' ')[0].split('.')
            version = [int(part) for part in version]
            while len(version) < 3:
                version.append(0)
            version_parts = semver.parse('{}.{}.{}'.format(*version))
        except ValueError as e:
            # Postgres might be in development, with format \d+[beta|rc]\d+
            match = re.match(r'(\d+)([a-zA-Z]+)(\d+)', raw_version)
            if match:
                version = list(match.groups())
                version_parts = semver.parse('{}.0.0-{}.{}'.format(*version))
    if version_parts:
        return semver.VersionInfo(
            major=version_parts.get('major'),
            minor=version_parts.get('minor'),
            patch=version_parts.get('patch'),
            prerelease=version_parts.get('prerelease', None),
        )
    return None


def transform_version(raw_version, options=None):
    version = _parse_version(raw_version)
    return {
        'version.major': version.major,
        'version.minor': version.minor,
        'version.patch': version.patch,
        'version.build': version.prerelease,
        'version.raw': raw_version,
        'version.scheme': 'semver',
    }


def is_above(version, version_to_compare):
    if isinstance(version_to_compare, str):
        version_parts = semver.parse(version_to_compare)
        version_to_compare = semver.VersionInfo(
            major=version_parts.get('major'),
            minor=version_parts.get('minor'),
            patch=version_parts.get('patch'),
            prerelease=version_parts.get('prerelease', None),
        )
    if version is None:
        return False
    return version >= version_to_compare


def is_8_3_or_above(version):
    return is_above(version, V8_3)


def is_9_1_or_above(version):
    return is_above(version, V9_1)


def is_9_2_or_above(version):
    return is_above(version, V9_2)


def is_9_4_or_above(version):
    return is_above(version, V9_4)


def is_9_6_or_above(version):
    return is_above(version, V9_6)


def is_10_or_above(version):
    return is_above(version, V10)
