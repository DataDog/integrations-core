# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.time import get_timestamp
from datadog_checks.dev.testing import requires_py3

from ..utils import get_check

pytestmark = [
    requires_py3,
]


def test(aggregator, dd_run_check, mock_http_response):
    mock_http_response(
        """
        # HELP go_memstats_last_gc_time_seconds Number of seconds since 1970 of last garbage collection.
        # TYPE go_memstats_last_gc_time_seconds gauge
        go_memstats_last_gc_time_seconds{{foo="bar"}} {}
        """.format(
            get_timestamp() - 1.2
        )
    )
    check = get_check({'metrics': [{'go_memstats_last_gc_time_seconds': {'type': 'time_elapsed'}}]})
    dd_run_check(check)

    assert 'test.go_memstats_last_gc_time_seconds' in aggregator._metrics
    assert len(aggregator._metrics) == 1
    assert len(aggregator._metrics['test.go_memstats_last_gc_time_seconds']) == 1
    m = aggregator._metrics['test.go_memstats_last_gc_time_seconds'][0]

    assert 1.2 < m.value < 2
    assert m.type == aggregator.GAUGE
    assert set(m.tags) == {'endpoint:test', 'foo:bar'}
