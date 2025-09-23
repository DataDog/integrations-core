# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import get_e2e_instance, get_e2e_instance_postqueue, get_queue_counts


@pytest.mark.e2e
def test_check_default(dd_agent_check):
    aggregator = dd_agent_check(get_e2e_instance())

    for queue, count in get_queue_counts().items():
        tags = ['instance:postfix_data', 'queue:{}'.format(queue)]
        aggregator.assert_metric('postfix.queue.size', value=count[0], tags=tags)


@pytest.mark.e2e
def test_check_postqueue(dd_agent_check):
    aggregator = dd_agent_check(get_e2e_instance_postqueue())

    for queue in ['active', 'hold', 'deferred']:
        tags = ['instance:/etc/postfix', 'queue:{}'.format(queue)]
        # TODO: assert `postfix.queue.size` metric value, this will require starting the postfix server
        aggregator.assert_metric('postfix.queue.size', tags=tags)
