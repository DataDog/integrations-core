# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re

from semver import VersionInfo

from datadog_checks.base.log import get_check_logger

V8_3 = VersionInfo.parse("8.3.0")
V9 = VersionInfo.parse("9.0.0")
V9_1 = VersionInfo.parse("9.1.0")
V9_2 = VersionInfo.parse("9.2.0")
V9_4 = VersionInfo.parse("9.4.0")
V9_6 = VersionInfo.parse("9.6.0")
V10 = VersionInfo.parse("10.0.0")
V12 = VersionInfo.parse("12.0.0")


class VersionUtils(object):
    def __init__(self):
        self.log = get_check_logger()

    @staticmethod
    def get_raw_version(db):
        cursor = db.cursor()
        cursor.execute('SHOW SERVER_VERSION;')
        raw_version = cursor.fetchone()[0]
        return raw_version

    def is_aurora(self, db):
        cursor = db.cursor()
        try:
            # This query will pollute PG logs in non aurora versions but is the only reliable way of detecting aurora
            cursor.execute('select AURORA_VERSION();')
            return True
        except Exception as e:
            self.log.debug("Captured exception %s while determining if the DB is aurora. Assuming is not", str(e))
            db.rollback()
            return False

    @staticmethod
    def parse_version(raw_version):
        try:
            # Only works for MAJOR.MINOR.PATCH(-PRE_RELEASE)
            return VersionInfo.parse(raw_version)
        except ValueError:
            pass
        try:
            # Version may be missing minor eg: 10.0
            version = raw_version.split(' ')[0].split('.')
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
