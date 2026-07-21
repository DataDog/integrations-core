# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from urllib.parse import urlparse

import pytest

from datadog_checks.vault import Vault
from datadog_checks.vault.errors import ApiUnreachable

from .common import INSTANCES

# These tests make real outbound network calls (not the mocked unit suite) and don't use the Vault container.
pytestmark = pytest.mark.integration


@pytest.mark.parametrize('use_openmetrics', [False, True], indirect=True)
def test_service_check_connect_fail(aggregator, dd_run_check, use_openmetrics):
    instance = {'use_openmetrics': use_openmetrics}
    instance.update(INSTANCES['bad_url'])
    c = Vault(Vault.CHECK_NAME, {}, [instance])

    if use_openmetrics:
        hostname = urlparse(instance['api_url']).hostname
        expected_exception = r'Connection to {} timed out'.format(hostname)

    else:
        expected_exception = r'^Vault endpoint `{}.+?` timed out after 1\.0 seconds$'.format(
            re.escape(instance['api_url'])
        )

    with pytest.raises(
        Exception,
        match=expected_exception,
    ):
        dd_run_check(c, extract_message=True)

    aggregator.assert_service_check(
        Vault.SERVICE_CHECK_CONNECT,
        status=Vault.CRITICAL,
        tags=['instance:foobar', 'api_url:http://1.2.3.4:555/v1'],
        count=1,
    )


def test_api_unreachable():
    instance = {'use_openmetrics': False}
    instance.update(INSTANCES['main'])
    c = Vault(Vault.CHECK_NAME, {}, [instance])

    with pytest.raises(ApiUnreachable, match=r"Error accessing Vault endpoint.*"):
        c.access_api("http://foo.bar", ignore_status_codes=None)
