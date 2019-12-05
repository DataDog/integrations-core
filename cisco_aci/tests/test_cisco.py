# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from mock import MagicMock

from datadog_checks.cisco_aci import CiscoACICheck
from datadog_checks.cisco_aci.api import Api, SessionWrapper
from datadog_checks.utils.containers import hash_mutable

from . import common


def test_cisco(aggregator):
    cisco_aci_check = CiscoACICheck(common.CHECK_NAME, {}, {})
    api = Api(common.ACI_URLS, cisco_aci_check.http, common.USERNAME, password=common.PASSWORD, log=cisco_aci_check.log)
    api.wrapper_factory = common.FakeSessionWrapper
    cisco_aci_check._api_cache[hash_mutable(common.CONFIG)] = api

    cisco_aci_check.check(common.CONFIG)


def test_recover_from_expired_token(aggregator):
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

    api = Api(common.ACI_URLS, http, common.USERNAME, password=common.PASSWORD)

    api.sessions = [session_wrapper]

    data = api.make_request("")
    # Assert that we retrieved the value from `valid_response.json()`
    assert data == {"foo": "bar"}

    get_calls = http.get._mock_call_args_list
    post_calls = http.post._mock_call_args_list
    # Assert that the first call was to the ACI_URL
    assert get_calls[0].args[0] == common.ACI_URL
    # Assert that the second call was to the login endpoint
    assert 'aaaLogin.xml' in post_calls[0].args[0]
    # Assert that the last call was to the ACI_URL again
    assert get_calls[1].args[0] == common.ACI_URL
