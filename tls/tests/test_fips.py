# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

import pytest

from datadog_checks.tls import TLSCheck
from datadog_checks.tls.const import (
    SERVICE_CHECK_CAN_CONNECT,
    SERVICE_CHECK_VALIDATION,
)


@pytest.mark.e2e
@pytest.mark.fips_off
def test_connection_before_fips(clean_fips_environment, dd_fips_environment, dd_agent_check, instance_e2e_fips):
    """
    Connection to the FIPS server before enabling FIPS mode should succeed.
    """
    aggregator = dd_agent_check(instance_e2e_fips)
    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=TLSCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=TLSCheck.OK, count=1)


@pytest.mark.e2e
@pytest.mark.fips_off
def test_connection_before_non_fips(clean_fips_environment, dd_fips_environment, dd_agent_check, instance_e2e_non_fips):
    """
    Connection to the non-FIPS server before enabling FIPS mode should succeed.
    """
    aggregator = dd_agent_check(instance_e2e_non_fips)
    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=TLSCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=TLSCheck.OK, count=1)


@pytest.mark.e2e
@pytest.mark.fips_on
def test_connection_after_fips(clean_fips_environment, dd_fips_environment, dd_agent_check, instance_e2e_fips):
    """
    Connection to the FIPS server after enabling FIPS mode should succeed.
    """
    aggregator = dd_agent_check(instance_e2e_fips)
    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=TLSCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=TLSCheck.OK, count=1)


@pytest.mark.e2e
@pytest.mark.fips_on
def test_connection_after_non_fips(clean_fips_environment, dd_fips_environment, dd_agent_check, instance_e2e_non_fips):
    """
    Connection to the non-FIPS server after enabling FIPS mode should fail.
    """
    aggregator = dd_agent_check(instance_e2e_non_fips)
    aggregator.assert_service_check(
        SERVICE_CHECK_VALIDATION,
        message="[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] ssl/tls alert handshake failure (_ssl.c:1000)",
    )
