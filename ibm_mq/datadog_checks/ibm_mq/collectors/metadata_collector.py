# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base.utils.common import to_native_string

try:
    import pymqi
except ImportError as e:
    pymqiException = e
    pymqi = None


class MetadataCollector(object):
    def __init__(self, log):
        self.log = log

    def collect_metadata(self, queue_manager):
        try:
            raw_version = self._get_version(queue_manager)
            self.log.debug('IBM MQ version: %s', raw_version)
            return raw_version
        except Exception as e:
            self.log.debug("Version could not be retreived: %s", e)
            return

    def _get_version(self, queue_manager):
        pcf = pymqi.PCFExecute(queue_manager)
        resp = pcf.MQCMD_INQUIRE_Q_MGR()
        try:
            version = to_native_string(resp[0][2120])
            self.log.debug("IBM MQ version from response: %s", version)
        except Exception as e:
            self.log.debug("Error collecting IBM MQ version: %s", e)
            return None

        if version is None:
            return None
        return self._parse_version(version)

    @staticmethod
    def _parse_version(version):
        try:
            major, minor, mod, fix = [int(version[i : i + 2]) for i in range(0, len(version), 2)]
            return {
                'major': str(int(major)),
                'minor': str(int(minor)),
                'mod': str(int(mod)),
                'fix': str(int(fix)),
            }
        except Exception:
            return None
