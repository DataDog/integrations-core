# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy
from unittest.mock import MagicMock

import mock
import pytest

from datadog_checks.couch import CouchDb
from datadog_checks.couch.couch import CouchDB2

from . import common


@pytest.mark.parametrize(
    'test_case, extra_config, expected_http_kwargs',
    [
        (
            "legacy auth config",
            {'user': 'legacy_foo', 'password': 'legacy_bar'},
            {'auth': ('legacy_foo', 'legacy_bar')},
        ),
        ("new auth config", {'username': 'new_foo', 'password': 'new_bar'}, {'auth': ('new_foo', 'new_bar')}),
        ("timeout", {'timeout': 17}, {'timeout': (17, 17)}),
    ],
)
def test_config(test_case, extra_config, expected_http_kwargs):
    instance = deepcopy(common.BASIC_CONFIG)
    instance.update(extra_config)
    check = CouchDb(common.CHECK_NAME, {}, instances=[instance])

    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.return_value = mock.MagicMock(status_code=200, content='{}')

        check.check(instance)

        http_wargs = {
            'auth': mock.ANY,
            'cert': mock.ANY,
            'headers': mock.ANY,
            'proxies': mock.ANY,
            'timeout': mock.ANY,
            'verify': mock.ANY,
            'allow_redirects': mock.ANY,
        }
        http_wargs.update(expected_http_kwargs)

        r.get.assert_called_with('http://{}:5984/_all_dbs/'.format(common.HOST), **http_wargs)


def test_new_version_system_metrics(load_test_data):
    # Testing the _build_system_metrics method I'm feeding it a json that has a the updated
    # keys that was added in version 3.4 that was causing the check to break. The idea here
    # is that I'm going to give the method the json then assert that it's able to go through
    # it thhorougly by the number of function calls and debug log calls.

    # Mock everything needed for the function to run
    mock_agent_check = MagicMock()
    mock_agent_check.gauge = MagicMock()
    mock_agent_check.log = MagicMock()

    couchdb_check = CouchDB2(mock_agent_check)
    tags = ["test:tag"]

    # The fixture file json is loaded as a fixture in the confest.py file
    couchdb_check._build_system_metrics(load_test_data, tags)

    assert mock_agent_check.gauge.call_count >= 183
    mock_agent_check.log.debug.assert_any_call("Skipping distribution events")
