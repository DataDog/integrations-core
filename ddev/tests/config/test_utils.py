# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.config.utils import _walk_config


@pytest.mark.parametrize(
    'config, glob, expected',
    [
        pytest.param({}, 'github.token', [], id='empty-config'),
        pytest.param({'github': 9000}, 'github.token', [], id='wrong-section-type'),
        pytest.param({'github': {}}, 'github.token', [], id='missing-leaf-key'),
        pytest.param({'github': {'token': 'abc'}}, 'github.token', [('token', 'abc')], id='simple-match'),
        pytest.param(
            {'orgs': {'a': {'api_key': 'x'}, 'b': {'api_key': 'y'}}},
            'orgs.*.api_key',
            [('api_key', 'x'), ('api_key', 'y')],
            id='wildcard-multiple-orgs',
        ),
        pytest.param({'orgs': {}}, 'orgs.*.api_key', [], id='wildcard-empty-section'),
        pytest.param({'orgs': {'a': 1, 'b': 2}}, 'orgs.*', [('a', 1), ('b', 2)], id='trailing-wildcard'),
    ],
)
def test_walk_config(config, glob, expected):
    result = [(key, parent[key]) for parent, key in _walk_config(config, glob)]
    assert sorted(result) == sorted(expected)
