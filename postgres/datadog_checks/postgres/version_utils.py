# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re

from semver import VersionInfo

from datadog_checks.base.log import get_check_logger
from datadog_checks.postgres.cursor import CommenterCursor

V8_3 = VersionInfo.parse("8.3.0")
V9 = VersionInfo.parse("9.0.0")
V9_1 = VersionInfo.parse("9.1.0")
V9_2 = VersionInfo.parse("9.2.0")
V9_4 = VersionInfo.parse("9.4.0")
V9_6 = VersionInfo.parse("9.6.0")
V10 = VersionInfo.parse("10.0.0")
V11 = VersionInfo.parse("11.0.0")
V12 = VersionInfo.parse("12.0.0")
V13 = VersionInfo.parse("13.0.0")
V14 = VersionInfo.parse("14.0.0")
V15 = VersionInfo.parse("15.0.0")


class VersionUtils(object):
    def __init__(self):
        self.log = get_check_logger()
        self._seen_aurora_exception = False

    @staticmethod
    def get_raw_version(db):
        with db as conn:
            with conn.cursor(cursor_factory=CommenterCursor) as cursor:
                cursor.execute('SHOW SERVER_VERSION;')
                raw_version = cursor.fetchone()[0]
                return raw_version

    def is_aurora(self, db):
        if self._seen_aurora_exception:
            return False
        with db as conn:
            with conn.cursor(cursor_factory=CommenterCursor) as cursor:
                # This query will pollute PG logs in non aurora versions,
                # but is the only reliable way to detect aurora
                try:
                    cursor.execute('select AURORA_VERSION();')
                    return True
                except Exception as e:
                    self.log.debug(
                        "Captured exception %s while determining if the DB is aurora. Assuming is not", str(e)
                    )
                    self._seen_aurora_exception = True
                    return False

    @staticmethod
    def parse_version(raw_version):
        try:
            # Only works for MAJOR.MINOR.PATCH(-PRE_RELEASE)
            return VersionInfo.parse(raw_version)
        except ValueError:
            pass
        try:
            # Version may be missing minor eg: 10.0 and it might have an edition suffix (e.g. 12.3_TDE_1.0)
            version = re.split('[ _]', raw_version)[0].split('.')
            version = [int(part) for part in version]
            while len(version) < 3:
                version.append(0)
            return VersionInfo(*version)
        except ValueError:
            # Postgres might be in development, with format \d+[beta|rc]\d+
            match = re.match(r'(\d+)([a-zA-Z]+)(\d+)', raw_version)
            if match:
                version = list(match.groups())
                return VersionInfo.parse('{}.0.0-{}.{}'.format(*version))
        raise Exception("Cannot determine which version is {}".format(raw_version))

    @staticmethod
    def transform_version(raw_version, options=None):
        """
        :param raw_version: raw version in str format
        :param options: keyword arguments to pass to any defined transformer
        """
        version = VersionUtils.parse_version(raw_version)
        transformed = {
            'version.major': str(version.major),
            'version.minor': str(version.minor),
            'version.patch': str(version.patch),
            'version.raw': raw_version,
            'version.scheme': 'semver',
        }
        if version.prerelease:
            transformed['version.release'] = version.prerelease
        return transformed
