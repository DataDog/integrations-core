# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.postfix import PostfixCheck

from .common import get_instance, get_queue_counts


@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator):
    instance = get_instance()
    check = PostfixCheck('postfix', {}, [instance])
    check.check(instance)

    for queue, count in get_queue_counts().items():
        tags = ['instance:postfix_data', 'queue:{}'.format(queue)]
        aggregator.assert_metric('postfix.queue.size', value=count[0], tags=tags)
