# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re
import semver


def get_version(db):
    cursor = db.cursor()
    cursor.execute('SHOW SERVER_VERSION;')
    raw_version = cursor.fetchone()[0]
    try:
        version_parts = raw_version.split(' ')[0].split('.')
        version = [int(part) for part in version_parts]
        while len(version) < 3:
            version.append(0)
        return semver.VersionInfo(*version)
    except Exception:
        # Postgres might be in development, with format \d+[beta|rc]\d+
        match = re.match(r'(\d+)([a-zA-Z]+)(\d+)', raw_version)
        if match:
            version = list(match.groups())
            # We found a valid development version
            if len(version) == 3:
                # Replace development tag with a negative number to properly compare versions
                version[1] = -1
                version = [int(part) for part in version]
            return semver.VersionInfo(*version)


def is_above(version, version_to_compare):
    if version is None:
        return False
    return version >= semver.parse(version_to_compare)


def is_8_3_or_above(version):
    return is_above(version, "8.3.0")


def is_9_1_or_above(version):
    return is_above(version, "9.1.0")


def is_9_2_or_above(version):
    return is_above(version, "9.2.0")


def is_9_4_or_above(version):
    return is_above(version, "9.4.0")


def is_9_6_or_above(version):
    return is_above(version, "9.6.0")


def is_10_or_above(version):
    return is_above(version, "10.0.0")
