# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.time import get_timestamp
from datadog_checks.dev.testing import requires_py3, requires_windows

from ..utils import GLOBAL_TAGS, get_check

pytestmark = [requires_py3, requires_windows]


def test(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects({'Foo': (['instance1'], {'Bar': [get_timestamp() - 1.2]})})
    check = get_check(
        {
            'metrics': {
                'Foo': {
                    'name': 'foo',
                    'tag_name': 'baz',
                    'counters': [{'Bar': {'name': 'bar', 'type': 'time_elapsed'}}],
                }
            }
        }
    )
    dd_run_check(check)

    tags = ['baz:instance1']
    tags.extend(GLOBAL_TAGS)

    assert 'test.foo.bar' in aggregator._metrics
    assert len(aggregator._metrics) == 1
    assert len(aggregator._metrics['test.foo.bar']) == 1
    m = aggregator._metrics['test.foo.bar'][0]

    assert 1.2 < m.value < 2
    assert m.type == aggregator.GAUGE
    assert sorted(m.tags) == sorted(tags)
