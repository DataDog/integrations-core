# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from six import PY2

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import ON_WINDOWS


class MemrayCheck(AgentCheck):
    __NAMESPACE__ = 'memray'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.check_initializations.append(self.initialize)

    def initialize(self):
        self.gauge('initialize', 0, tags=self.tags)
        self.log.debug('Initializing - %s - %s', self.name, self.check_id)

    def check(self, _):
        self.gauge('metric', 0, tags=self.tags)
        self.service_check('sc', ServiceCheck.OK if self.redirecting else ServiceCheck.CRITICAL, tags=self.tags)


@pytest.mark.parametrize(
    'init_config, instance_config',
    [
        pytest.param({'tags': ['bar:baz']}, {'enable_memray': True, 'tags': ['foo:bar']}, id='Instance-level config'),
        pytest.param({'tags': ['bar:baz'], 'enable_memray': True}, {'tags': ['foo:bar']}, id='Init-level config'),
    ],
)
@pytest.mark.skipif(not ON_WINDOWS, reason='Memray is not supported on Windows')
def test_memray_windows(caplog, dd_run_check, aggregator, datadog_agent, init_config, instance_config):
    check = MemrayCheck('memory', init_config, [instance_config])
    check.check_id = 'test:123'

    with pytest.raises(ConfigurationError, match='^`enable_memray` option is only supported on Linux and macOS.$'):
        dd_run_check(check)


@pytest.mark.parametrize(
    'init_config, instance_config',
    [
        pytest.param({'tags': ['bar:baz']}, {'enable_memray': True, 'tags': ['foo:bar']}, id='Instance-level config'),
        pytest.param({'tags': ['bar:baz'], 'enable_memray': True}, {'tags': ['foo:bar']}, id='Init-level config'),
    ],
)
@pytest.mark.skipif(not PY2, reason='Memray is not supported on py2 environments')
def test_memray_py2(caplog, dd_run_check, aggregator, datadog_agent, init_config, instance_config):
    check = MemrayCheck('memory', init_config, [instance_config])
    check.check_id = 'test:123'

    with pytest.raises(ConfigurationError, match='^`enable_memray` option is not supported for py2 environments.$'):
        dd_run_check(check)
