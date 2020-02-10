# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

INSTANCE = {"tags": ["tag1:value1"]}


def _test_check(aggregator, instance):
    aggregator.assert_metric('system.swap.swapped_in', tags=instance.get("tags"))
    aggregator.assert_metric('system.swap.swapped_out', tags=instance.get("tags"))
