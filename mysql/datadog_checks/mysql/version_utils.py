# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re
from collections import namedtuple
from contextlib import closing

from datadog_checks.base import to_native_string
from datadog_checks.base.log import get_check_logger

from .const import BUILDS


def get_version(db):
    with closing(db.cursor()) as cursor:
        cursor.execute('SELECT VERSION()')
        result = cursor.fetchone()

        # Version might include a build, a flavor, or both
        # e.g. 4.1.26-log, 4.1.26-MariaDB, 10.0.1-MariaDB-mariadb1precise-log
        # See http://dev.mysql.com/doc/refman/4.1/en/information-functions.html#function_version
        # https://mariadb.com/kb/en/library/version/
        # and https://mariadb.com/kb/en/library/server-system-variables/#version
        raw_version = to_native_string(result[0])
        parts = raw_version.split('-')
        version, flavor, build = [parts[0], '', '']

        for data in parts:
            if data == "MariaDB":
                flavor = "MariaDB"
            if data != "MariaDB" and flavor == '':
                flavor = "MySQL"
            if data in BUILDS:
                build = data
        if build == '':
            build = 'unspecified'

        return MySQLVersion(version, flavor, build)


class MySQLVersion(namedtuple('MySQLVersion', ['version', 'flavor', 'build'])):
    def version_compatible(self, compat_version):
        # some patch version numbers contain letters (e.g. 5.0.51a)
        # so let's be careful when we compute the version number
        log = get_check_logger()
        try:
            mysql_version = self.version.split('.')
        except Exception as e:
            log.warning("Cannot compute mysql version, assuming it's older.: %s", e)
            return False
        log.debug("MySQL version %s", mysql_version)

        patchlevel = int(re.match(r"([0-9]+)", mysql_version[2]).group(1))
        version = (int(mysql_version[0]), int(mysql_version[1]), patchlevel)

        return version >= compat_version
