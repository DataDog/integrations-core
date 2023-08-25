# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import defaultdict

import mock
from six import iteritems

from datadog_checks.base.utils.platform import Platform
from datadog_checks.system_core import SystemCore

from . import common


class TestSystemCore:
    def test_system_core(self, aggregator):
        c = SystemCore('system_core', {}, {}, [{}])

        with mock.patch('datadog_checks.system_core.system_core.psutil') as psutil_mock:
            psutil_mock.cpu_times.side_effect = fake_cpu_times
            psutil_mock.cpu_count.return_value = common.MOCK_PSUTIL_CPU_COUNT
            psutil_mock.cpu_freq.return_value = common.MOCK_PSUTIL_CPU_FREQ
            c.check({})

        aggregator.assert_metric('system.core.count', value=4, count=1)
        for i, _freq in enumerate(common.MOCK_PSUTIL_CPU_FREQ):
            aggregator.assert_metric('system.core.frequency', value=2500, tags=['core:{}'.format(i)])

        for rate in common.CHECK_RATES:
            for i in range(4):
                aggregator.assert_metric(rate, count=1, tags=['core:{0}'.format(i)])

            aggregator.assert_metric('{}.total'.format(rate), count=1)

    def test_system_core_not_unix(self, aggregator, dd_run_check):
        """
        We force the 'is_unix' check to be false to make sure no per-CPU tags are attached to the frequency metric.
        """
        c = SystemCore('system_core', {}, {}, [{}])
        with mock.patch('datadog_checks.system_core.system_core.psutil') as psutil_mock, mock.patch.object(
            Platform, 'is_unix'
        ) as is_unix_mock:
            psutil_mock.cpu_times.side_effect = fake_cpu_times
            psutil_mock.cpu_count.return_value = common.MOCK_PSUTIL_CPU_COUNT
            psutil_mock.cpu_freq.return_value = common.MOCK_PSUTIL_CPU_FREQ
            is_unix_mock.return_value = False
            dd_run_check(c)

        aggregator.assert_metric('system.core.frequency', value=2500, tags=[])


def fake_cpu_times(percpu=False):
    if percpu:
        return common.MOCK_PSUTIL_CPU_TIMES
    else:
        # Average all the values
        sum_dict = defaultdict(float)

        for cputimes in common.MOCK_PSUTIL_CPU_TIMES:
            for key, value in iteritems(cputimes._asdict()):
                sum_dict[key] += value / len(common.MOCK_PSUTIL_CPU_TIMES)

        return common.MOCK_PSUTIL_CPU_TIMES[0].__class__(**sum_dict)
