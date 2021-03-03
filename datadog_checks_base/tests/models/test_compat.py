# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck

from ..utils import requires_py2
from .config_models import ConfigMixin

pytestmark = [requires_py2]


class Check(AgentCheck, ConfigMixin):
    def check(self, _):
        pass


def test(dd_run_check):
    init_config = {}
    instance = {}

    check = Check('test', init_config, [instance])
    check.check_id = 'test:123'

    dd_run_check(check)

    assert check.shared_config.deprecated == ''

    assert check.config.text == ''
    assert check.config.flag is False
    assert check.config.timeout == 0 and isinstance(check.config.timeout, float)
    assert check.config.pid == 0 and isinstance(check.config.pid, int)
    assert check.config.array == []
    assert check.config.mapping == {}
    assert check.config.obj == {}
