# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import logging
import os

import pytest
import simplejson as json
from mock import MagicMock
from requests import Session

from datadog_checks.cisco_aci import CiscoACICheck
from datadog_checks.cisco_aci.api import Api, SessionWrapper
from datadog_checks.utils.containers import hash_mutable

from . import common
from .mock_sender import mock_send

log = logging.getLogger('test_cisco_aci')


class FakeSess(SessionWrapper):
    """ This mock:
     1. Takes the requested path and replace all special characters to underscore
     2. Fetch the corresponding hash from common.FIXTURE_LIST_FILE_MAP
     3. Returns the corresponding file content
     """

    def make_request(self, path):
        mock_path = path.replace('/', '_')
        mock_path = mock_path.replace('?', '_')
        mock_path = mock_path.replace('&', '_')
        mock_path = mock_path.replace('=', '_')
        mock_path = mock_path.replace(',', '_')
        mock_path = mock_path.replace('-', '_')
        mock_path = mock_path.replace('.', '_')
        mock_path = mock_path.replace('"', '_')
        mock_path = mock_path.replace('(', '_')
        mock_path = mock_path.replace(')', '_')
        mock_path = mock_path.replace('[', '_')
        mock_path = mock_path.replace(']', '_')
        mock_path = mock_path.replace('|', '_')
        mock_path = common.FIXTURE_LIST_FILE_MAP[mock_path]
        for p in common.ALL_FICTURE_DIR:
            path = os.path.join(p, mock_path)
            path += '.txt'

            try:
                log.info(os.listdir(p))
                with open(path, 'r') as f:
                    return json.loads(f.read())
            except Exception:
                continue
        return {"imdata": []}


@pytest.fixture
def session_mock():
    session = Session()
    session.send = mock_send
    fake_session_wrapper = FakeSess(common.ACI_URL, session, 'cookie')
    return fake_session_wrapper


def test_cisco(aggregator, session_mock):
    cisco_aci_check = CiscoACICheck(common.CHECK_NAME, {}, {})
    api = Api(
        common.ACI_URLS, common.USERNAME, password=common.PASSWORD, log=cisco_aci_check.log, sessions=[session_mock]
    )
    api._refresh_sessions = False
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
    session = MagicMock()
    session.send = MagicMock(side_effect=[unauthentified_response, login_response, valid_response])

    session_wrapper = SessionWrapper(aci_url=common.ACI_URL, log=MagicMock(), session=session, apic_cookie="cookie")

    api = Api(common.ACI_URLS, common.USERNAME, password=common.PASSWORD, sessions=[session_wrapper])
    api._refresh_sessions = False

    data = api.make_request("")
    # Assert that we retrieved the value from `valid_response.json()`
    assert data == {"foo": "bar"}

    session_calls = session.send._mock_call_args_list
    # Assert that the first call was to the ACI_URL
    assert session_calls[0].args[0].url == common.ACI_URL + "/"
    # Assert that the second call was to the login endpoint
    assert 'aaaLogin.xml' in session_calls[1].args[0].url
    # Assert that the last call was to the ACI_URL again
    assert session_calls[2].args[0].url == common.ACI_URL + "/"
