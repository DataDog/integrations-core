# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
import pytest
import logging
import simplejson as json
from requests import Session

from datadog_checks.cisco_aci import CiscoACICheck
from datadog_checks.cisco_aci.api import SessionWrapper, Api
from datadog_checks.utils.containers import hash_mutable

import conftest
from .common import FIXTURE_LIST_FILE_MAP

log = logging.getLogger('test_cisco_aci')


class FakeSess(SessionWrapper):
    """ This mock:
     1. Takes the requested path and replace all special characters to underscore
     2. Fetch the corresponding hash from FIXTURE_LIST_FILE_MAP
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
        mock_path = FIXTURE_LIST_FILE_MAP[mock_path]
        for p in conftest.ALL_FICTURE_DIR:
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
    setattr(session, 'send', conftest.mock_send)
    fake_session_wrapper = FakeSess(conftest.ACI_URL, session, 'cookie')
    return fake_session_wrapper


def test_cisco(aggregator, session_mock):
    cisco_aci_check = CiscoACICheck(conftest.CHECK_NAME, {}, {})
    api = Api(conftest.ACI_URLS, conftest.USERNAME,
              password=conftest.PASSWORD, log=cisco_aci_check.log, sessions=[session_mock])
    api._refresh_sessions = False
    cisco_aci_check._api_cache[hash_mutable(conftest.CONFIG)] = api

    cisco_aci_check.check(conftest.CONFIG)
