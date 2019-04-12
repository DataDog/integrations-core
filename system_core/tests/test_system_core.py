# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock

from datadog_checks.system_core import SystemCore

from . import common


class TestSystemCore:
    def test_system_core(self, aggregator):
        c = SystemCore('system_core', {}, {}, [{}])

        psutil_mock = mock.MagicMock(return_value=common.MOCK_PSUTIL_CPU_TIMES)
        with mock.patch('datadog_checks.system_core.system_core.psutil.cpu_times', psutil_mock):
            c.check({})

        aggregator.assert_metric('system.core.count', value=4, count=1)

        for i in range(4):
            for rate in common.CHECK_RATES:
                aggregator.assert_metric(rate, count=1, tags=['core:{0}'.format(i)])
