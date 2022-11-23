# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest
from mock import MagicMock, patch

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.testing import requires_py2, requires_py3


class MemrayCheck(AgentCheck):
    __NAMESPACE__ = 'memray'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.check_id = "test:123"
        self.tags = ['bar:baz']
        self.check_initializations.append(self.initialize)

    def initialize(self):
        self.gauge('initialize', 0, tags=self.tags)
        self.log.debug('Initializing - %s - %s', self.name, self.check_id)

    def check(self, _):
        self.gauge('metric', 0, tags=self.tags)
        self.service_check('sc', ServiceCheck.OK, tags=self.tags)


@pytest.mark.parametrize(
    'init_config, instance_config',
    [
        pytest.param({}, {'enable_memray': True}, id='Instance-level config'),
        pytest.param({'enable_memray': True}, {}, id='Init-level config'),
    ],
)
@requires_py3
def test_memray_windows(caplog, dd_run_check, aggregator, datadog_agent, init_config, instance_config):
    check = MemrayCheck('memory', init_config, [instance_config])

    with mock.patch('sys.platform', 'windows'):
        with pytest.raises(
            ConfigurationError, match='^`enable_memray` option is only supported on Linux and macOS\\.$'
        ):
            check.load_memray_context_manager()


@pytest.mark.parametrize(
    'init_config, instance_config',
    [
        pytest.param({}, {'enable_memray': True}, id='Instance-level config'),
        pytest.param({'enable_memray': True}, {}, id='Init-level config'),
    ],
)
@requires_py2
def test_memray_py2(caplog, dd_run_check, aggregator, datadog_agent, init_config, instance_config):
    check = MemrayCheck('memory', init_config, [instance_config])

    with pytest.raises(ConfigurationError, match='^`enable_memray` option is not supported for py2 environments\\.$'):
        check.load_memray_context_manager()


@pytest.mark.parametrize(
    'init_config, instance_config, native_traces',
    [
        pytest.param(
            {},
            {'enable_memray': True, 'memray_file': 'my-file'},
            False,
            id='Instance-level config without native traces',
        ),
        pytest.param(
            {'enable_memray': True, 'memray_file': 'my-file'}, {}, False, id='Init-level config without native traces'
        ),
        pytest.param(
            {},
            {'enable_memray': True, 'memray_file': 'my-file', 'memray_native_mode': True},
            True,
            id='Instance-level config with native traces',
        ),
        pytest.param(
            {'enable_memray': True, 'memray_file': 'my-file', 'memray_native_mode': True},
            {},
            True,
            id='Init-level config with native traces',
        ),
    ],
)
@requires_py3
def test_memray(caplog, dd_run_check, aggregator, datadog_agent, init_config, instance_config, native_traces):
    check = MemrayCheck('memory', init_config, [instance_config])
    tracker_mock = MagicMock()

    with patch("memray.Tracker", return_value=tracker_mock) as mock:
        dd_run_check(check)

    mock.assert_called_with(file_name="my-file", native_traces=native_traces)
    tracker_mock.__enter__.assert_called_once()
