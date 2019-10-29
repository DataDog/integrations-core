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
    return raw_version
