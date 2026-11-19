# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.prefect import PrefectCheck

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'credentials,expected',
    [
        ({'prefect_userpass': 'platform:secret'}, 'platform:secret'),
        ({'prefect_userpass': 'platform:secret', 'auth_type': 'BASIC'}, 'platform:secret'),
        ({'prefect_userpass': 'platform:secret', 'auth_type': 'bAsIc'}, 'platform:secret'),
        ({'prefect_userpass': 'platform:secret:with:colons'}, 'platform:secret:with:colons'),
        ({'username': 'platform', 'password': 'secret'}, 'platform:secret'),
        ({}, None),
    ],
)
def test_authentication_credentials(credentials: dict[str, str], expected: str | None):
    # A secured Prefect server must receive the same credentials in either supported configuration format.
    check = PrefectCheck('prefect', {}, [{'prefect_url': 'https://prefect.example/api', **credentials}])
    check.run_check_initializations()

    assert check.client.http is check.http
    assert check.http.options['auth'] == (None if expected is None else tuple(expected.split(':', 1)))


@pytest.mark.parametrize(
    'credentials',
    [
        {'prefect_userpass': 'missing-separator'},
        {'prefect_userpass': ':secret'},
        {'prefect_userpass': 'platform:'},
        {'prefect_userpass': 'platform:secret', 'username': 'other'},
        {'prefect_userpass': 'platform:secret', 'password': 'other'},
        {'prefect_userpass': 'platform:secret', 'auth_type': 'digest'},
    ],
)
def test_invalid_authentication_rejected(credentials: dict[str, str], fake_http):
    check = PrefectCheck('prefect', {}, [{'prefect_url': 'https://prefect.example/api', **credentials}])

    with pytest.raises(ConfigurationError) as error:
        check.run_check_initializations()

    assert 'secret' not in str(error.value)
    assert fake_http.requests == []
