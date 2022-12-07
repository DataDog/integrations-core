# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dns_check import DNSCheck

from . import common


@pytest.fixture(scope="session")
def dd_environment():
    yield common.INSTANCE_INTEGRATION, common.E2E_METADATA


@pytest.fixture
def check():
    return DNSCheck('dns_check', {}, [common.INSTANCE_INTEGRATION])
