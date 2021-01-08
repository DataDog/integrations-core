# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from distutils.version import LooseVersion

import mock

from datadog_checks.base import ensure_unicode

from . import common


# Varnish < 4.x varnishadm output
def debug_health_mock(*args, **kwargs):
    if common.VARNISHADM_PATH in args[0]:
        fpath = os.path.join(common.FIXTURE_DIR, "debug_health_output")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0
    else:
        fpath = os.path.join(common.FIXTURE_DIR, "stats_output")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0


# Varnish >= 4.x && <= 5.x varnishadm output
def backend_list_mock(*args, **kwargs):
    if common.VARNISHADM_PATH in args[0]:
        fpath = os.path.join(common.FIXTURE_DIR, "backend_list_output")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0
    else:
        fpath = os.path.join(common.FIXTURE_DIR, "stats_output")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0


# Varnish >= 5.x varnishadm output
def backend_list_mock_v5(*args, **kwargs):
    if common.VARNISHADM_PATH in args[0]:
        fpath = os.path.join(common.FIXTURE_DIR, "backend_list_output")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0
    else:
        fpath = os.path.join(common.FIXTURE_DIR, "stats_output_json")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0


# Varnish >= 6.5 varnishadm output
def backend_list_mock_v6_5(*args, **kwargs):
    if common.VARNISHADM_PATH in args[0]:
        fpath = os.path.join(common.FIXTURE_DIR, "backend_list_output")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0
    else:
        fpath = os.path.join(common.FIXTURE_DIR, "stats_output_json_6.5")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0


# Varnish >= 4.x && <= 5.x Varnishadm manually set backend to sick
def backend_manual_unhealthy_mock(*args, **kwargs):
    if common.VARNISHADM_PATH in args[0]:
        fpath = os.path.join(common.FIXTURE_DIR, "backend_manually_unhealthy")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0
    else:
        fpath = os.path.join(common.FIXTURE_DIR, "stats_output")
        with open(fpath) as f:
            return ensure_unicode(f.read()), u"", 0


@mock.patch('datadog_checks.varnish.varnish.geteuid')
@mock.patch('datadog_checks.varnish.varnish.Varnish._get_version_info')
@mock.patch('datadog_checks.varnish.varnish.get_subprocess_output', side_effect=backend_manual_unhealthy_mock)
def test_command_line_manually_unhealthy(mock_subprocess, mock_version, mock_geteuid, aggregator, check, instance):
    """
    Test the varnishadm output for version >= 4.x with manually set health
    """
    mock_version.return_value = LooseVersion('4.0.0'), 'xml'
    mock_geteuid.return_value = 0

    instance['varnishadm'] = common.VARNISHADM_PATH
    instance['secretfile'] = common.SECRETFILE_PATH

    check.check(instance)
    args, _ = mock_subprocess.call_args
    assert args[0] == [common.VARNISHADM_PATH, '-S', common.SECRETFILE_PATH, 'debug.health']
    aggregator.assert_service_check(
        "varnish.backend_healthy", status=check.CRITICAL, tags=['backend:default', 'cluster:webs'], count=1
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
@mock.patch('datadog_checks.varnish.varnish.get_subprocess_output', side_effect=backend_list_mock)
def test_command_line_post_varnish4(mock_subprocess, mock_version, mock_geteuid, aggregator, check, instance):
    """
    Test the Varnishadm output for version >= 4.x
    """
    mock_version.return_value = LooseVersion('4.0.0'), 'xml'
    mock_geteuid.return_value = 0

    instance['varnishadm'] = common.VARNISHADM_PATH
    instance['secretfile'] = common.SECRETFILE_PATH

    check.check(instance)
    args, _ = mock_subprocess.call_args
    assert args[0] == [common.VARNISHADM_PATH, '-S', common.SECRETFILE_PATH, 'debug.health']
    aggregator.assert_service_check(
        "varnish.backend_healthy", status=check.OK, tags=['backend:backend2', 'cluster:webs'], count=1
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
@mock.patch('datadog_checks.varnish.varnish.get_subprocess_output', side_effect=backend_list_mock_v5)
def test_command_line_post_varnish5(mock_subprocess, mock_version, mock_geteuid, aggregator, check, instance):
    """
    Test the Varnishadm output for version >= 5.x
    """
    mock_version.return_value = LooseVersion('5.0.0'), 'json'
    mock_geteuid.return_value = 0

    instance['varnishadm'] = common.VARNISHADM_PATH
    instance['secretfile'] = common.SECRETFILE_PATH

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
        "varnish.backend_healthy", status=check.OK, tags=['backend:backend2', 'cluster:webs'], count=1
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
@mock.patch('datadog_checks.varnish.varnish.get_subprocess_output', side_effect=backend_list_mock_v6_5)
def test_command_line_post_varnish6_5(mock_subprocess, mock_version, mock_geteuid, aggregator, check, instance):
    """
    Test the Varnishadm output for version >= 6.5
    """
    mock_version.return_value = LooseVersion('6.5.0'), 'json'
    mock_geteuid.return_value = 0

    instance['varnishadm'] = common.VARNISHADM_PATH
    instance['secretfile'] = common.SECRETFILE_PATH

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
        "varnish.backend_healthy", status=check.OK, tags=['backend:backend2', 'cluster:webs'], count=1
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
@mock.patch('datadog_checks.varnish.varnish.get_subprocess_output', side_effect=debug_health_mock)
def test_command_line(mock_subprocess, mock_version, mock_geteuid, aggregator, check, instance):
    """
    Test the varnishadm output for Varnish < 4.x
    """
    mock_version.return_value = LooseVersion("3.9.0"), 'xml'
    mock_geteuid.return_value = 0

    instance['varnishadm'] = common.VARNISHADM_PATH
    instance['secretfile'] = common.SECRETFILE_PATH

    check.check(instance)
    args, _ = mock_subprocess.call_args
    assert args[0] == [common.VARNISHADM_PATH, '-S', common.SECRETFILE_PATH, 'debug.health']
    aggregator.assert_service_check(
        "varnish.backend_healthy", status=check.OK, tags=['backend:default', 'cluster:webs'], count=1
    )
