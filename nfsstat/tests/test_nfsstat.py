# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os
from copy import deepcopy

import mock
import pytest

from datadog_checks.base import ensure_unicode
from datadog_checks.nfsstat import NfsStatCheck
from datadog_checks.nfsstat.nfsstat import SOURCE_NFSIOSTAT_PATH, Device

from .common import METRICS

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')

log = logging.getLogger(__name__)

OMNIBUS_NFSIOSTAT_PATH = '/opt/datadog-agent/embedded/sbin/nfsiostat'
OMNIBUS_PYTHON_PATH = '/opt/datadog-agent/embedded/bin/python'
FLEET_NFSIOSTAT_PATH = '/opt/datadog-packages/datadog-agent/stable/embedded/sbin/nfsiostat'
FLEET_PYTHON_PATH = '/opt/datadog-packages/datadog-agent/stable/embedded/bin/python'


def make_check(init_config: dict[str, str], present_paths: set[str]) -> NfsStatCheck:
    with mock.patch('datadog_checks.nfsstat.nfsstat.os.path.exists', side_effect=lambda path: path in present_paths):
        return NfsStatCheck('nfsstat', init_config, [{}])


class TestNfsstat:
    CHECK_NAME = 'nfsstat'
    INSTANCES = {'main': {'tags': ['optional:tag1']}}

    INIT_CONFIG = {'nfsiostat_path': '/opt/datadog-agent/embedded/sbin/nfsiostat'}

    def test_no_devices(self, aggregator):
        instance = self.INSTANCES['main']
        c = NfsStatCheck(self.CHECK_NAME, self.INIT_CONFIG, [instance])
        c.log = mock.MagicMock()

        with mock.patch(
            'datadog_checks.nfsstat.nfsstat.get_subprocess_output',
            return_value=('No NFS mount points were found', '', 0),
        ):
            c.check(instance)
        c.log.warning.assert_called_once_with("No NFS mount points were found.", extra=mock.ANY)

    def test_autofs_enabled(self, aggregator):
        instance = self.INSTANCES['main']
        init_config = deepcopy(self.INIT_CONFIG)
        init_config['autofs_enabled'] = True
        c = NfsStatCheck(self.CHECK_NAME, init_config, [instance])
        c.log = mock.MagicMock()

        with mock.patch(
            'datadog_checks.nfsstat.nfsstat.get_subprocess_output',
            return_value=('No NFS mount points were found', '', 0),
        ):
            c.check(instance)
        c.log.debug.assert_called_once_with("AutoFS enabled: no mount points currently.")

    def test_check(self, aggregator):
        instance = self.INSTANCES['main']
        c = NfsStatCheck(self.CHECK_NAME, self.INIT_CONFIG, [instance])

        with open(os.path.join(FIXTURE_DIR, 'nfsiostat'), 'rb') as f:
            mock_output = ensure_unicode(f.read())

        with mock.patch('datadog_checks.nfsstat.nfsstat.get_subprocess_output', return_value=(mock_output, '', 0)):
            c.check(instance)

        tags = list(instance['tags'])
        tags.extend(['nfs_server:192.168.34.1', 'nfs_export:/exports/nfs/datadog/two', 'nfs_mount:/mnt/datadog/two'])
        tags_unicode = list(instance['tags'])
        tags_unicode.extend(
            [
                'nfs_server:192.168.34.1',
                'nfs_export:/exports/nfs/datadog/thr\u00e9\u00e9',
                'nfs_mount:/mnt/datadog/thr\u00e9\u00e9',
            ]
        )

        for metric in METRICS:
            aggregator.assert_metric(metric, tags=tags)
            aggregator.assert_metric(metric, tags=tags_unicode)

        assert aggregator.metrics_asserted_pct == 100.0

    @pytest.mark.unit
    def test_device_without_export_path(self):
        device = Device(
            [
                ['nfs-server', 'mounted', 'on', '/test1:'],
                [],
                ['0.0', '0.0'],
                [],
                ['0.0', '0.0', '0.0', '0.0', '(0.0%)', '0.0', '0.0'],
                [],
                ['0.0', '0.0', '0.0', '0.0', '(0.0%)', '0.0', '0.0'],
            ],
            mock.MagicMock(),
        )

        assert device.nfs_server == 'nfs-server'
        assert device.nfs_export == ''

    @pytest.mark.unit
    def test_check_skips_incomplete_initial_sample(self, aggregator):
        instance = self.INSTANCES['main']
        check = NfsStatCheck(self.CHECK_NAME, self.INIT_CONFIG, [instance])

        with open(os.path.join(FIXTURE_DIR, 'nfsiostat'), 'rb') as f:
            mock_output = ensure_unicode(f.read())

        mock_output = 'nfs-server mounted on /test1:\n\n' + mock_output
        with mock.patch('datadog_checks.nfsstat.nfsstat.get_subprocess_output', return_value=(mock_output, '', 0)):
            check.check(instance)

        aggregator.assert_metric('system.nfs.ops')


@pytest.mark.unit
class TestNfsiostatPathResolution:
    def assert_check_uses_command(self, check: NfsStatCheck, expected_command: list[str]) -> None:
        with mock.patch(
            'datadog_checks.nfsstat.nfsstat.get_subprocess_output',
            return_value=('No NFS mount points were found', '', 0),
        ) as get_subprocess_output:
            check.check({})

        get_subprocess_output.assert_called_once_with(expected_command, check.log)

    def test_explicit_path_is_used_verbatim(self):
        self.assert_check_uses_command(
            make_check({'nfsiostat_path': '/custom/nfsiostat --debug'}, set()),
            ['/custom/nfsiostat', '--debug', '1', '2'],
        )

    def test_fleet_automation_path_uses_its_embedded_python(self):
        check = make_check({}, {FLEET_NFSIOSTAT_PATH, FLEET_PYTHON_PATH})

        self.assert_check_uses_command(check, [FLEET_PYTHON_PATH, FLEET_NFSIOSTAT_PATH, '1', '2'])

    def test_bundled_path_without_embedded_python_runs_directly(self):
        check = make_check({}, {FLEET_NFSIOSTAT_PATH})

        self.assert_check_uses_command(check, [FLEET_NFSIOSTAT_PATH, '1', '2'])

    def test_omnibus_path_takes_precedence(self):
        check = make_check(
            {},
            {OMNIBUS_NFSIOSTAT_PATH, OMNIBUS_PYTHON_PATH, FLEET_NFSIOSTAT_PATH, FLEET_PYTHON_PATH},
        )

        self.assert_check_uses_command(check, [OMNIBUS_PYTHON_PATH, OMNIBUS_NFSIOSTAT_PATH, '1', '2'])

    def test_source_path_runs_directly(self):
        check = make_check({}, {SOURCE_NFSIOSTAT_PATH})

        self.assert_check_uses_command(check, [SOURCE_NFSIOSTAT_PATH, '1', '2'])

    def test_missing_nfsiostat_raises(self):
        with pytest.raises(Exception, match='nfsstat check requires nfsiostat be installed'):
            make_check({}, set())
