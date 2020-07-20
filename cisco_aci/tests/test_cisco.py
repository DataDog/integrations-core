# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
from copy import deepcopy

import pytest
from mock import MagicMock

from datadog_checks.base.utils.containers import hash_mutable
from datadog_checks.cisco_aci import CiscoACICheck
from datadog_checks.cisco_aci.api import Api, SessionWrapper

from . import common


def test_cisco(aggregator):
    cisco_aci_check = CiscoACICheck(common.CHECK_NAME, {}, {})
    api = Api(common.ACI_URLS, cisco_aci_check.http, common.USERNAME, password=common.PASSWORD, log=cisco_aci_check.log)
    api.wrapper_factory = common.FakeSessionWrapper
    cisco_aci_check._api_cache[hash_mutable(common.CONFIG)] = api

    cisco_aci_check.check(common.CONFIG)


@pytest.mark.parametrize(
    ' api_kwargs',
    [
        pytest.param({'password': common.PASSWORD}, id='login with password'),
        pytest.param(
            {'cert_name': 'foo', 'cert_key': open(os.path.join(common.CERTIFICATE_DIR, 'cert.pem'), 'rb').read()},
            id='login with cert',
        ),
    ],
)
def test_recover_from_expired_token(aggregator, api_kwargs):
    # First api answers with 403 to force the check to re-authenticate
    unauthentified_response = MagicMock(status_code=403)
    # Api answer when a request is being made to the login endpoint
    login_response = MagicMock()
    # Third api answer, when the check retries the initial endpoint but is now authenticated
    valid_response = MagicMock()
    valid_response.json = MagicMock(return_value={"foo": "bar"})
    http = MagicMock()
    http.post = MagicMock(side_effect=[login_response])
    http.get = MagicMock(side_effect=[unauthentified_response, valid_response])

    session_wrapper = SessionWrapper(aci_url=common.ACI_URL, http=http, log=MagicMock())
    session_wrapper.apic_cookie = "cookie"

    api = Api(common.ACI_URLS, http, common.USERNAME, **api_kwargs)

    api.sessions = {common.ACI_URL: session_wrapper}

    data = api.make_request("")

    # Assert that we retrieved the value from `valid_response.json()`
    assert data == {"foo": "bar"}

    get_calls = http.get._mock_call_args_list
    post_calls = http.post._mock_call_args_list

    # Assert that the first call was to the ACI_URL
    assert get_calls[0].args[0] == common.ACI_URL
    if 'password' in api_kwargs:
        # Assert that the second call was to the login endpoint
        assert 'aaaLogin.xml' in post_calls[0].args[0]

    # Assert that the last call was to the ACI_URL again
    assert get_calls[1].args[0] == common.ACI_URL

    # Assert session correctly renewed
    assert len(api.sessions) == 1  # check the number of sessions doesn't grow
    assert api.sessions[common.ACI_URL] != session_wrapper  # check session renewed

    # Assert cookie to check the session changed
    assert get_calls[0].kwargs['headers']['Cookie'] == 'cookie'
    assert get_calls[1].kwargs['headers']['Cookie'] != 'cookie'


@pytest.mark.parametrize(
    'extra_config, expected_http_kwargs',
    [
        pytest.param({'pwd': 'foobar'}, {'auth': (common.USERNAME, 'foobar'), 'verify': True}, id='new auth config'),
        pytest.param({'ssl_verify': True}, {'verify': True}, id='legacy ssl verify config True'),
        pytest.param({'ssl_verify': False}, {'verify': False}, id='legacy ssl verify config False'),
    ],
)
def test_config(aggregator, extra_config, expected_http_kwargs):
    instance = deepcopy(common.CONFIG_WITH_TAGS)
    instance.update(extra_config)
    check = CiscoACICheck(common.CHECK_NAME, {}, [instance])

    actual_options = {k: v for k, v in check.http.options.items() if k in expected_http_kwargs}
    assert expected_http_kwargs == actual_options
