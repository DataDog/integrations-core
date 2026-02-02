# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re

from semver import VersionInfo

from datadog_checks.base.log import get_check_logger

DEV_VERSION_PATTERN = re.compile(r'(\d+)([a-zA-Z]+)(\d+)')
RDS_VERSION_PATTERN = re.compile(r'(\d+\.\d+)-rds\.(\d+)')
VERSION_SPLIT_PATTERN = re.compile(r'[ _]')

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
V16 = VersionInfo.parse("16.0.0")
V17 = VersionInfo.parse("17.0.0")
V18 = VersionInfo.parse("18.0.0")


class VersionUtils(object):
    def __init__(self):
        self.log = get_check_logger()
        self._is_aurora = None

    @staticmethod
    def get_raw_version(db):
        with db as conn:
            with conn.cursor() as cursor:
                cursor.execute('SHOW SERVER_VERSION;')
                raw_version = cursor.fetchone()[0]
                return raw_version

    def is_aurora(self, db):
        if self._is_aurora is not None:
            return self._is_aurora
        with db as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM pg_available_extension_versions "
                    "WHERE name ILIKE '%aurora%' OR comment ILIKE '%aurora%' "
                    "LIMIT 1;"
                )
                if cursor.fetchone():
                    # This query will pollute PG logs in non aurora versions,
                    # but is the only reliable way to detect aurora.
                    # Since we found aurora extensions, this should exist.
                    try:
                        cursor.execute('select AURORA_VERSION();')
                        self._is_aurora = True
                        return self._is_aurora
                    except Exception as e:
                        self.log.debug(
                            "Captured exception %s while determining if the DB is aurora. Assuming is not", str(e)
                        )
                self._is_aurora = False
                return self._is_aurora

    @staticmethod
    def parse_version(raw_version):
        try:
            # Only works for MAJOR.MINOR.PATCH(-PRE_RELEASE)
            return VersionInfo.parse(raw_version)
        except ValueError:
            pass
        try:
            # Version may be missing minor eg: 10.0 and it might have an edition suffix (e.g. 12.3_TDE_1.0)
            version = VERSION_SPLIT_PATTERN.split(raw_version)[0].split('.')
            version = [int(part) for part in version]
            while len(version) < 3:
                version.append(0)
            return VersionInfo(*version)
        except ValueError:
            pass
        try:
            # Postgres might be in development, with format \d+[beta|rc]\d+
            match = DEV_VERSION_PATTERN.match(raw_version)
            if match:
                version = list(match.groups())
                return VersionInfo.parse('{}.0.0-{}.{}'.format(*version))
            else:
                raise ValueError('Unable to match development version')
        except ValueError:
            # RDS changes the version format when the version switches to EOL.
            # Example: 11.22-rds.20241121.
            match = RDS_VERSION_PATTERN.match(raw_version)
            if match:
                version = list(match.groups())
                return VersionInfo.parse('{}.{}'.format(*version))
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
