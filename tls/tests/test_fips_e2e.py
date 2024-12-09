# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import Any  # noqa: F401

import pytest

from datadog_checks.tls import TLSCheck
from datadog_checks.tls.const import (
    SERVICE_CHECK_CAN_CONNECT,
    SERVICE_CHECK_EXPIRATION,
    SERVICE_CHECK_VALIDATION,
    SERVICE_CHECK_VERSION,
)


@pytest.fixture(scope="function")
def clean_environment():
    os.environ["GOFIPS"] = "0"
    os.environ["OPENSSL_CONF"] = ""
    os.environ["OPENSSL_MODULES"] = ""
    yield


@pytest.mark.e2e
def test_connection_before_fips(clean_environment, dd_fips_environment, dd_agent_check, instance_e2e_fips):
    """
    Test connection to the FIPS server before enabling FIPS mode.
    """
    aggregator = dd_agent_check(instance_e2e_fips)
    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=TLSCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=TLSCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=TLSCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=TLSCheck.OK, count=1)



@pytest.mark.e2e
def test_connection_before_non_fips(clean_environment, dd_fips_environment, dd_agent_check, instance_e2e_non_fips):
    """
    Test connection to the non-FIPS server before enabling FIPS mode.
    """
    aggregator = dd_agent_check(instance_e2e_non_fips)
    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=TLSCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=TLSCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=TLSCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=TLSCheck.OK, count=1)


@pytest.mark.e2e
def test_connection_after_fips(clean_environment, dd_fips_environment, dd_agent_check, instance_e2e_fips):
    """
    Test connection to the FIPS server after enabling FIPS mode.
    """
    os.environ["GOFIPS"] = "1"
    aggregator = dd_agent_check(instance_e2e_fips)
    aggregator.assert_service_check(SERVICE_CHECK_CAN_CONNECT, status=TLSCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VERSION, status=TLSCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=TLSCheck.OK, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_EXPIRATION, status=TLSCheck.OK, count=1)


@pytest.mark.e2e
def test_connection_after_non_fips(clean_environment, dd_fips_environment, dd_agent_check, instance_e2e_non_fips):
    """
    Test connection to the non-FIPS server after enabling FIPS mode.
    """
    os.environ["GOFIPS"] = "1"
    aggregator = dd_agent_check(instance_e2e_non_fips)
    aggregator.assert_service_check(
        SERVICE_CHECK_VALIDATION,
        message="[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:1006)",
    )
