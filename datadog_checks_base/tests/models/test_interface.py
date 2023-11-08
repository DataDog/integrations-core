# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import PY3

from datadog_checks.base import AgentCheck
from datadog_checks.dev.testing import requires_py3

if PY3:
    from .config_models import ConfigMixin
else:
    ConfigMixin = object

pytestmark = [requires_py3]


class Check(AgentCheck, ConfigMixin):
    def check(self, _):
        pass


def test_defaults(dd_run_check):
    init_config = {}
    instance = {}

    check = Check('test', init_config, [instance])
    check.check_id = 'test:123'

    dd_run_check(check)

    assert check.shared_config.deprecated is None

    assert check.config.text is None
    assert check.config.flag is False
    assert check.config.timeout is None
    assert check.config.pid is None
    assert check.config.array is None
    assert check.config.mapping is None
    assert check.config.obj is None

    assert not check.warnings


def test_errors_shared_config(dd_run_check):
    init_config = {'timeout': 'foo'}
    instance = {}

    check = Check('test', init_config, [instance])
    check.check_id = 'test:123'

    with pytest.raises(
        Exception,
        match="""Detected 1 error while loading configuration model `SharedConfig`:
timeout
  Input should be a valid number, unable to parse string as a number""",
    ):
        dd_run_check(check, extract_message=True)


def test_errors_instance_config(dd_run_check):
    init_config = {}
    instance = {'timeout': 'foo', 'array': [[]], 'obj': {'bar': []}}

    check = Check('test', init_config, [instance])
    check.check_id = 'test:123'

    with pytest.raises(
        Exception,
        match="""Detected 3 errors while loading configuration model `InstanceConfig`:
array -> 1
  Input should be a valid string
obj -> foo
  Field required
timeout
  Input should be a valid number, unable to parse string as a number""",
    ):
        dd_run_check(check, extract_message=True)


@pytest.mark.parametrize(
    'value, result',
    [
        (0, False),
        (1, True),
        (2, 'error'),
        ('foo', 'error'),
        ('yes', True),
        ('no', False),
        ('true', True),
        ('false', False),
    ],
)
def test_boolean_allowance(dd_run_check, value, result):
    init_config = {}
    instance = {'flag': value}

    check = Check('test', init_config, [instance])
    check.check_id = 'test:123'

    if result == 'error':
        with pytest.raises(Exception):
            dd_run_check(check)
    else:
        dd_run_check(check)

        assert check.config.flag is result


@pytest.mark.parametrize(
    'name, normalized_name',
    [pytest.param('pass', 'pass_', id='keyword'), pytest.param('hyphenated-name', 'hyphenated_name', id='hyphenated')],
)
def test_name_edge_cases(dd_run_check, name, normalized_name):
    init_config = {}
    instance = {name: 'foo'}

    check = Check('test', init_config, [instance])
    check.check_id = 'test:123'

    dd_run_check(check)

    assert getattr(check.config, normalized_name) == 'foo'


def test_deprecations(dd_run_check):
    init_config = {'deprecated': 'foo'}
    instance = {'deprecated': 'foo'}

    check = Check('test', init_config, [instance])
    check.check_id = 'test:123'

    dd_run_check(check)

    assert check.warnings == [
        """Option `deprecated` in `init_config` is deprecated ->
Agent_Version: 8.0.0
Migration: do this
           and that
""",
        """Option `deprecated` in `instances` is deprecated ->
Agent version: 9.0.0
Migration: do this
           and that
""",
    ]
