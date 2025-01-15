# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

import pytest

from datadog_checks.fips_test import FIPSTestCheck
from datadog_checks.fips_test.const import (
    SERVICE_CHECK_HTTP,
    SERVICE_CHECK_RMI,
    SERVICE_CHECK_SOCKET,
    SERVICE_CHECK_SSH,
)


@pytest.mark.e2e
@pytest.mark.fips_off
@pytest.mark.parametrize('dd_environment', ['fips'], indirect=True)
def test_connection_before_fips(clean_fips_environment, dd_environment, dd_agent_check, instance_fips):
    """
    Connection to the FIPS servers before enabling FIPS mode should succeed.
    """
    aggregator = dd_agent_check(instance_fips)
    aggregator.assert_service_check(SERVICE_CHECK_HTTP, status=FIPSTestCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_RMI, status=FIPSTestCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_SOCKET, status=FIPSTestCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_SSH, status=FIPSTestCheck.OK, count=1)


@pytest.mark.e2e
@pytest.mark.fips_off
@pytest.mark.parametrize('dd_environment', ['non-fips'], indirect=True)
def test_connection_before_non_fips(clean_fips_environment, dd_environment, dd_agent_check, instance_non_fips):
    """
    Connection to the non FIPS servers before enabling FIPS mode should succeed.
    """
    aggregator = dd_agent_check(instance_non_fips)
    aggregator.assert_service_check(SERVICE_CHECK_HTTP, status=FIPSTestCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_RMI, status=FIPSTestCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_SOCKET, status=FIPSTestCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_SSH, status=FIPSTestCheck.OK, count=1)


@pytest.mark.e2e
@pytest.mark.fips_on
@pytest.mark.parametrize('dd_environment', ['fips'], indirect=True)
def test_connection_fips(clean_fips_environment, dd_environment, dd_agent_check, instance_fips):
    """
    Connection to the FIPS servers after enabling FIPS mode should succeed.
    """
    aggregator = dd_agent_check(instance_fips)
    aggregator.assert_service_check(SERVICE_CHECK_HTTP, status=FIPSTestCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_RMI, status=FIPSTestCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_SOCKET, status=FIPSTestCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_SSH, status=FIPSTestCheck.OK, count=1)


@pytest.mark.e2e
@pytest.mark.fips_on
@pytest.mark.parametrize('dd_environment', ['non-fips'], indirect=True)
def test_connection_non_fips(clean_fips_environment, dd_environment, dd_agent_check, instance_non_fips):
    """
    Connection to the non-FIPS servers after enabling FIPS mode should fail.
    """
    aggregator = dd_agent_check(instance_non_fips)
    aggregator.assert_service_check(SERVICE_CHECK_HTTP, status=FIPSTestCheck.CRITICAL, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_RMI, status=FIPSTestCheck.CRITICAL, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_SOCKET, status=FIPSTestCheck.CRITICAL, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_SSH, status=FIPSTestCheck.CRITICAL, count=1)
