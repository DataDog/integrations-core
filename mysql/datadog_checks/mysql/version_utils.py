# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import logging
import re
from collections import namedtuple
from contextlib import closing

from .const import BUILDS

log = logging.getLogger(__name__)


def get_metadata(db):
    with closing(db.cursor()) as cursor:
        cursor.execute('SELECT VERSION()')
        result = cursor.fetchone()

        # Version might include a build, a flavor, or both
        # e.g. 4.1.26-log, 4.1.26-MariaDB, 10.0.1-MariaDB-mariadb1precise-log
        # See http://dev.mysql.com/doc/refman/4.1/en/information-functions.html#function_version
        # https://mariadb.com/kb/en/library/version/
        # and https://mariadb.com/kb/en/library/server-system-variables/#version
        parts = result[0].split('-')
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

        return MySQLMetadata(version, flavor, build)


class MySQLMetadata(namedtuple('MySQLMetadata', ['version', 'flavor', 'build'])):
    def version_compatible(self, compat_version):
        # some patch version numbers contain letters (e.g. 5.0.51a)
        # so let's be careful when we compute the version number

        try:
            mysql_version = self.version.split('.')
        except Exception as e:
            log.warning("Cannot compute mysql version, assuming it's older.: %s", e)
            return False
        log.debug("MySQL version %s", mysql_version)

        patchlevel = int(re.match(r"([0-9]+)", mysql_version[2]).group(1))
        version = (int(mysql_version[0]), int(mysql_version[1]), patchlevel)

        return version >= compat_version
