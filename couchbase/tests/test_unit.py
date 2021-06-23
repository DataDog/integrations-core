# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import mock
import pytest

from datadog_checks.couchbase import Couchbase


def test_camel_case_to_joined_lower(instance):
    couchbase = Couchbase('couchbase', {}, [instance])

    CAMEL_CASE_TEST_PAIRS = {
        'camelCase': 'camel_case',
        'FirstCapital': 'first_capital',
        'joined_lower': 'joined_lower',
        'joined_Upper1': 'joined_upper1',
        'Joined_upper2': 'joined_upper2',
        'Joined_Upper3': 'joined_upper3',
        '_leading_Underscore': 'leading_underscore',
        'Trailing_Underscore_': 'trailing_underscore',
        'DOubleCAps': 'd_ouble_c_aps',
        '@@@super--$$-Funky__$__$$%': 'super_funky',
    }

    for test_input, expected_output in CAMEL_CASE_TEST_PAIRS.items():
        test_output = couchbase.camel_case_to_joined_lower(test_input)
        assert test_output == expected_output, 'Input was {}, expected output was {}, actual output was {}'.format(
            test_input, expected_output, test_output
        )


def test_extract_seconds_value(instance):
    couchbase = Couchbase('couchbase', {}, [instance])

    EXTRACT_SECONDS_TEST_PAIRS = {
        '3.45s': 3.45,
        '12ms': 0.012,
        '700.5us': 0.0007005,
        u'733.364\u00c2s': 0.000733364,
        '0': 0,
    }

    for test_input, expected_output in EXTRACT_SECONDS_TEST_PAIRS.items():
        test_output = couchbase.extract_seconds_value(test_input)
        assert test_output == expected_output, 'Input was {}, expected output was {}, actual output was {}'.format(
            test_input, expected_output, test_output
        )


def test__get_query_monitoring_data(instance_query):
    """
    `query_monitoring_url` can potentially fail, be sure we don't raise when the
    endpoint is not reachable
    """
    couchbase = Couchbase('couchbase', {}, [instance_query])
    couchbase._get_query_monitoring_data()


@pytest.mark.parametrize(
    'test_case, extra_config, expected_http_kwargs',
    [
        (
            "new auth config",
            {'username': 'new_foo', 'password': 'bar', 'tls_verify': False},
            {'auth': ('new_foo', 'bar'), 'verify': False},
        ),
        ("legacy config", {'user': 'new_foo', 'ssl_verify': False}, {'auth': ('new_foo', 'password'), 'verify': False}),
    ],
)
def test_config(test_case, extra_config, expected_http_kwargs, instance):
    instance = deepcopy(instance)
    instance.update(extra_config)
    check = Couchbase('couchbase', {}, [instance])

    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.return_value = mock.MagicMock(status_code=200)

        check.check(instance)

        http_wargs = dict(
            auth=mock.ANY, cert=mock.ANY, headers=mock.ANY, proxies=mock.ANY, timeout=mock.ANY, verify=mock.ANY
        )
        http_wargs.update(expected_http_kwargs)
        r.get.assert_called_with('http://localhost:8091/pools/default/tasks', **http_wargs)
