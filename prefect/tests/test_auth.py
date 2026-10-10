# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from base64 import b64encode

import pytest
from requests import Response

from datadog_checks.base import ConfigurationError
from datadog_checks.prefect import PrefectCheck

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'credentials,expected',
    [
        ({'auth_string': 'platform:secret'}, 'platform:secret'),
        ({'auth_string': 'platform:secret', 'auth_type': 'BASIC'}, 'platform:secret'),
        ({'auth_string': 'platform:secret', 'auth_type': 'bAsIc'}, 'platform:secret'),
        ({'auth_string': 'platform:secret:with:colons'}, 'platform:secret:with:colons'),
        ({'username': 'platform', 'password': 'secret'}, 'platform:secret'),
        ({}, None),
    ],
)
def test_authentication_header(credentials: dict[str, str], expected: str | None, mocker):
    # A secured Prefect server must receive the same credentials in either supported configuration format.
    url = 'https://prefect.example/api'
    check = PrefectCheck('prefect', {}, [{'prefect_url': url, **credentials}])
    check.run_check_initializations()
    response = Response()
    response.status_code = 200
    response._content = b'true'
    send = mocker.patch('requests.sessions.Session.send', return_value=response)

    assert check.client.get('/health') is True

    request = send.call_args.args[0]
    assert request.url == f'{url}/health'
    header = request.headers.get('Authorization')
    if expected is None:
        assert header is None
    else:
        assert header == f'Basic {b64encode(expected.encode()).decode()}'


@pytest.mark.parametrize(
    'credentials',
    [
        {'auth_string': 'missing-separator'},
        {'auth_string': ':secret'},
        {'auth_string': 'platform:'},
        {'auth_string': 'platform:secret', 'username': 'other'},
        {'auth_string': 'platform:secret', 'password': 'other'},
        {'auth_string': 'platform:secret', 'auth_type': 'digest'},
    ],
)
def test_invalid_authentication_rejected(credentials: dict[str, str], mocker):
    check = PrefectCheck('prefect', {}, [{'prefect_url': 'https://prefect.example/api', **credentials}])
    send = mocker.patch('requests.sessions.Session.send')

    with pytest.raises(ConfigurationError) as error:
        check.run_check_initializations()

    assert 'secret' not in str(error.value)
    send.assert_not_called()
