# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.etcd import Etcd

CHECK_NAME = 'etcd'


@pytest.mark.parametrize(
    'test_case, extra_config, expected_http_kwargs',
    [
        ("new auth config", {'username': 'new_foo', 'password': 'new_bar'}, {'auth': ('new_foo', 'new_bar')}),
        ("legacy ssl config True", {'ssl_verify': True}, {'verify': True}),
        ("legacy ssl config False", {'ssl_verify': False}, {'verify': False}),
        ("legacy ssl config unset", {}, {'verify': False}),
        ("timeout", {'prometheus_timeout': 100}, {'timeout': (100.0, 100.0)}),
    ],
)
def test_config(instance, test_case, extra_config, expected_http_kwargs):
    instance.update(extra_config)
    check = Etcd(CHECK_NAME, {}, [instance])

    for key, value in expected_http_kwargs.items():
        assert check.http.options[key] == value
