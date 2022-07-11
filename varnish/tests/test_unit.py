# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from distutils.version import LooseVersion

import mock
import pytest

from datadog_checks.varnish import Varnish
from datadog_checks.varnish.varnish import sanitize_metric_name

from . import common, mocks

pyestmark = [pytest.mark.unit]


@mock.patch('datadog_checks.varnish.varnish.geteuid')
@mock.patch('datadog_checks.varnish.varnish.Varnish._get_version_info')
@mock.patch('datadog_checks.varnish.varnish.get_subprocess_output', side_effect=mocks.backend_manual_unhealthy_mock)
@pytest.mark.parametrize(
    'version, uuid, expected_cmd',
    [
        ((LooseVersion('4.0.0'), 'xml'), 0, [common.VARNISHADM_PATH, '-S', common.SECRETFILE_PATH, 'debug.health']),
        (
            (LooseVersion('4.1.0'), 'xml'),
            1,
            [
                'sudo',
                common.VARNISHADM_PATH,
                '-T',
                common.DAEMON_ADDRESS,
                '-S',
                common.SECRETFILE_PATH,
                'backend.list',
                '-p',
            ],
        ),
    ],
)
def test_command_line_manually_unhealthy(
    mock_subprocess, mock_version, mock_geteuid, aggregator, instance, version, uuid, expected_cmd
):
    """
    Test the varnishadm output with manually set health
    """
    instance['varnishadm'] = common.VARNISHADM_PATH
    instance['secretfile'] = common.SECRETFILE_PATH
    check = Varnish(common.CHECK_NAME, {}, [instance])

    mock_version.return_value = version
    mock_geteuid.return_value = uuid
    check.check(instance)

    args, _ = mock_subprocess.call_args
    assert args[0] == expected_cmd
    aggregator.assert_service_check(
        "varnish.backend_healthy", status=check.CRITICAL, tags=['backend:default', 'varnish_cluster:webs'], count=1
    )


@mock.patch('datadog_checks.varnish.varnish.geteuid')
@mock.patch('datadog_checks.varnish.varnish.Varnish._get_version_info')
@pytest.mark.parametrize(
    'version, uuid, expected_cmd, output_mock',
    [
        (
            (LooseVersion("3.9.0"), 'xml'),
            0,
            [common.VARNISHADM_PATH, '-S', common.SECRETFILE_PATH, 'debug.health'],
            mocks.debug_health_mock,
        ),
        (
            (LooseVersion('4.0.0'), 'xml'),
            0,
            [common.VARNISHADM_PATH, '-S', common.SECRETFILE_PATH, 'debug.health'],
            mocks.backend_list_mock_v4,
        ),
        (
            (LooseVersion('4.1.0'), 'xml'),
            1,
            [
                'sudo',
                common.VARNISHADM_PATH,
                '-T',
                common.DAEMON_ADDRESS,
                '-S',
                common.SECRETFILE_PATH,
                'backend.list',
                '-p',
            ],
            mocks.backend_list_mock_v4,
        ),
        (
            (LooseVersion('5.0.0'), 'json'),
            0,
            [
                common.VARNISHADM_PATH,
                '-T',
                common.DAEMON_ADDRESS,
                '-S',
                common.SECRETFILE_PATH,
                'backend.list',
                '-p',
            ],
            mocks.backend_list_mock_v5,
        ),
        (
            (LooseVersion('5.0.0'), 'json'),
            1,
            [
                'sudo',
                common.VARNISHADM_PATH,
                '-T',
                common.DAEMON_ADDRESS,
                '-S',
                common.SECRETFILE_PATH,
                'backend.list',
                '-p',
            ],
            mocks.backend_list_mock_v5,
        ),
        (
            (LooseVersion('6.5.0'), 'json'),
            0,
            [
                common.VARNISHADM_PATH,
                '-T',
                common.DAEMON_ADDRESS,
                '-S',
                common.SECRETFILE_PATH,
                'backend.list',
                '-p',
            ],
            mocks.backend_list_mock_v6_5,
        ),
        (
            (LooseVersion('6.5.0'), 'json'),
            1,
            [
                'sudo',
                common.VARNISHADM_PATH,
                '-T',
                common.DAEMON_ADDRESS,
                '-S',
                common.SECRETFILE_PATH,
                'backend.list',
                '-p',
            ],
            mocks.backend_list_mock_v6_5,
        ),
    ],
)
def test_command_line_healthy(
    mock_version, mock_geteuid, aggregator, instance, version, uuid, expected_cmd, output_mock
):
    """
    Test the Varnishadm output for version >= 4.x
    """
    instance['varnishadm'] = common.VARNISHADM_PATH
    instance['secretfile'] = common.SECRETFILE_PATH
    check = Varnish(common.CHECK_NAME, {}, [instance])

    mock_version.return_value = version
    mock_geteuid.return_value = uuid

    with mock.patch('datadog_checks.varnish.varnish.get_subprocess_output', side_effect=output_mock) as mock_subprocess:
        check.check(instance)
        args, _ = mock_subprocess.call_args
        assert args[0] == expected_cmd
    aggregator.assert_service_check(
        "varnish.backend_healthy", status=check.OK, tags=['backend:backend2', 'varnish_cluster:webs'], count=1
    )


@pytest.mark.parametrize(
    'original,expected', [('VBE.reload_20220530_163054_49600.default.conn', 'VBE.boot.default.conn'), ('MEMPOOL.busyobj.live', 'MEMPOOL.busyobj.live')]
)
def test_sanitize_metric_name(original, expected):
    transformed_name = sanitize_metric_name(original)
    assert expected == transformed_name
