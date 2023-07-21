# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.testing import requires_py3

pytestmark = [requires_py3]


def test_make_immutable():
    # TODO: move imports up top when we drop Python 2
    from types import MappingProxyType

    from datadog_checks.base.utils.models.validation.utils import make_immutable

    obj = make_immutable(
        {
            'string': 'foo',
            'integer': 9000,
            'float': 3.14,
            'boolean': True,
            'array': [{'key': 'foo'}, {'key': 'bar'}],
            'mapping': {'foo': 'bar'},
        }
    )

    assert isinstance(obj, MappingProxyType)
    assert len(obj) == 6
    assert isinstance(obj['string'], str)
    assert obj['string'] == 'foo'
    assert isinstance(obj['integer'], int)
    assert obj['integer'] == 9000
    assert isinstance(obj['float'], float)
    assert obj['float'] == 3.14
    assert isinstance(obj['boolean'], bool)
    assert obj['boolean'] is True
    assert isinstance(obj['array'], tuple)
    assert len(obj['array']) == 2
    assert isinstance(obj['array'][0], MappingProxyType)
    assert obj['array'][0]['key'] == 'foo'
    assert isinstance(obj['array'][1], MappingProxyType)
    assert obj['array'][1]['key'] == 'bar'
    assert isinstance(obj['mapping'], MappingProxyType)
    assert len(obj['mapping']) == 1
    assert obj['mapping']['foo'] == 'bar'
