# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import mock
import pytest

from datadog_checks.couch import CouchDb

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
