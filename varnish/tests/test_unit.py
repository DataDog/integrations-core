# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from distutils.version import LooseVersion

import mock
from . import mocks
from . import common
from datadog_checks.varnish import Varnish


@mock.patch('datadog_checks.varnish.varnish.geteuid')
@mock.patch('datadog_checks.varnish.varnish.Varnish._get_version_info')
@mock.patch('datadog_checks.varnish.varnish.get_subprocess_output', side_effect=mocks.backend_manual_unhealthy_mock)
def test_command_line_manually_unhealthy(mock_subprocess, mock_version, mock_geteuid, aggregator, instance):
    """
    Test the varnishadm output for version >= 4.x with manually set health
    """
    instance['varnishadm'] = common.VARNISHADM_PATH
    instance['secretfile'] = common.SECRETFILE_PATH
    check = Varnish(common.CHECK_NAME, {}, [instance])

    mock_version.return_value = LooseVersion('4.0.0'), 'xml'
    mock_geteuid.return_value = 0
    check.check(instance)

    args, _ = mock_subprocess.call_args
    assert args[0] == [common.VARNISHADM_PATH, '-S', common.SECRETFILE_PATH, 'debug.health']
    aggregator.assert_service_check(
        "varnish.backend_healthy", status=check.CRITICAL, tags=['backend:default', 'varnish_cluster:webs'], count=1
    )

    mock_version.return_value = LooseVersion('4.1.0'), 'xml'
    mock_geteuid.return_value = 1

    check.check(instance)
    args, _ = mock_subprocess.call_args
    assert args[0] == [
        'sudo',
        common.VARNISHADM_PATH,
        '-T',
        common.DAEMON_ADDRESS,
        '-S',
        common.SECRETFILE_PATH,
        'backend.list',
        '-p',
    ]


@mock.patch('datadog_checks.varnish.varnish.geteuid')
@mock.patch('datadog_checks.varnish.varnish.Varnish._get_version_info')
@mock.patch('datadog_checks.varnish.varnish.get_subprocess_output', side_effect=mocks.backend_list_mock)
def test_command_line_post_varnish4(mock_subprocess, mock_version, mock_geteuid, aggregator, instance):
    """
    Test the Varnishadm output for version >= 4.x
    """
    instance['varnishadm'] = common.VARNISHADM_PATH
    instance['secretfile'] = common.SECRETFILE_PATH
    check = Varnish(common.CHECK_NAME, {}, [instance])

    mock_version.return_value = LooseVersion('4.0.0'), 'xml'
    mock_geteuid.return_value = 0
    check.check(instance)

    args, _ = mock_subprocess.call_args
    assert args[0] == [common.VARNISHADM_PATH, '-S', common.SECRETFILE_PATH, 'debug.health']
    aggregator.assert_service_check(
        "varnish.backend_healthy", status=check.OK, tags=['backend:backend2', 'varnish_cluster:webs'], count=1
    )

    mock_version.return_value = LooseVersion('4.1.0'), 'xml'
    mock_geteuid.return_value = 1

    check.check(instance)
    args, _ = mock_subprocess.call_args
    assert args[0] == [
        'sudo',
        common.VARNISHADM_PATH,
        '-T',
        common.DAEMON_ADDRESS,
        '-S',
        common.SECRETFILE_PATH,
        'backend.list',
        '-p',
    ]


@mock.patch('datadog_checks.varnish.varnish.geteuid')
@mock.patch('datadog_checks.varnish.varnish.Varnish._get_version_info')
@mock.patch('datadog_checks.varnish.varnish.get_subprocess_output', side_effect=mocks.backend_list_mock_v5)
def test_command_line_post_varnish5(mock_subprocess, mock_version, mock_geteuid, aggregator, instance):
    """
    Test the Varnishadm output for version >= 5.x
    """
    instance['varnishadm'] = common.VARNISHADM_PATH
    instance['secretfile'] = common.SECRETFILE_PATH
    check = Varnish(common.CHECK_NAME, {}, [instance])

    mock_version.return_value = LooseVersion('5.0.0'), 'json'
    mock_geteuid.return_value = 0
    check.check(instance)

    args, _ = mock_subprocess.call_args
    assert args[0] == [
        common.VARNISHADM_PATH,
        '-T',
        common.DAEMON_ADDRESS,
        '-S',
        common.SECRETFILE_PATH,
        'backend.list',
        '-p',
    ]
    aggregator.assert_service_check(
        "varnish.backend_healthy", status=check.OK, tags=['backend:backend2', 'varnish_cluster:webs'], count=1
    )

    mock_version.return_value = LooseVersion('5.0.0'), 'json'
    mock_geteuid.return_value = 1

    check.check(instance)
    args, _ = mock_subprocess.call_args
    assert args[0] == [
        'sudo',
        common.VARNISHADM_PATH,
        '-T',
        common.DAEMON_ADDRESS,
        '-S',
        common.SECRETFILE_PATH,
        'backend.list',
        '-p',
    ]


@mock.patch('datadog_checks.varnish.varnish.geteuid')
@mock.patch('datadog_checks.varnish.varnish.Varnish._get_version_info')
@mock.patch('datadog_checks.varnish.varnish.get_subprocess_output', side_effect=mocks.backend_list_mock_v6_5)
def test_command_line_post_varnish6_5(mock_subprocess, mock_version, mock_geteuid, aggregator, instance):
    """
    Test the Varnishadm output for version >= 6.5
    """
    instance['varnishadm'] = common.VARNISHADM_PATH
    instance['secretfile'] = common.SECRETFILE_PATH
    check = Varnish(common.CHECK_NAME, {}, [instance])

    mock_version.return_value = LooseVersion('6.5.0'), 'json'
    mock_geteuid.return_value = 0
    check.check(instance)

    args, _ = mock_subprocess.call_args
    assert args[0] == [
        common.VARNISHADM_PATH,
        '-T',
        common.DAEMON_ADDRESS,
        '-S',
        common.SECRETFILE_PATH,
        'backend.list',
        '-p',
    ]
    aggregator.assert_service_check(
        "varnish.backend_healthy", status=check.OK, tags=['backend:backend2', 'varnish_cluster:webs'], count=1
    )

    mock_version.return_value = LooseVersion('6.5.0'), 'json'
    mock_geteuid.return_value = 1

    check.check(instance)
    args, _ = mock_subprocess.call_args
    assert args[0] == [
        'sudo',
        common.VARNISHADM_PATH,
        '-T',
        common.DAEMON_ADDRESS,
        '-S',
        common.SECRETFILE_PATH,
        'backend.list',
        '-p',
    ]


@mock.patch('datadog_checks.varnish.varnish.geteuid')
@mock.patch('datadog_checks.varnish.varnish.Varnish._get_version_info')
@mock.patch('datadog_checks.varnish.varnish.get_subprocess_output', side_effect=mocks.debug_health_mock)
def test_command_line(mock_subprocess, mock_version, mock_geteuid, aggregator, instance):
    """
    Test the varnishadm output for Varnish < 4.x
    """
    instance['varnishadm'] = common.VARNISHADM_PATH
    instance['secretfile'] = common.SECRETFILE_PATH
    check = Varnish(common.CHECK_NAME, {}, [instance])

    mock_version.return_value = LooseVersion("3.9.0"), 'xml'
    mock_geteuid.return_value = 0
    check.check(instance)

    args, _ = mock_subprocess.call_args
    assert args[0] == [common.VARNISHADM_PATH, '-S', common.SECRETFILE_PATH, 'debug.health']
    aggregator.assert_service_check(
        "varnish.backend_healthy", status=check.OK, tags=['backend:default', 'varnish_cluster:webs'], count=1
    )
