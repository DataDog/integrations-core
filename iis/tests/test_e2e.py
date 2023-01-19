# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import subprocess
import six
import socket

from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_active_env
from datadog_checks.iis import IIS
from datadog_checks.iis.service_check import IIS_APPLICATION_POOL_STATE

from .common import CHECK_NAME


@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, instance):
    """
    Check should run without error if IIS is installed
    """
    aggregator = dd_agent_check(instance)
    if six.PY3:
        aggregator.assert_service_check('iis.windows.perf.health', IIS.OK)


@pytest.fixture
def iis_host(aggregator, dd_default_hostname):
    if six.PY2:
        # the python2 version of the check uses the configured hostname,
        # which is the hostnane of the docker host.
        return 'iis_host:{}'.format(socket.gethostname())
    else:
        # the python3 version of the check uses the perf counter server field,
        # which is the hostname of the container.
        hostname = run_command(['hostname'])
        return 'iis_host:{}'.format(hostname)


def normalize_tags(tags):
    if six.PY2:
        # The python2 version of the check calls self.normalize_tag
        a = AgentCheck()
        return [a.normalize_tag(tag) for tag in tags]
    else:
        return tags


def run_command(command):
    """
    Run a command in the docker container being used for E2E tests
    """
    container_name = 'dd_{}_{}'.format(CHECK_NAME, get_active_env())
    result = subprocess.check_output(
        ['docker', 'exec', container_name] + command,
    ).decode().strip()
    return result


def start_iis():
    app_pools = ['DefaultAppPool']
    sites = ['Default Web Site']

    for app_pool in app_pools:
        run_command(['powershell.exe', '-Command', 'Start-WebAppPool -Name "{}"'.format(app_pool)])
    for site in sites:
        run_command(['powershell.exe', '-Command', 'Start-IISSite -Name "{}"'.format(site)])


def stop_iis():
    app_pools = ['DefaultAppPool']
    sites = ['Default Web Site']

    for app_pool in app_pools:
        run_command(['powershell.exe', '-Command', 'if((Get-WebAppPoolState -Name "{app_pool}").Value -ne "Stopped") {{ Stop-WebAppPool -Name "{app_pool}" }}'.format(app_pool=app_pool)])
    for site in sites:
        run_command(['powershell.exe', '-Command', 'Stop-IISSite -Name "{}" -Confirm:$false'.format(site)])


@pytest.mark.e2e
def test_service_checks(dd_agent_check, aggregator, instance, iis_host):
    """
    Test that the site and app_pool service checks are correct for running and non-existent instances
    """
    start_iis()

    aggregator = dd_agent_check(instance)

    namespace_data = (
        (IIS.SITE, IIS.OK, ['Default Web Site']),
        (IIS.APP_POOL, IIS.OK, ['DefaultAppPool']),
        (IIS.SITE, IIS.CRITICAL, ['Non Existing Website']),
        (IIS.APP_POOL, IIS.CRITICAL, ['Non Existing App Pool']),
    )
    for namespace, status, values in namespace_data:
        for value in values:
            aggregator.assert_service_check(
                'iis.{}_up'.format(namespace), status, tags=normalize_tags(['{}:{}'.format(namespace, value), iis_host]), count=1
            )


@pytest.mark.e2e
def test_site_uptime(dd_agent_check, aggregator, instance, iis_host):
    """
    Assert that the site uptime goes to 0 when the site is stopped.
    The uptime is used to calculate the serive check for sites.
    """
    stop_iis()

    aggregator = dd_agent_check(instance)

    aggregator.assert_metric('iis.uptime', value=0, tags=normalize_tags(['site:Default Web Site', iis_host]))


@pytest.mark.e2e
def test_app_pool_status_running(dd_agent_check, aggregator, instance, iis_host):
    """
    Assert the app pool state when it is running.
    The status is used to calculate the serive check for app pools.
    """
    start_iis()

    aggregator = dd_agent_check(instance)

    value = IIS_APPLICATION_POOL_STATE['Running']
    assert value == 3
    aggregator.assert_metric('iis.app_pool.state', value=value, tags=normalize_tags(['app_pool:DefaultAppPool', iis_host]))


@pytest.mark.e2e
def test_app_pool_status_stopped(dd_agent_check, aggregator, instance, iis_host):
    """
    Assert the app pool state when it is stopped.
    The status is used to calculate the serive check for app pools.
    """
    stop_iis()

    aggregator = dd_agent_check(instance)

    value = IIS_APPLICATION_POOL_STATE['Disabled']
    assert value == 5
    aggregator.assert_metric('iis.app_pool.state', value=value, tags=normalize_tags(['app_pool:DefaultAppPool', iis_host]))
