# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re
from collections import namedtuple

from datadog_checks.base import to_native_string
from datadog_checks.base.log import get_check_logger

from .const import BUILDS

# Precompile regex for extracting numeric part from patch level (e.g., "51a" -> "51")
PATCHLEVEL_REGEX = re.compile(r"([0-9]+)")


def parse_version(raw_version, version_comment):
    # Version might include a build, a flavor, or both
    # e.g. 4.1.26-log, 4.1.26-MariaDB, 10.0.1-MariaDB-mariadb1precise-log
    # See http://dev.mysql.com/doc/refman/4.1/en/information-functions.html#function_version
    # https://mariadb.com/kb/en/library/version/
    # and https://mariadb.com/kb/en/library/server-system-variables/#version
    parts = raw_version.split('-')
    version, flavor, build = [parts[0], '', '']

    for data in parts:
        if data == "MariaDB":
            flavor = "MariaDB"
        if data != "MariaDB" and flavor == '':
            flavor = "MySQL"
        if data in BUILDS:
            build = data
    if version_comment and to_native_string(version_comment).lower().startswith('percona'):
        flavor = 'Percona'
    if build == '':
        build = 'unspecified'

    return MySQLVersion(version, flavor, build)


class MySQLVersion(namedtuple('MySQLVersion', ['version', 'flavor', 'build'])):
    def version_compatible(self, compat_version):
        # some patch version numbers contain letters (e.g. 5.0.51a)
        # so let's be careful when we compute the version number
        try:
            mysql_version = self.version.split('.')
        except Exception as e:
            log = get_check_logger()
            log.warning("Cannot compute MySQL version, assuming it's older: %s", e)
            return False

        patchlevel = int(PATCHLEVEL_REGEX.match(mysql_version[2] if len(mysql_version) > 2 else '0').group(1))
        version = (int(mysql_version[0]), int(mysql_version[1]), patchlevel)

        return version >= compat_version
